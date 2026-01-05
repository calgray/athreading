"""Iterator utilities."""

from __future__ import annotations

import asyncio
import functools
import queue
import sys
import threading
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Optional, TypeVar, Union

from athreading.aliases import AsyncIteratorContext

if sys.version_info >= (3, 12):
    from typing import ParamSpec, overload, override
else:  # pragma: not covered
    from typing_extensions import ParamSpec, overload, override

if TYPE_CHECKING:
    from types import TracebackType


_ParamsT = ParamSpec("_ParamsT")
_YieldT = TypeVar("_YieldT")


@overload
def iterate(
    fn: None = None,
    *,
    buffer_maxsize: Optional[int] = None,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Callable[
    [Callable[_ParamsT, Iterator[_YieldT]]],
    Callable[_ParamsT, AsyncIteratorContext[_YieldT]],
]:
    ...


@overload
def iterate(
    fn: Callable[_ParamsT, Iterator[_YieldT]],
    *,
    buffer_maxsize: Optional[int] = None,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Callable[_ParamsT, AsyncIteratorContext[_YieldT]]:
    ...


def iterate(
    fn: Optional[Callable[_ParamsT, Iterator[_YieldT]]] = None,
    *,
    buffer_maxsize: Optional[int] = None,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Union[
    Callable[_ParamsT, AsyncIteratorContext[_YieldT]],
    Callable[
        [Callable[_ParamsT, Iterator[_YieldT]]],
        Callable[_ParamsT, AsyncIteratorContext[_YieldT]],
    ],
]:
    """Decorates a thread-safe iterator with a ThreadPoolExecutor and exposes a thread-safe
    AsyncIterator.

    Args:
        fn: Function returning an iterator or iterable. Defaults to None.
        buffer_maxsize: Maximum number of items the background worker will buffer before
            blocking and putting backpressure on the source. Defaults to None (no-limit).

        executor: Defaults to None.

    Returns:
        Decorated iterator function with lazy argument evaluation.
    """
    return (
        _create_iterate_decorator(buffer_maxsize=buffer_maxsize, executor=executor)
        if fn is None
        else _create_iterate_wrapper(
            fn, buffer_maxsize=buffer_maxsize, executor=executor
        )
    )


def _create_iterate_wrapper(
    fn: Callable[_ParamsT, Iterator[_YieldT]],
    *,
    buffer_maxsize: Optional[int],
    executor: Optional[ThreadPoolExecutor],
) -> Callable[_ParamsT, AsyncIteratorContext[_YieldT]]:
    @functools.wraps(fn)
    def wrapper(
        *args: _ParamsT.args, **kwargs: _ParamsT.kwargs
    ) -> AsyncIteratorContext[_YieldT]:
        return ThreadedAsyncIterator(
            fn(*args, **kwargs), buffer_maxsize=buffer_maxsize, executor=executor
        )

    return wrapper


def _create_iterate_decorator(
    buffer_maxsize: Optional[int],
    executor: Optional[ThreadPoolExecutor],
) -> Callable[
    [Callable[_ParamsT, Iterator[_YieldT]]],
    Callable[_ParamsT, AsyncIteratorContext[_YieldT]],
]:
    def decorator(
        fn: Callable[_ParamsT, Iterator[_YieldT]],
    ) -> Callable[_ParamsT, AsyncIteratorContext[_YieldT]]:
        return _create_iterate_wrapper(
            fn, buffer_maxsize=buffer_maxsize, executor=executor
        )

    return decorator


class ThreadedAsyncIterator(AsyncIteratorContext[_YieldT]):
    """Wraps a synchronous iterator with an executor and exposes an AsyncIteratorContext."""

    def __init__(
        self,
        iterator: Iterator[_YieldT],
        buffer_maxsize: Optional[int] = None,
        executor: Optional[ThreadPoolExecutor] = None,
    ):
        """Initilizes a ThreadedAsyncIterator from a synchronous iterator.

        Args:
            iterator: Synchronous iterator or iterable.
            buffer_maxsize: Maximum number of items the background worker will buffer before
                blocking and putting backpressure on the source. Defaults to None (no-limit).
            executor: Shared thread pool instance. Defaults to ThreadPoolExecutor().
        """
        self._yield_semaphore = asyncio.Semaphore(0)
        self._done_event = threading.Event()
        self._queue: queue.Queue[_YieldT] = queue.Queue(buffer_maxsize or 0)
        self._iterator = iterator
        self._executor = executor
        self._worker_future: Optional[asyncio.Future[None]] = None

    @override
    async def __aenter__(self) -> ThreadedAsyncIterator[_YieldT]:
        self._loop = asyncio.get_running_loop()
        self._worker_future = self._loop.run_in_executor(
            self._executor, self.__worker_threadsafe
        )
        return self

    @override
    async def __aexit__(
        self,
        __exc_type: Optional[type[BaseException]],
        __val: Optional[BaseException],
        __tb: Optional[TracebackType],
        /,
    ) -> None:
        assert self._worker_future is not None
        self._done_event.set()
        self._yield_semaphore.release()
        await self._worker_future

    async def __anext__(self) -> _YieldT:
        assert (
            self._worker_future is not None
        ), "Iteration started before entering context"
        if not self._done_event.is_set() or not self._queue.empty():
            await self._yield_semaphore.acquire()
            if not self._queue.empty():
                return self._queue.get(False)
        raise StopAsyncIteration

    def __worker_threadsafe(self) -> None:
        """Stream the synchronous iterator to the queue and notify the async thread."""
        try:
            for item in self._iterator:
                self._queue.put(item)
                self._loop.call_soon_threadsafe(self._yield_semaphore.release)

                while self._queue.full() and not self._done_event.is_set():
                    with self._queue.not_full:
                        self._queue.not_full.wait(timeout=0.1)

                if self._done_event.is_set():
                    break
        finally:
            self._done_event.set()
            self._loop.call_soon_threadsafe(self._yield_semaphore.release)
