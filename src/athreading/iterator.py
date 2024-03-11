"""Iterator utilities."""


from __future__ import annotations

import asyncio
import queue
import threading
from collections.abc import AsyncGenerator, AsyncIterator, Callable, Iterable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor, wait
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from types import TracebackType
from typing import ParamSpec, TypeVar, overload

from overrides import override

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
    """_summary_

    Args:
        fn (Callable[..., Iterator[YieldT]]): _description_
        executor (ThreadPoolExecutor | None, optional): _description_. Defaults to None.

    Returns:
        ThreadedAsyncIterator[YieldT]: _description_
    """
    if fn is None:
        return _iterate_decorator(executor=executor)
    else:

        def wrapper(
            *args: ParamsT.args, **kwargs: ParamsT.kwargs
        ) -> ThreadedAsyncIterator[YieldT]:
            return _iterate(fn(*args, **kwargs), executor=executor)

        return wrapper


def _iterate(
    iterator: Iterator[YieldT],
    executor: ThreadPoolExecutor | None = None,
) -> ThreadedAsyncIterator[YieldT]:
    """Wraps a synchronous Iterator to an AsyncIterator for running using a ThreadPoolExecutor.

    Args:
        iterable (Iterable[YieldT]): _description_
        executor (ThreadPoolExecutor | None, optional): _description_. Defaults to None.

    Returns:
        ThreadedAsyncIterator[YieldT]: _description_
    """
    return ThreadedAsyncIterator(iterator, executor)


def _iterate_decorator(
    executor: ThreadPoolExecutor | None = None,
) -> Callable[
    [Callable[ParamsT, Iterator[YieldT]]],
    Callable[ParamsT, ThreadedAsyncIterator[YieldT]],
]:
    """_summary_

    Args:
        fn (Callable[ParamsT, Iterable[YieldT]]): _description_
        executor (ThreadPoolExecutor | None, optional): _description_. Defaults to None.

    Returns:
        Callable[ParamsT, ThreadedAsyncIterator[YieldT]]: _description_
    """

    def decorator(
        fn: Callable[ParamsT, Iterator[YieldT]],
    ) -> Callable[ParamsT, ThreadedAsyncIterator[YieldT]]:
        def wrapper(
            *args: ParamsT.args, **kwargs: ParamsT.kwargs
        ) -> ThreadedAsyncIterator[YieldT]:
            return _iterate(fn(*args, **kwargs), executor)

        return wrapper

    return decorator


@asynccontextmanager
async def _fiterate(
    iterable: Iterable[YieldT], executor: ThreadPoolExecutor | None = None
) -> AsyncGenerator[AsyncIterator[YieldT], None]:
    """Wraps a synchronous generator to an AsyncGenerator for running using a ThreadPoolExecutor.

    Args:
        iterable (Iterable[ItemT]): a synchronously iterable sequence.
        executor (ThreadPoolExecutor, optional): shared executor pool. Defaults to
        concurrent.futures.ThreadPoolExecutor().

    Returns:
        AsyncGenerator[ItemT, None]: Async iterator to the results of the iterable running in the
        executor.

    Yields:
        ItemT: item from the iterable.
    """
    semaphore = asyncio.Semaphore(0)
    event = threading.Event()
    yield_queue: queue.Queue[YieldT] = queue.Queue()
    loop = asyncio.get_running_loop()
    executor = executor if executor is not None else ThreadPoolExecutor()

    def stream() -> None:
        try:
            for item in iterable:
                yield_queue.put(item)
                loop.call_soon_threadsafe(semaphore.release)
                if event.is_set():
                    break
        finally:
            event.set()
            loop.call_soon_threadsafe(semaphore.release)

    async def async_genenerator() -> AsyncGenerator[YieldT, None]:
        while not event.is_set() or not yield_queue.empty():
            await semaphore.acquire()
            if not yield_queue.empty():
                yield yield_queue.get(False)
            else:
                break

    stream_future = executor.submit(stream)
    yield async_genenerator()
    event.set()
    semaphore.release()
    wait([stream_future])


class ThreadedAsyncIterator(
    AbstractAsyncContextManager["ThreadedAsyncIterator[YieldT]"], AsyncIterator[YieldT]
):
    """Wraps a synchronous generator to an AsyncGenerator for running using a ThreadPoolExecutor.

    Args:
        iterable (Iterable[ItemT]): a synchronously iterable sequence.
        executor (ThreadPoolExecutor, optional): shared executor pool. Defaults to
        concurrent.futures.ThreadPoolExecutor().

    Returns:
        AsyncGenerator[ItemT, None]: Async iterator to the results of the iterable running in the
        executor.

    Yields:
        ItemT: item from the iterable.
    """

    def __init__(
        self,
        iterator: Iterator[YieldT],
        executor: ThreadPoolExecutor | None = None,
    ):
        """Initilizes a ThreadedAsyncIterator from a synchronous iterator.

        Args:
            iterator (Generator[ItemT, SendT, None]): Synchronous iterable.
            executor (ThreadPoolExecutor, optional): Shared thread pool instance. Defaults to
            ThreadPoolExecutor().
        """
        self._yield_semaphore = asyncio.Semaphore(0)
        self._done_event = threading.Event()
        self._queue: queue.Queue[YieldT] = queue.Queue()
        self._iterator = iterator
        self._executor = executor if executor is not None else ThreadPoolExecutor()
        self._stream_future: Future[None] | None = None

    @override
    async def __aenter__(self) -> ThreadedAsyncIterator[YieldT]:
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
        wait([self._stream_future])

    async def __anext__(self) -> YieldT:
        assert (
            self._stream_future is not None
        ), "Iterator started before entering context"
        if not self._done_event.is_set() or not self._queue.empty():
            # still waiting for items
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
