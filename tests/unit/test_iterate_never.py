import asyncio
import sys
import time
from collections.abc import AsyncGenerator, AsyncIterator, Generator
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from time import sleep
from types import TracebackType
from typing import Callable, Optional, Union

if sys.version_info > (3, 12):
    from typing import override
else:
    from typing_extensions import override

import pytest

import athreading


class NeverGenerator(
    AbstractContextManager["NeverGenerator"], Generator[int, None, None]
):
    """A thread-safe context-bounded iterator that never yields
    or returns until the context is exitted."""

    def __init__(self, delay=0.0):
        self._is_running = True
        self._delay = delay

    def __enter__(self):
        return self

    def __exit__(self, __exc_type, __val, __tb):
        self.close()

    def __next__(self):
        while self._is_running:
            time.sleep(self._delay)
        raise StopIteration

    @override
    def send(self, value: Optional[int]) -> int:
        while self._is_running:
            time.sleep(self._delay)
        raise StopIteration

    @override
    def throw(
        self,
        __exc_type: Union[type[BaseException], BaseException],
        __val: object = None,
        __tb: Optional[TracebackType] = None,
    ) -> int:
        return 0

    @override
    def close(self):
        self._is_running = False


def test_iterate_never_context():
    executor = ThreadPoolExecutor()
    output = []

    with NeverGenerator(delay=0.1) as generator:

        def exit_after(time: float):
            sleep(time)
            generator.__exit__(None, None, None)

        future = executor.submit(exit_after, 2.0)

        for v in generator:
            output.append(v)

        assert future.done()

    assert output == []


@pytest.mark.parametrize(
    "streamcontext",
    [
        lambda iterator: athreading.ThreadedAsyncIterator(iterator),
        lambda iterator: athreading.ThreadedAsyncGenerator(iterator),
    ],
    ids=["iterate", "generate"],
)
@pytest.mark.asyncio
async def test_aiterate_never_context(
    streamcontext: Callable[[float], AbstractAsyncContextManager[AsyncIterator[int]]]
):
    output = []
    with NeverGenerator(delay=0.1) as generator:
        async with streamcontext(generator) as agenerator:

            async def aexit_after(time: float):
                await asyncio.sleep(time)
                # TODO: should the same as aiostream?
                # await agenerator.__aexit__(None, None, None)
                generator.__exit__(None, None, None)

            t = asyncio.create_task(aexit_after(2.0))
            async for v in agenerator:
                output.append(v)
            await t
    assert output == []
    await asyncio.wait_for(asyncio.get_running_loop().shutdown_default_executor(), 1.0)


@pytest.mark.parametrize(
    "streamcontext",
    [
        lambda iterator: athreading.ThreadedAsyncGenerator(iterator),
    ],
    ids=["generate"],
)
@pytest.mark.asyncio
async def test_aiterate_never_aclose(
    streamcontext: Callable[
        [float], AbstractAsyncContextManager[AsyncGenerator[int, None]]
    ]
):
    output = []
    with NeverGenerator(delay=0.1) as generator:
        async with streamcontext(generator) as agenerator:

            async def aclose_after(time: float):
                await asyncio.sleep(time)
                await agenerator.aclose()

            t = asyncio.create_task(aclose_after(2.0))
            async for v in agenerator:
                output.append(v)
            await t
    assert output == []
    await asyncio.wait_for(asyncio.get_running_loop().shutdown_default_executor(), 1.0)
