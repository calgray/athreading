"""Function utilities."""

import asyncio
import queue
from collections.abc import Callable, Coroutine
from concurrent.futures import ThreadPoolExecutor, wait
from typing import ParamSpec, TypeVar, overload

ParamsT = ParamSpec("ParamsT")
ReturnT = TypeVar("ReturnT")


@overload
def call(
    fn: None = None,
    *,
    executor: ThreadPoolExecutor | None = None,
) -> Callable[
    [Callable[ParamsT, ReturnT]], Callable[ParamsT, Coroutine[None, None, ReturnT]]
]:
    pass


@overload
def call(
    fn: Callable[ParamsT, ReturnT],
) -> Callable[ParamsT, Coroutine[None, None, ReturnT]]:
    pass


def call(
    fn: Callable[ParamsT, ReturnT] | None = None,
    *,
    executor: ThreadPoolExecutor | None = None,
) -> (
    Callable[ParamsT, Coroutine[None, None, ReturnT]]
    | Callable[
        [Callable[ParamsT, ReturnT]], Callable[ParamsT, Coroutine[None, None, ReturnT]]
    ]
):
    """Wraps a callable to a Coroutine for calling using a ThreadPoolExecutor.

    NOTE: must be called from the thread with running event loop.
    """
    if fn is None:
        return _call_decorator(executor=executor)
    else:
        return _call_simple(fn, executor=executor)


def _call_simple(
    fn: Callable[ParamsT, ReturnT],
    *,
    executor: ThreadPoolExecutor | None = None,
) -> Callable[ParamsT, Coroutine[None, None, ReturnT]]:
    """Wraps a callable to a Coroutine for calling using a ThreadPoolExecutor.

    Args:
        fn (Callable[ParamsT, ReturnT]): _description_
        executor (ThreadPoolExecutor | None, optional): _description_. Defaults to None.

    Returns:
        Callable[ParamsT, Coroutine[None, None, ReturnT]]: _description_
    """
    executor = executor if executor is not None else ThreadPoolExecutor()

    async def wrapper(*args: ParamsT.args, **kwargs: ParamsT.kwargs) -> ReturnT:
        return await asyncio.wrap_future(executor.submit(fn, *args, **kwargs))

    return wrapper


def _call(
    fn: Callable[ParamsT, ReturnT],
    *,
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
        e = future.exception()
        if e is not None:
            raise e
        return q.get()

    return call_and_await_result


def _call_decorator(
    executor: ThreadPoolExecutor | None = None,
) -> Callable[
    [Callable[ParamsT, ReturnT]], Callable[ParamsT, Coroutine[None, None, ReturnT]]
]:
    """Wraps a callable to a Coroutine for calling using a ThreadPoolExecutor.

    NOTE: must be called from the thread with running event loop.
    """

    def decorator(
        fn: Callable[ParamsT, ReturnT],
    ) -> Callable[ParamsT, Coroutine[None, None, ReturnT]]:
        return _call_simple(fn, executor=executor)

    return decorator
