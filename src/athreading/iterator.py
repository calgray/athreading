"""Iterator utilities."""


from __future__ import annotations

import asyncio
import queue
import threading
from collections.abc import AsyncGenerator, AsyncIterator, Iterable
from concurrent.futures import Future, ThreadPoolExecutor, wait
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from types import TracebackType
from typing import TypeVar

from overrides import override

YieldT = TypeVar("YieldT")


def iterate(
    iterable: Iterable[YieldT],
    executor: ThreadPoolExecutor | None = None,
) -> ThreadedAsyncIterator[YieldT]:
    """Wraps a synchronous generator to an AsyncGenerator for running using a ThreadPoolExecutor.

    Args:
        iterable (Iterable[YieldT]): _description_
        executor (ThreadPoolExecutor | None, optional): _description_. Defaults to None.

    Returns:
        ThreadedAsyncIterator[YieldT]: _description_
    """
    return ThreadedAsyncIterator(iterable, executor)


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
        for item in iterable:
            yield_queue.put(item)
            loop.call_soon_threadsafe(semaphore.release)
            if event.is_set():
                break
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
        iterable: Iterable[YieldT],
        executor: ThreadPoolExecutor | None = None,
    ):
        """Initilizes a ThreadedAsyncIterator from a synchronous iterator.

        Args:
            iterable (Generator[ItemT, SendT, None]): Synchronous iterable.
            executor (ThreadPoolExecutor, optional): Shared thread pool instance. Defaults to
            ThreadPoolExecutor().
        """
        self._semaphore = asyncio.Semaphore(0)
        self._event = threading.Event()
        self._queue: queue.Queue[YieldT] = queue.Queue()
        self._iterable = iterable
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
        self._event.set()
        self._semaphore.release()
        wait([self._stream_future])

    async def __anext__(self) -> YieldT:
        assert (
            self._stream_future is not None
        ), "Iterator started before entering context"
        if not self._event.is_set() or not self._queue.empty():
            await self._semaphore.acquire()
            if not self._queue.empty():
                return self._queue.get(False)
        raise StopAsyncIteration

    def __stream(self) -> None:
        for item in self._iterable:
            self._queue.put(item)
            self._loop.call_soon_threadsafe(self._semaphore.release)
            if self._event.is_set():
                break
        self._event.set()
        self._loop.call_soon_threadsafe(self._semaphore.release)
