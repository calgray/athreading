"""Function utilities."""

import asyncio
import queue
from collections.abc import Callable, Coroutine
from concurrent.futures import ThreadPoolExecutor, wait
from typing import ParamSpec, TypeVar

ParamsT = ParamSpec("ParamsT")
ReturnT = TypeVar("ReturnT")


def call(
    f: Callable[ParamsT, ReturnT],
    executor: ThreadPoolExecutor | None = None,
) -> Callable[ParamsT, Coroutine[None, None, ReturnT]]:
    """Wraps a callable to a Coroutine for calling using a ThreadPoolExecutor."""
    event = asyncio.Event()
    q: queue.Queue[ReturnT] = queue.Queue()
    loop = asyncio.get_running_loop()
    executor = executor if executor is not None else ThreadPoolExecutor()

    def call_handler(*args: ParamsT.args, **kwargs: ParamsT.kwargs) -> None:
        result = f(*args, **kwargs)
        q.put(result)
        loop.call_soon_threadsafe(event.set)

    async def call_and_await_result(
        *args: ParamsT.args, **kwargs: ParamsT.kwargs
    ) -> ReturnT:
        invoke_future = executor.submit(call_handler, *args, **kwargs)
        await event.wait()
        wait([invoke_future])
        return q.get()

    return call_and_await_result
