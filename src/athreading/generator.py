"""Generator utilities."""

from __future__ import annotations

import asyncio
import functools
import queue
import sys
import threading
from collections.abc import Callable, Generator
from concurrent.futures import ThreadPoolExecutor
from types import TracebackType
from typing import Optional, TypeVar, Union

if sys.version_info >= (3, 12):
    from typing import ParamSpec, overload, override
else:  # pragma: not covered
    from typing_extensions import ParamSpec, overload, override

from athreading.aliases import AsyncGeneratorContext

__all__ = ["ThreadedAsyncGenerator", "generate"]


_ParamsT = ParamSpec("_ParamsT")
_YieldT = TypeVar("_YieldT")
_YieldT_co = TypeVar("_YieldT_co", covariant=True)
_SendT = TypeVar("_SendT")
_SendT_co = TypeVar("_SendT_co", covariant=True)


@overload
def generate(
    fn: None = None,
    *,
    buffer_maxsize: Optional[int] = None,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Callable[
    [Callable[_ParamsT, Generator[_YieldT_co, _SendT_co, None]]],
    Callable[_ParamsT, AsyncGeneratorContext[_YieldT_co, _SendT_co]],
]:
    ...


@overload
def generate(
    fn: Callable[_ParamsT, Generator[_YieldT_co, _SendT_co, None]],
    *,
    buffer_maxsize: Optional[int] = None,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Callable[_ParamsT, AsyncGeneratorContext[_YieldT_co, _SendT_co]]:
    ...


def generate(
    fn: Optional[Callable[_ParamsT, Generator[_YieldT_co, _SendT_co, None]]] = None,
    *,
    buffer_maxsize: Optional[int] = None,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Union[
    Callable[_ParamsT, AsyncGeneratorContext[_YieldT_co, _SendT_co]],
    Callable[
        [Callable[_ParamsT, Generator[_YieldT_co, _SendT_co, None]]],
        Callable[_ParamsT, AsyncGeneratorContext[_YieldT_co, _SendT_co]],
    ],
]:
    """Decorates a thread-safe synchronous generator with a ThreadPoolExecutor and exposes a
    thread-safe async generator.

    Args:
        fn: Function returning a generator. Defaults to None.
        buffer_maxsize: Maximum buffer size for background worker to pre-emptively pull
            data into. Defaults to None (no priming).
        executor: Defaults to None.

    Returns:
        Decorated generator function with lazy argument evaluation.
    """
    return (
        _create_generate_decorator(buffer_maxsize=buffer_maxsize, executor=executor)
        if fn is None
        else _create_generate_wrapper(
            fn, buffer_maxsize=buffer_maxsize, executor=executor
        )
    )


def _create_generate_wrapper(
    fn: Callable[_ParamsT, Generator[_YieldT_co, _SendT_co, None]],
    *,
    buffer_maxsize: Optional[int],
    executor: Optional[ThreadPoolExecutor],
) -> Callable[_ParamsT, AsyncGeneratorContext[_YieldT_co, _SendT_co]]:
    @functools.wraps(fn)
    def wrapper(
        *args: _ParamsT.args, **kwargs: _ParamsT.kwargs
    ) -> AsyncGeneratorContext[_YieldT_co, _SendT_co]:
        return ThreadedAsyncGenerator(fn(*args, **kwargs), buffer_maxsize, executor)

    return wrapper


def _create_generate_decorator(
    buffer_maxsize: Optional[int] = None,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Callable[
    [Callable[_ParamsT, Generator[_YieldT_co, _SendT_co, None]]],
    Callable[_ParamsT, AsyncGeneratorContext[_YieldT_co, _SendT_co]],
]:
    def decorator(
        fn: Callable[_ParamsT, Generator[_YieldT_co, _SendT_co, None]],
    ) -> Callable[_ParamsT, AsyncGeneratorContext[_YieldT_co, _SendT_co]]:
        return _create_generate_wrapper(
            fn, buffer_maxsize=buffer_maxsize, executor=executor
        )

    return decorator


class ThreadedAsyncGenerator(AsyncGeneratorContext[_YieldT, _SendT]):
    """Runs a thread-safe synchronous generator with a ThreadPoolExecutor and exposes a
    thread-safe AsyncGenerator.
    """

    def __init__(
        self,
        generator: Generator[_YieldT, _SendT, None],
        buffer_maxsize: Optional[int] = None,
        executor: Optional[ThreadPoolExecutor] = None,
    ):
        """Initilizes a ThreadedAsyncGenerator from a synchronous generator.

        Args:
            generator: Synchronous generator.
            buffer_maxsize: Maximum buffer size for background worker to pre-emptively pull
                data into. Defaults to None (no priming).
            executor: Shared thread pool instance. Defaults to ThreadPoolExecutor().
        """
        self._yield_semaphore = asyncio.Semaphore(0)
        self._done_event = threading.Event()
        self._send_queue: queue.Queue[Optional[_SendT]] = queue.Queue()
        self._yield_queue: queue.Queue[_YieldT] = queue.Queue(buffer_maxsize or 0)
        if buffer_maxsize:
            for _ in range(buffer_maxsize):
                self._send_queue.put(None)
        self._generator = generator
        self._executor = executor
        self._worker_future: Optional[asyncio.Future[None]] = None

    @override
    async def __aenter__(self) -> ThreadedAsyncGenerator[_YieldT, _SendT]:
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
        # move to aclose
        assert self._worker_future is not None
        self._done_event.set()
        self._yield_semaphore.release()
        self._send_queue.put(None)
        await self._worker_future

    @override
    async def __anext__(self) -> _YieldT:
        assert (
            self._worker_future is not None
        ), "Iteration started before entering context"
        self._send_queue.put(None)
        return await self.__get()

    @override
    async def asend(self, value: Optional[_SendT]) -> _YieldT:
        """Send a value to the generator send queue"""
        self._send_queue.put(value)
        return await self.__get()

    async def aclose(self) -> None:
        """Closes the generator"""
        self._generator.close()

    async def __get(self) -> _YieldT:
        if not self._done_event.is_set() or not self._yield_queue.empty():
            await self._yield_semaphore.acquire()
            if not self._yield_queue.empty():
                return self._yield_queue.get(False)
        raise StopAsyncIteration

    @override
    async def athrow(
        self,
        __typ: Union[type[BaseException], BaseException],
        __val: object = None,
        __tb: Optional[TracebackType] = None,
        /,
    ) -> _YieldT:
        """Raise a custom exception immediately from the generator"""
        if isinstance(__typ, BaseException):
            raise __typ
        return self._generator.throw(__typ, __val, __tb)

    def __worker_threadsafe(self) -> None:
        """Stream the synchronous itertor to the queue and notify the async thread."""
        try:
            while not self._done_event.is_set():
                sent = self._send_queue.get()
                if not self._done_event.is_set():
                    try:
                        item = self._generator.send(sent)  # type: ignore
                        self._yield_queue.put(item)
                        self._loop.call_soon_threadsafe(self._yield_semaphore.release)
                    except StopIteration:
                        break
        finally:
            self._done_event.set()
            self._loop.call_soon_threadsafe(self._yield_semaphore.release)
