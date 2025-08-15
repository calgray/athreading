"""Iterator utilities."""

from __future__ import annotations

import asyncio
import functools
import sys
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Protocol, TypeVar, Union

from athreading.aliases import AsyncIteratorContext

if sys.version_info > (3, 12):
    from typing import ParamSpec, overload, override
else:  # pragma: not covered
    from typing_extensions import ParamSpec, overload, override


_ParamsT = ParamSpec("_ParamsT")
_YieldT = TypeVar("_YieldT")


class CallableWithCallback(Protocol[_ParamsT, _YieldT]):  # type: ignore
    """Callback protocol where the callback is always the first positional argument."""

    def __call__(
        self,
        callback: Callable[[_YieldT], None],
        *args: _ParamsT.args,
        **kwargs: _ParamsT.kwargs,
    ):
        """Call the callable."""
        ...


@overload
def iterate_callback(
    fn: None = None,
    *,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Callable[
    [CallableWithCallback[_ParamsT, _YieldT]],
    Callable[_ParamsT, AsyncIteratorContext[_YieldT]],
]:
    ...


@overload
def iterate_callback(
    fn: CallableWithCallback[_ParamsT, _YieldT],
    *,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Callable[_ParamsT, AsyncIteratorContext[_YieldT]]:
    ...


def iterate_callback(
    fn: Optional[CallableWithCallback[_ParamsT, _YieldT]] = None,
    *,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Union[
    Callable[_ParamsT, AsyncIteratorContext[_YieldT]],
    Callable[
        [CallableWithCallback[_ParamsT, _YieldT]],
        Callable[_ParamsT, AsyncIteratorContext[_YieldT]],
    ],
]:
    """Decorates a callback based generator with a ThreadPoolExecutor and exposes a thread-safe
    AsyncIterator.

    Args:
        fn: Function accepting a callback.
        Defaults to None.
        executor: Defaults to None.

    Returns:
        Callable[ParamsT, AsyncIteratorContext[_YieldT]]: Decorated iterator function with lazy
        argument evaluation.
    """
    if fn is None:
        return _create_iterate_decorator(executor=executor)
    else:

        @functools.wraps(fn)
        def wrapper(
            *args: _ParamsT.args, **kwargs: _ParamsT.kwargs
        ) -> AsyncIteratorContext[_YieldT]:
            return CallbackThreadedAsyncIterator(
                lambda callback: fn(callback, *args, **kwargs), executor=executor
            )

        return wrapper


def _create_iterate_decorator(
    executor: Optional[ThreadPoolExecutor] = None,
) -> Callable[
    [CallableWithCallback[_ParamsT, _YieldT]],
    Callable[_ParamsT, AsyncIteratorContext[_YieldT]],
]:
    def decorator(
        fn: CallableWithCallback[_ParamsT, _YieldT],
    ) -> Callable[_ParamsT, AsyncIteratorContext[_YieldT]]:
        @functools.wraps(fn)
        def wrapper(
            *args: _ParamsT.args, **kwargs: _ParamsT.kwargs
        ) -> AsyncIteratorContext[_YieldT]:
            return CallbackThreadedAsyncIterator(
                lambda callback: fn(callback, *args, **kwargs), executor=executor
            )

        return wrapper

    return decorator


class CallbackThreadedAsyncIterator(AsyncIteratorContext[_YieldT]):
    def __init__(
        self,
        runner: Callable[[Callable[[_YieldT], None]], None],
        executor: Optional[ThreadPoolExecutor] = None,
    ):
        self._yield_semaphore = asyncio.Semaphore(0)
        self._done_event = threading.Event()
        # Now queue holds tuples: (value, exception)
        self._queue: asyncio.Queue[
            Tuple[Optional[_YieldT], Optional[BaseException]]
        ] = asyncio.Queue()
        self._runner = runner
        self._executor = executor
        self._stream_future: Optional[asyncio.Future[None]] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def __aenter__(self) -> CallbackThreadedAsyncIterator[_YieldT]:
        self._loop = asyncio.get_running_loop()
        self._stream_future = asyncio.create_task(self.__arun())
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        assert self._stream_future is not None
        self._done_event.set()
        self._yield_semaphore.release()
        if not self._stream_future.done():
            self._stream_future.cancel()
            try:
                await self._stream_future
            except asyncio.CancelledError:
                pass

    async def __anext__(self) -> _YieldT:
        await self._yield_semaphore.acquire()

        if self._done_event.is_set() and self._queue.empty():
            raise StopAsyncIteration

        value, exc = await self._queue.get()

        if exc is not None:
            # Raise the stored exception exactly where it happened
            raise exc

        # Normal value
        return value

    def __callback_threadsafe(self, value: _YieldT) -> None:
        assert self._loop is not None

        def put_value():
            self._queue.put_nowait((value, None))
            self._yield_semaphore.release()

        self._loop.call_soon_threadsafe(put_value)

    def __callback_threadsafe_with_error(self, exc: BaseException) -> None:
        # Optionally a separate method or inside callback wrapper:
        assert self._loop is not None

        def put_error():
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
