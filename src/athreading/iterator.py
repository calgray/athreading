"""Iterator utilities."""

from __future__ import annotations

import asyncio
import functools
import queue
import sys
import threading
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from types import TracebackType
from typing import Optional, TypeVar, Union

from athreading.type_aliases import AsyncIteratorContext

if sys.version_info[:2] > (3, 11):
    from typing import ParamSpec, overload, override
else:
    from typing_extensions import ParamSpec, overload, override


ParamsT = ParamSpec("ParamsT")
YieldT = TypeVar("YieldT")


@overload
def iterate(
    fn: None = None,
    *,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Callable[
    [Callable[ParamsT, Iterator[YieldT]]],
    Callable[ParamsT, AsyncIteratorContext[YieldT]],
]:
    ...


@overload
def iterate(
    fn: Callable[ParamsT, Iterator[YieldT]],
    *,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Callable[ParamsT, AsyncIteratorContext[YieldT]]:
    ...


def iterate(
    fn: Optional[Callable[ParamsT, Iterator[YieldT]]] = None,
    *,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Union[
    Callable[ParamsT, AsyncIteratorContext[YieldT]],
    Callable[
        [Callable[ParamsT, Iterator[YieldT]]],
        Callable[ParamsT, AsyncIteratorContext[YieldT]],
    ],
]:
    """Decorates a thread-safe iterator with a ThreadPoolExecutor and exposes a thread-safe
    AsyncIterator.

    Args:
        fn (Callable[ParamsT, Iterator[YieldT]], optional): Function returning an iterator or
        iterable. Defaults to None.
        executor (ThreadPoolExecutor, optional): Defaults to None.

    Returns:
        Callable[ParamsT, AsyncIteratorContext[YieldT]]: Decorated iterator function with lazy
        argument evaluation.
    """
    if fn is None:
        return _create_iterate_decorator(executor=executor)
    else:

        @functools.wraps(fn)
        def wrapper(
            *args: ParamsT.args, **kwargs: ParamsT.kwargs
        ) -> AsyncIteratorContext[YieldT]:
            return ThreadedAsyncIterator(fn(*args, **kwargs), executor=executor)

        return wrapper


def _create_iterate_decorator(
    executor: Optional[ThreadPoolExecutor] = None,
) -> Callable[
    [Callable[ParamsT, Iterator[YieldT]]],
    Callable[ParamsT, AsyncIteratorContext[YieldT]],
]:
    def decorator(
        fn: Callable[ParamsT, Iterator[YieldT]],
    ) -> Callable[ParamsT, AsyncIteratorContext[YieldT]]:
        @functools.wraps(fn)
        def wrapper(
            *args: ParamsT.args, **kwargs: ParamsT.kwargs
        ) -> AsyncIteratorContext[YieldT]:
            return ThreadedAsyncIterator(fn(*args, **kwargs), executor=executor)

        return wrapper

    return decorator


class ThreadedAsyncIterator(AsyncIteratorContext[YieldT]):
    """Wraps a synchronous Iterator with a ThreadPoolExecutor and exposes an AsyncIterator."""

    def __init__(
        self,
        iterator: Iterator[YieldT],
        executor: Optional[ThreadPoolExecutor] = None,
    ):
        """Initilizes a ThreadedAsyncIterator from a synchronous iterator.

        Args:
            iterator (Iterator[YieldT]): Synchronous iterator or iterable.
            executor (ThreadPoolExecutor, optional): Shared thread pool instance. Defaults to
            ThreadPoolExecutor().
        """
        self._yield_semaphore = asyncio.Semaphore(0)
        self._done_event = threading.Event()
        self._queue: queue.Queue[YieldT] = queue.Queue()
        self._iterator = iterator
        self._executor = executor
        self._stream_future: Optional[asyncio.Future[None]] = None

    @override
    async def __aenter__(self) -> ThreadedAsyncIterator[YieldT]:
        self._loop = asyncio.get_running_loop()
        self._stream_future = self._loop.run_in_executor(
            self._executor, self.__stream_threadsafe
        )
        return self

    @override
    async def __aexit__(
        self,
        __exc_type: Optional[type[BaseException]],
        __val: Optional[BaseException],
        __tb: Optional[TracebackType],
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

    def __stream_threadsafe(self) -> None:
        """Stream the synchronous itertor to the queue and notify the async thread."""
        try:
            for item in self._iterator:
                self._queue.put(item)
                self._loop.call_soon_threadsafe(self._yield_semaphore.release)
                if self._done_event.is_set():
                    break
        finally:
            self._done_event.set()
            self._loop.call_soon_threadsafe(self._yield_semaphore.release)
