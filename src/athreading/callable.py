"""Function utilities."""

import asyncio
import queue
from collections.abc import Callable, Coroutine
from concurrent.futures import ThreadPoolExecutor, wait
from typing import ParamSpec, TypeVar

ParamsT = ParamSpec("ParamsT")
ReturnT = TypeVar("ReturnT")


def call(
    fn: Callable[ParamsT, ReturnT],
    executor: ThreadPoolExecutor | None = None,
) -> Callable[ParamsT, Coroutine[None, None, ReturnT]]:
    """Wraps a callable to a Coroutine for calling using a ThreadPoolExecutor.

    NOTE: must be called from the thread with running event loop.
    """
    done_event = asyncio.Event()
    q: queue.Queue[ReturnT] = queue.Queue()
    executor = executor if executor is not None else ThreadPoolExecutor()

    async def call_and_await_result(
        *args: ParamsT.args, **kwargs: ParamsT.kwargs
    ) -> ReturnT:
        loop = asyncio.get_running_loop()

        def call_handler(*args: ParamsT.args, **kwargs: ParamsT.kwargs) -> None:
            try:
                result = fn(*args, **kwargs)
                q.put(result)
            finally:
                loop.call_soon_threadsafe(done_event.set)

        future = executor.submit(call_handler, *args, **kwargs)
        await done_event.wait()
        wait([future])
        if future.cancelled():
            # TODO: untested
            raise asyncio.CancelledError()
        e = future.exception()
        if e is not None:
            raise e
        return q.get()

    return call_and_await_result


def wrap_callable(
    executor: ThreadPoolExecutor | None = None,
) -> Callable[
    [Callable[ParamsT, ReturnT]], Callable[ParamsT, Coroutine[None, None, ReturnT]]
]:
    """Wraps a callable to a Coroutine for calling using a ThreadPoolExecutor.

    NOTE: must be called from the thread with running event loop.
    """

    def decorator(
        fn: Callable[ParamsT, ReturnT]
    ) -> Callable[ParamsT, Coroutine[None, None, ReturnT]]:
        return call(fn, executor)

    return decorator
