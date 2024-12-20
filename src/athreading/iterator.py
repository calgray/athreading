"""Iterator utilities."""


from __future__ import annotations

import asyncio
import functools
import queue
import threading
from collections.abc import AsyncIterator, Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractAsyncContextManager
from types import TracebackType
from typing import ParamSpec, TypeVar, overload

from typing_extensions import override

ParamsT = ParamSpec("ParamsT")
YieldT = TypeVar("YieldT")


@overload
def iterate(
    fn: None = None,
    *,
    executor: ThreadPoolExecutor | None = None,
) -> Callable[
    [Callable[ParamsT, Iterator[YieldT]]],
    Callable[ParamsT, ThreadedAsyncIterator[YieldT]],
]:
    pass


@overload
def iterate(
    fn: Callable[ParamsT, Iterator[YieldT]],
    *,
    executor: ThreadPoolExecutor | None = None,
) -> Callable[ParamsT, ThreadedAsyncIterator[YieldT]]:
    pass


def iterate(
    fn: Callable[ParamsT, Iterator[YieldT]] | None = None,
    *,
    executor: ThreadPoolExecutor | None = None,
) -> (
    Callable[ParamsT, ThreadedAsyncIterator[YieldT]]
    | Callable[
        [Callable[ParamsT, Iterator[YieldT]]],
        Callable[ParamsT, ThreadedAsyncIterator[YieldT]],
    ]
):
    """Decorates a thread-safe iterator with a ThreadPoolExecutor and exposes a thread-safe
    AsyncIterator.

    Args:
        fn (Callable[ParamsT, Iterator[YieldT]], optional): Function returning an iterator or
        iterable. Defaults to None.
        executor (ThreadPoolExecutor, optional): Defaults to None.

    Returns:
        Callable[ParamsT, ThreadedAsyncIterator[YieldT]]: Decorated iterator function with lazy
        argument evaluation.
    """
    if fn is None:
        return _create_iterate_decorator(executor=executor)
    else:

        @functools.wraps(fn)
        def wrapper(
            *args: ParamsT.args, **kwargs: ParamsT.kwargs
        ) -> ThreadedAsyncIterator[YieldT]:
            return ThreadedAsyncIterator(fn(*args, **kwargs), executor=executor)

        return wrapper


def _create_iterate_decorator(
    executor: ThreadPoolExecutor | None = None,
) -> Callable[
    [Callable[ParamsT, Iterator[YieldT]]],
    Callable[ParamsT, ThreadedAsyncIterator[YieldT]],
]:
    def decorator(
        fn: Callable[ParamsT, Iterator[YieldT]],
    ) -> Callable[ParamsT, ThreadedAsyncIterator[YieldT]]:
        @functools.wraps(fn)
        def wrapper(
            *args: ParamsT.args, **kwargs: ParamsT.kwargs
        ) -> ThreadedAsyncIterator[YieldT]:
            return ThreadedAsyncIterator(fn(*args, **kwargs), executor=executor)

        return wrapper

    return decorator


class ThreadedAsyncIterator(
    AbstractAsyncContextManager["ThreadedAsyncIterator[YieldT]"], AsyncIterator[YieldT]
):
    """Wraps a synchronous Iterator with a ThreadPoolExecutor and exposes an AsyncIterator."""

    def __init__(
        self,
        iterator: Iterator[YieldT],
        executor: ThreadPoolExecutor | None = None,
    ):
        """Initilizes a ThreadedAsyncIterator from a synchronous iterator.

        Args:
            iterator (Iterator[YieldT]): Synchronous iterator or iterable.
            executor (ThreadPoolExecutor, optional): Shared thread pool instance. Defaults to
            asyncio ThreadPoolExecutor().
        """
        self._yield_semaphore = asyncio.Semaphore(0)
        self._done_event = threading.Event()
        self._queue: queue.Queue[YieldT] = queue.Queue()
        self._iterator = iterator
        self._executor = executor
        self._stream_future: asyncio.Future[None] | None = None

    @override
    async def __aenter__(self) -> ThreadedAsyncIterator[YieldT]:
        self._loop = asyncio.get_running_loop()
        self._stream_future = self._loop.run_in_executor(self._executor, self.__stream)
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
        await self._stream_future

    async def __anext__(self) -> YieldT:
        assert (
            self._stream_future is not None
        ), "Iteration started before entering context"
        if not self._done_event.is_set() or not self._queue.empty():
            await self._yield_semaphore.acquire()
            if not self._queue.empty():
                return self._queue.get(False)
        raise StopAsyncIteration

    def __stream(self) -> None:
        try:
            for item in self._iterator:
                self._queue.put(item)
                self._loop.call_soon_threadsafe(self._yield_semaphore.release)
                if self._done_event.is_set():
                    break
        finally:
            self._done_event.set()
            self._loop.call_soon_threadsafe(self._yield_semaphore.release)
