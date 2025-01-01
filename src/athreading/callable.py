"""Function utilities."""

import asyncio
import functools
import sys
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional, TypeVar, Union, overload

if sys.version_info[:2] > (3, 9):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec


ParamsT = ParamSpec("ParamsT")
ReturnT = TypeVar("ReturnT")


@overload
def call(
    fn: None = None,
    *,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Callable[
    [Callable[ParamsT, ReturnT]], Callable[ParamsT, Coroutine[None, None, ReturnT]]
]:
    ...


@overload
def call(
    fn: Callable[ParamsT, ReturnT],
) -> Callable[ParamsT, Coroutine[None, None, ReturnT]]:
    ...


def call(
    fn: Optional[Callable[ParamsT, ReturnT]] = None,
    *,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Union[
    Callable[ParamsT, Coroutine[None, None, ReturnT]],
    Callable[
        [Callable[ParamsT, ReturnT]], Callable[ParamsT, Coroutine[None, None, ReturnT]]
    ],
]:
    """Wraps a thread-safe synchronous Callable with an ThreadPoolExecutor and exposes a
    thread-safe asynchronous Callable.

    Args:
        fn (Callable[ParamsT, ReturnT], optional): thread-safe synchronous function. Defaults to
        None.
        executor: (ThreadPoolExecutor, optional): Defaults to asyncio default executor.

    Returns:
        Callable[ParamsT, Coroutine[None, None, ReturnT]]: thread-safe asynchronous function.
    """
    if fn is None:
        return _create_call_decorator(executor=executor)
    else:
        return _call(fn, executor=executor)


def _create_call_decorator(
    executor: Optional[ThreadPoolExecutor] = None,
) -> Callable[
    [Callable[ParamsT, ReturnT]], Callable[ParamsT, Coroutine[None, None, ReturnT]]
]:
    def decorator(
        fn: Callable[ParamsT, ReturnT],
    ) -> Callable[ParamsT, Coroutine[None, None, ReturnT]]:
        return _call(fn, executor=executor)

    return decorator


def _call(
    fn: Callable[ParamsT, ReturnT],
    *,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Callable[ParamsT, Coroutine[None, None, ReturnT]]:
    """Wraps a callable to a Coroutine for calling using a ThreadPoolExecutor."""

    @functools.wraps(fn)
    async def wrapper(*args: ParamsT.args, **kwargs: ParamsT.kwargs) -> ReturnT:
        return await asyncio.get_running_loop().run_in_executor(
            executor, functools.partial(fn, *args, **kwargs)
        )

    return wrapper
