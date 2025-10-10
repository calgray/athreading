"""Iterator utilities."""

from __future__ import annotations

import asyncio
import functools
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from typing import TYPE_CHECKING, Optional, TypeVar, Union

from athreading.aliases import AsyncIteratorContext

if sys.version_info >= (3, 11):
    from typing import Concatenate, ParamSpec, overload
else:  # pragma: not covered
    from typing_extensions import Concatenate, ParamSpec, overload

if TYPE_CHECKING:
    from types import TracebackType

from collections.abc import Callable

_ParamsT = ParamSpec("_ParamsT")
_YieldT_co = TypeVar("_YieldT_co", covariant=True)
_YieldT = TypeVar("_YieldT")

CallableWithCallback = Callable[Concatenate[Callable[[_YieldT], None], _ParamsT], None]


@overload
def iterate_callback(
    fn: None = None,
    *,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Callable[
    [CallableWithCallback[_YieldT_co, _ParamsT]],
    Callable[_ParamsT, AsyncIteratorContext[_YieldT_co]],
]:
    ...


@overload
def iterate_callback(
    fn: CallableWithCallback[_YieldT_co, _ParamsT],
    *,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Callable[_ParamsT, AsyncIteratorContext[_YieldT_co]]:
    ...


def iterate_callback(  # type: ignore[misc]
    fn: Optional[CallableWithCallback[_YieldT_co, _ParamsT]] = None,
    *,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Union[
    Callable[_ParamsT, AsyncIteratorContext[_YieldT_co]],
    Callable[
        [CallableWithCallback[_YieldT_co, _ParamsT]],
        Callable[_ParamsT, AsyncIteratorContext[_YieldT_co]],
    ],
]:
    """Decorates a callback based generator with a ThreadPoolExecutor and exposes a thread-safe
    AsyncIterator.

    Args:
        fn: Function accepting a callback.
        Defaults to None.
        executor: Shared thread pool instance. Defaults to None (new threadpool).

    Returns:
        Decorated iterator function with lazy argument evaluation.
    """
    if fn is None:
        return _create_iterate_decorator(executor=executor)  # type: ignore[return-value]
    else:

        @functools.wraps(fn)
        def wrapper(
            *args: _ParamsT.args, **kwargs: _ParamsT.kwargs
        ) -> AsyncIteratorContext[_YieldT_co]:
            return CallbackThreadedAsyncIterator(
                lambda callback: fn(callback, *args, **kwargs), executor=executor
            )

        return wrapper


def _create_iterate_decorator(
    executor: Optional[ThreadPoolExecutor] = None,
) -> Callable[
    [CallableWithCallback[_YieldT_co, _ParamsT]],
    Callable[_ParamsT, AsyncIteratorContext[_YieldT_co]],
]:
    def decorator(
        fn: CallableWithCallback[_YieldT_co, _ParamsT],
    ) -> Callable[_ParamsT, AsyncIteratorContext[_YieldT_co]]:
        @functools.wraps(fn)
        def wrapper(
            *args: _ParamsT.args, **kwargs: _ParamsT.kwargs
        ) -> AsyncIteratorContext[_YieldT_co]:
            return CallbackThreadedAsyncIterator(
                lambda callback: fn(callback, *args, **kwargs), executor=executor
            )

        return wrapper

    return decorator  # type: ignore[return-value]


class CallbackThreadedAsyncIterator(AsyncIteratorContext[_YieldT]):
    """Thread-based async iterator using blocking call with callback."""

    def __init__(
        self,
        runner: Callable[[Callable[[_YieldT], None]], None],
        executor: Optional[ThreadPoolExecutor] = None,
    ):
        """Initializer.

        Args:
            runner: Function accepting a callback.
            executor: Shared thread pool instance. Defaults to None (new threadpool).
        """
        self._yield_semaphore = asyncio.Semaphore(0)
        self._done_event = threading.Event()
        self._queue: asyncio.Queue[
            tuple[_YieldT, None] | tuple[None, BaseException]
        ] = asyncio.Queue()
        self._runner = runner
        self._executor = executor
        self._stream_future: Optional[asyncio.Future[None]] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def __aenter__(self) -> CallbackThreadedAsyncIterator[_YieldT]:
        self._loop = asyncio.get_running_loop()
        self._stream_future = asyncio.create_task(self.__arun())
        return self

    async def __aexit__(
        self,
        __exc_type: Optional[type[BaseException]],
        __val: Optional[BaseException],
        __tb: Optional[TracebackType],
        /,
    ) -> None:
        assert self._stream_future is not None
        self._done_event.set()
        self._yield_semaphore.release()
        if not self._stream_future.done():
            self._stream_future.cancel()
            with suppress(asyncio.CancelledError):
                await self._stream_future

    async def __anext__(self) -> _YieldT:
        await self._yield_semaphore.acquire()

        if self._done_event.is_set() and self._queue.empty():
            raise StopAsyncIteration

        value_exc = await self._queue.get()

        if value_exc[1] is not None:
            # Raise the stored exception exactly where it happened
            raise value_exc[1]
        # Normal value
        return value_exc[0]

    def __callback_threadsafe(self, value: _YieldT) -> None:
        assert self._loop is not None

        def put_value() -> None:
            self._queue.put_nowait((value, None))
            self._yield_semaphore.release()

        self._loop.call_soon_threadsafe(put_value)

    def __callback_threadsafe_with_error(self, exc: BaseException) -> None:
        assert self._loop is not None

        def put_error() -> None:
            self._queue.put_nowait((None, exc))
            self._yield_semaphore.release()

        self._loop.call_soon_threadsafe(put_error)

    async def __arun(self) -> None:
        try:
            assert self._loop is not None

            def runner_wrapper(cb: Callable[[_YieldT], None]) -> None:
                try:
                    self._runner(cb)
                except BaseException as exc:
                    # Push exception immediately into the queue for __anext__
                    self.__callback_threadsafe_with_error(exc)
                    # Optionally re-raise or just exit
                    # raise

            await self._loop.run_in_executor(
                self._executor, runner_wrapper, self.__callback_threadsafe
            )

        finally:
            self._done_event.set()
            self._yield_semaphore.release()
