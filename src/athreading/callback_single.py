"""Callback utilities."""

from __future__ import annotations

import asyncio
import functools
import sys
from collections.abc import Awaitable
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, TypeVar, Union

if sys.version_info >= (3, 11):
    from typing import Concatenate, ParamSpec, overload
else:  # pragma: not covered
    from typing_extensions import Concatenate, ParamSpec, overload


from collections.abc import Callable

_ParamsT = ParamSpec("_ParamsT")
_T_co = TypeVar("_T_co", covariant=True)
_T = TypeVar("_T")

CallableWithCallback = Callable[Concatenate[Callable[[_T_co], None], _ParamsT], None]


@overload
def single_callback(
    fn: None = None, *, executor: Optional[ThreadPoolExecutor] = None
) -> Callable[
    [CallableWithCallback[_T_co, _ParamsT]], Callable[_ParamsT, Awaitable[_T_co]]
]:
    ...


@overload
def single_callback(
    fn: CallableWithCallback[_T_co, _ParamsT],
    *,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Callable[_ParamsT, Awaitable[_T_co]]:
    ...


def single_callback(
    fn: Optional[CallableWithCallback[_T_co, _ParamsT]] = None,
    *,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Union[
    Callable[_ParamsT, Awaitable[_T_co]],
    Callable[
        [CallableWithCallback[_T_co, _ParamsT]], Callable[_ParamsT, Awaitable[_T_co]]
    ],
]:
    """Decorates a callback based generator with a ThreadPoolExecutor and exposes a thread-safe
    AsyncIterator.

    Args:
        fn: Function accepting a callback. Defaults to None.
        executor: Defaults to None.

    Returns:
        Decorated iterator function with lazy argument evaluation.
    """
    return (
        _create_callback_decorator(executor=executor)
        if fn is None
        else _create_callback_wrapper(fn, executor=executor)
    )


def _create_callback_wrapper(
    fn: CallableWithCallback[_T_co, _ParamsT],
    *,
    executor: Optional[ThreadPoolExecutor],
) -> Callable[_ParamsT, Awaitable[_T_co]]:
    @functools.wraps(fn)
    def wrapper(*args: _ParamsT.args, **kwargs: _ParamsT.kwargs) -> Awaitable[_T_co]:
        return await_callback(fn, executor=executor)(*args, **kwargs)

    return wrapper


def _create_callback_decorator(
    *,
    executor: Optional[ThreadPoolExecutor],
) -> Callable[
    [CallableWithCallback[_T_co, _ParamsT]], Callable[_ParamsT, Awaitable[_T_co]]
]:
    def decorator(
        fn: CallableWithCallback[_T_co, _ParamsT],
    ) -> Callable[_ParamsT, Awaitable[_T_co]]:
        return _create_callback_wrapper(fn, executor=executor)

    return decorator


def await_callback(
    fn: CallableWithCallback[_T, _ParamsT],
    *,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Callable[_ParamsT, Awaitable[_T]]:
    """Transform a function where the first argument is a callback into
    an async function, returning the callback's result as an awaitable.

    If executor is provided, runs `fn` in that executor.
    """

    async def wrapper(*args: _ParamsT.args, **kwargs: _ParamsT.kwargs) -> _T:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[_T] = loop.create_future()

        def callback(value: _T) -> None:
            if not fut.done():
                fut.set_result(value)

        def run() -> None:
            fn(callback, *args, **kwargs)

        await loop.run_in_executor(executor, run)
        return await fut

    return wrapper
