import asyncio
import time
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractContextManager
from time import sleep
from types import TracebackType

import pytest
from typing_extensions import override

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
        self._is_running = False

    def __next__(self):
        while self._is_running:
            time.sleep(self._delay)
        raise StopIteration

    @override
    def send(self, value: int | None) -> int:
        while self._is_running:
            time.sleep(self._delay)
        raise StopIteration

    @override
    def throw(
        self,
        __exc_type: type[BaseException] | BaseException,
        __val: BaseException | object = None,
        __tb: TracebackType | None = None,
    ) -> int:
        return 0


def test_iterate_never():
    executor = ThreadPoolExecutor()
    output = []
    with NeverGenerator(delay=0.1) as never_iter:

        def exit_after(context: AbstractContextManager, time: float):
            sleep(time)
            context.__exit__(None, None, None)

        future = executor.submit(exit_after, never_iter, 2.0)

        for v in never_iter:
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
async def test_aiterate_never(streamcontext):
    output = []
    with NeverGenerator(delay=0.1) as iterator:
        async with streamcontext(iterator) as never_iter:

            async def aexit_after(context: AbstractContextManager, time: float):
                await asyncio.sleep(time)
                context.__exit__(None, None, None)

            t = asyncio.create_task(aexit_after(iterator, 2.0))
            async for v in never_iter:
                output.append(v)
            await t
    assert output == []
    await asyncio.wait_for(asyncio.get_running_loop().shutdown_default_executor(), 1.0)
