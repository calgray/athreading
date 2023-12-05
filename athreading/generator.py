from __future__ import annotations

import asyncio
import queue
import threading
from collections.abc import AsyncGenerator, Generator
from concurrent.futures import ThreadPoolExecutor, wait
from contextlib import AbstractAsyncContextManager
from types import TracebackType
from typing import TypeVar

YieldT = TypeVar("YieldT")
SendT = TypeVar("SendT")


def generate(
    generator: Generator[YieldT, SendT | None, None],
    executor: ThreadPoolExecutor | None = None,
) -> ThreadedAsyncGenerator[YieldT, SendT]:
    return ThreadedAsyncGenerator(generator, executor)


class ThreadedAsyncGenerator(
    AbstractAsyncContextManager["ThreadedAsyncGenerator[YieldT, SendT]"],
    AsyncGenerator[YieldT, SendT | None],
):
    """
    Runs a synchronous generator with a ThreadPoolExecutor and exposes itself as a thread-safe async generator.
    """

    def __init__(
        self,
        generator: Generator[YieldT, SendT | None, None],
        executor: ThreadPoolExecutor | None = None,
    ):
        """Initilizes a ThreadedAsyncGenerator from a synchronous generator.

        Args:
            generator (Generator[ItemT, SendT, None]): Synchronous generator.
            executor (ThreadPoolExecutor, optional): Shared thread pool instance. Defaults to ThreadPoolExecutor().
        """
        self._semaphore = asyncio.Semaphore(0)
        self._event = threading.Event()
        self._send_queue: queue.Queue[SendT | None] = queue.Queue()
        self._yield_queue: queue.Queue[YieldT] = queue.Queue()
        self._loop = asyncio.get_running_loop()
        self._generator = generator
        self._executor = executor if executor is not None else ThreadPoolExecutor()

    async def __aenter__(self) -> ThreadedAsyncGenerator[YieldT, SendT]:
        self.stream_future = self._executor.submit(self.__stream)
        return self

    async def __aexit__(
        self,
        __exc_type: type[BaseException] | None,
        __val: BaseException | None,
        __tb: TracebackType | None,
    ) -> None:
        self._event.set()
        self._semaphore.release()
        self._send_queue.put(None)
        wait([self.stream_future])

    async def __anext__(self) -> YieldT:
        assert (
            self.stream_future is not None
        ), "Iterator started before entering thread context"
        self._send_queue.put(None)
        return await self.__get()

    async def asend(self, value: SendT | None) -> YieldT:
        self._send_queue.put(value)
        return await self.__get()

    async def __get(self) -> YieldT:
        if not self._event.is_set() or not self._yield_queue.empty():
            await self._semaphore.acquire()
            if not self._yield_queue.empty():
                return self._yield_queue.get(False)
        raise StopAsyncIteration

    async def athrow(
        self,
        __typ: type[BaseException] | BaseException,
        __val: object = None,
        __tb: TracebackType | None = None,
    ) -> YieldT:
        if isinstance(__typ, BaseException):
            raise __typ
        return self._generator.throw(__typ, __val, __tb)

    def __stream(self) -> None:
        while not self._event.is_set():
            sent = self._send_queue.get()
            if not self._event.is_set():
                try:
                    item = self._generator.send(sent)
                    self._yield_queue.put(item)
                    self._loop.call_soon_threadsafe(self._semaphore.release)
                except StopIteration:
                    break

        self._event.set()
        self._loop.call_soon_threadsafe(self._semaphore.release)
