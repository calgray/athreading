"""Generator utilities."""

from __future__ import annotations

import asyncio
import functools
import queue
import threading
from collections.abc import AsyncGenerator, Callable, Generator
from concurrent.futures import Future, ThreadPoolExecutor, wait
from contextlib import AbstractAsyncContextManager
from types import TracebackType
from typing import ParamSpec, TypeVar, overload

from overrides import override

ParamsT = ParamSpec("ParamsT")
YieldT = TypeVar("YieldT")
SendT = TypeVar("SendT")


@overload
def generate(
    fn: None = None,
    *,
    executor: ThreadPoolExecutor | None = None,
) -> Callable[
    [Callable[ParamsT, Generator[YieldT, SendT | None, None]]],
    Callable[ParamsT, ThreadedAsyncGenerator[YieldT, SendT]],
]:
    pass


@overload
def generate(
    fn: Callable[ParamsT, Generator[YieldT, SendT | None, None]],
    *,
    executor: ThreadPoolExecutor | None = None,
) -> Callable[ParamsT, ThreadedAsyncGenerator[YieldT, SendT]]:
    pass


def generate(
    fn: Callable[ParamsT, Generator[YieldT, SendT | None, None]] | None = None,
    *,
    executor: ThreadPoolExecutor | None = None,
) -> (
    Callable[ParamsT, ThreadedAsyncGenerator[YieldT, SendT]]
    | Callable[
        [Callable[ParamsT, Generator[YieldT, SendT | None, None]]],
        Callable[ParamsT, ThreadedAsyncGenerator[YieldT, SendT]],
    ]
):
    """Runs a thread-safe synchronous generator with a ThreadPoolExecutor and exposes a
    thread-safe async generator.

    Args:
        generator (Generator[YieldT, SendT  |  None, None]): _description_
        executor (ThreadPoolExecutor | None, optional): _description_. Defaults to None.

    Returns:
        ThreadedAsyncGenerator[YieldT, SendT]: _description_
    """
    if fn is None:
        return _generate_decorator(executor=executor)
    else:

        @functools.wraps(fn)
        def wrapper(
            *args: ParamsT.args, **kwargs: ParamsT.kwargs
        ) -> ThreadedAsyncGenerator[YieldT, SendT]:
            return _generate(fn(*args, **kwargs), executor=executor)

        return wrapper


def _generate(
    generator: Generator[YieldT, SendT | None, None],
    executor: ThreadPoolExecutor | None = None,
) -> ThreadedAsyncGenerator[YieldT, SendT]:
    return ThreadedAsyncGenerator(generator, executor)


def _generate_decorator(
    executor: ThreadPoolExecutor | None = None,
) -> Callable[
    [Callable[ParamsT, Generator[YieldT, SendT | None, None]]],
    Callable[ParamsT, ThreadedAsyncGenerator[YieldT, SendT]],
]:
    """_summary_

    Args:
        executor (ThreadPoolExecutor | None, optional): _description_. Defaults to None.

    Returns:
        Callable[
            [Callable[ParamsT, Generator[YieldT, SendT | None, None]]],
            Callable[ParamsT, ThreadedAsyncGenerator[YieldT, SendT]],
        ]: _description_
    """

    def decorator(
        fn: Callable[ParamsT, Generator[YieldT, SendT | None, None]],
    ) -> Callable[ParamsT, ThreadedAsyncGenerator[YieldT, SendT]]:
        @functools.wraps(fn)
        def wrapper(
            *args: ParamsT.args, **kwargs: ParamsT.kwargs
        ) -> ThreadedAsyncGenerator[YieldT, SendT]:
            return _generate(fn(*args, **kwargs), executor)

        return wrapper

    return decorator


class ThreadedAsyncGenerator(
    AbstractAsyncContextManager["ThreadedAsyncGenerator[YieldT, SendT]"],
    AsyncGenerator[YieldT, SendT | None],
):
    """Runs a thread-safe synchronous generator with a ThreadPoolExecutor and exposes a
    thread-safe async generator.
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
        self._yield_semaphore = asyncio.Semaphore(0)
        self._done_event = threading.Event()
        self._send_queue: queue.Queue[SendT | None] = queue.Queue()
        self._yield_queue: queue.Queue[YieldT] = queue.Queue()
        self._generator = generator
        self._executor = executor if executor is not None else ThreadPoolExecutor()
        self._stream_future: Future[None] | None = None

    @override
    async def __aenter__(self) -> ThreadedAsyncGenerator[YieldT, SendT]:
        self._loop = asyncio.get_running_loop()
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
        self._done_event.set()
        self._yield_semaphore.release()
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
        if not self._done_event.is_set() or not self._yield_queue.empty():
            await self._yield_semaphore.acquire()
            if not self._yield_queue.empty():
                return self._yield_queue.get(False)
        raise StopAsyncIteration

    async def athrow(
        self,
        __typ: type[BaseException] | BaseException,
        __val: object = None,
        __tb: TracebackType | None = None,
    ) -> YieldT:
        """Raise a custom exception immediately from the generator"""
        if isinstance(__typ, BaseException):
            raise __typ
        return self._generator.throw(__typ, __val, __tb)

    def __stream(self) -> None:
        try:
            while not self._done_event.is_set():
                sent = self._send_queue.get()
                if not self._done_event.is_set():
                    try:
                        item = self._generator.send(sent)
                        self._yield_queue.put(item)
                        self._loop.call_soon_threadsafe(self._yield_semaphore.release)
                    except StopIteration:
                        break
        finally:
            self._done_event.set()
            self._loop.call_soon_threadsafe(self._yield_semaphore.release)
