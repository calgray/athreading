"""Generator utilities."""

from __future__ import annotations

import asyncio
import queue
import threading
from collections.abc import AsyncGenerator, Generator
from concurrent.futures import Future, ThreadPoolExecutor, wait
from contextlib import AbstractAsyncContextManager
from types import TracebackType
from typing import TypeVar

from overrides import override

YieldT = TypeVar("YieldT")
SendT = TypeVar("SendT")


def generate(
    generator: Generator[YieldT, SendT | None, None],
    executor: ThreadPoolExecutor | None = None,
) -> ThreadedAsyncGenerator[YieldT, SendT]:
    """Runs a synchronous generator with a ThreadPoolExecutor and exposes itself as a thread-safe
    async generator.

    Args:
        generator (Generator[YieldT, SendT  |  None, None]): _description_
        executor (ThreadPoolExecutor | None, optional): _description_. Defaults to None.

    Returns:
        ThreadedAsyncGenerator[YieldT, SendT]: _description_
    """
    return ThreadedAsyncGenerator(generator, executor)


class ThreadedAsyncGenerator(
    AbstractAsyncContextManager["ThreadedAsyncGenerator[YieldT, SendT]"],
    AsyncGenerator[YieldT, SendT | None],
):
    """Runs a synchronous generator with a ThreadPoolExecutor and exposes itself as a thread-safe
    async generator.
    """

    def __init__(
        self,
        generator: Generator[YieldT, SendT | None, None],
        executor: ThreadPoolExecutor | None = None,
    ):
        """Initilizes a ThreadedAsyncGenerator from a synchronous generator.

        Args:
            generator (Generator[ItemT, SendT, None]): Synchronous generator.
            executor (ThreadPoolExecutor, optional): Shared thread pool instance. Defaults to
            ThreadPoolExecutor().
        """
        self._semaphore = asyncio.Semaphore(0)
        self._event = threading.Event()
        self._send_queue: queue.Queue[SendT | None] = queue.Queue()
        self._yield_queue: queue.Queue[YieldT] = queue.Queue()
        self._loop = asyncio.get_running_loop()
        self._generator = generator
        self._executor = executor if executor is not None else ThreadPoolExecutor()
        self._stream_future: Future[None] | None = None

    @override
    async def __aenter__(self) -> ThreadedAsyncGenerator[YieldT, SendT]:
        self._stream_future = self._executor.submit(self.__stream)
        return self

    @override
    async def __aexit__(
        self,
        __exc_type: type[BaseException] | None,
        __val: BaseException | None,
        __tb: TracebackType | None,
    ) -> None:
        assert self._stream_future is not None
        self._event.set()
        self._semaphore.release()
        self._send_queue.put(None)
        wait([self._stream_future])

    @override
    async def __anext__(self) -> YieldT:
        assert (
            self._stream_future is not None
        ), "Generator started before entering thread context"
        self._send_queue.put(None)
        return await self.__get()

    @override
    async def asend(self, value: SendT | None) -> YieldT:
        """Send a value to the generator send queue"""
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
        """Raise an exception immediately from the generator"""
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
