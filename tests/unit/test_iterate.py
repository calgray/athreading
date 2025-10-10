from __future__ import annotations

import asyncio
import sys
import time
from collections.abc import AsyncGenerator, Generator
from concurrent.futures import ThreadPoolExecutor
from typing import Union

import async_timeout
import pytest

import athreading

if sys.version_info >= (3, 10):
    from contextlib import nullcontext
else:
    from tests.compat import nullcontext

TestData = Union[int, str, float, None]
TEST_VALUES: list[TestData] = [1, None, "", 2.0]

CUSTOM_EXECUTOR = ThreadPoolExecutor()


def generator(delay=0.0, repeats=1) -> Generator[TestData, TestData | None, None]:
    for _ in range(repeats):
        for item in TEST_VALUES:
            time.sleep(delay)
            yield item


async def agenerate_naive(delay=0.0, repeats=1) -> AsyncGenerator[TestData, None]:
    for value in generator(delay, repeats):
        yield value
        await asyncio.sleep(0.0)


@athreading.iterate(executor=CUSTOM_EXECUTOR)
def aiterate(delay=0.0, repeats=1):
    yield from generator(delay, repeats)


@athreading.iterate()
def aiterate_simpler(delay=0.0, repeats=1):
    yield from generator(delay, repeats)


@athreading.iterate
def aiterate_simplest(delay=0.0, repeats=1):
    yield from generator(delay, repeats)


@athreading.generate(executor=CUSTOM_EXECUTOR)
def agenerate(delay=0.0, repeats=1):
    yield from generator(delay, repeats)


@athreading.generate()
def agenerate_simpler(delay=0.0, repeats=1):
    yield from generator(delay, repeats)


@athreading.generate
def agenerate_simplest(delay=0.0, repeats=1):
    yield from generator(delay, repeats)


@pytest.mark.parametrize("worker_delay", [0.0, 0.1])
@pytest.mark.parametrize("main_delay", [0.0, 0.1])
@pytest.mark.parametrize(
    "streamcontext",
    [
        lambda delay: nullcontext(agenerate_naive(delay)),
        lambda delay: athreading.iterate(generator)(delay),
        lambda delay: aiterate(delay),
        lambda delay: aiterate_simpler(delay),
        lambda delay: aiterate_simplest(delay),
        lambda delay: athreading.generate(generator)(delay),
        lambda delay: agenerate(delay),
        lambda delay: agenerate_simpler(delay),
        lambda delay: agenerate_simplest(delay),
    ],
    ids=[
        "naive",
        "iterate",
        "aiterate",
        "aiterate_simpler",
        "aiterate_simplest",
        "generate",
        "agenerate",
        "agenerate_simpler",
        "agenerate_simplest",
    ],
)
@pytest.mark.asyncio
async def test_iterate_all(streamcontext, worker_delay, main_delay):
    output = []
    async with streamcontext(worker_delay) as stream:
        async for v in stream:
            await asyncio.sleep(main_delay)
            output.append(v)
    assert output == TEST_VALUES
    await asyncio.wait_for(asyncio.get_running_loop().shutdown_default_executor(), 1.0)


@pytest.mark.parametrize(
    "streamcontext",
    [
        lambda delay, e: athreading.iterate(generator, executor=e)(delay),
        lambda delay, e: athreading.iterate(executor=e)(generator)(delay),
        lambda delay, e: athreading.generate(generator, executor=e)(delay),
        lambda delay, e: athreading.generate(executor=e)(generator)(delay),
    ],
    ids=["iterate", "iterate2", "generate", "generate2"],
)
@pytest.mark.asyncio
async def test_iterate_all_parallel(streamcontext):
    max_workers = 8
    worker_delay = 1.0
    executor = ThreadPoolExecutor(max_workers=max_workers)

    async def process():
        outputs = []
        async with streamcontext(worker_delay, executor) as stream:
            outputs = [value async for value in stream]
        assert outputs == TEST_VALUES

    # set timeout between thread time and total thread time to ensure
    # execution exhibits parallelism for thread sleeps
    thread_time = worker_delay * len(TEST_VALUES)
    total_thread_time = max_workers * thread_time
    timeout = thread_time + 0.5 * (total_thread_time - thread_time)

    await asyncio.wait_for(
        asyncio.gather(*[process() for _ in range(max_workers)]),
        timeout=timeout,
    )
    await asyncio.wait_for(asyncio.get_running_loop().shutdown_default_executor(), 1.0)


@pytest.mark.parametrize(
    "streamcontext",
    [
        lambda buffer_maxsize: athreading.iterate(
            generator, buffer_maxsize=buffer_maxsize
        )(),
        lambda buffer_maxsize: athreading.generate(
            generator, buffer_maxsize=buffer_maxsize
        )(),
    ],
    ids=[
        "iterate",
        "generate",
    ],
)
@pytest.mark.parametrize("buffer_maxsize", [None, 1, 2, 3, 5, 6])
@pytest.mark.asyncio
async def test_iterate_buffer_maxsize(streamcontext, buffer_maxsize: int | None):
    """test background worker stops at the buffer maxsize

    Args:
        streamcontext: athreading iterator.
        buffer_maxsize: max amount of buffering whilest the iterator isn't started
    """

    ctx = streamcontext(buffer_maxsize or 0)
    stream = await ctx.__aenter__()

    # NOTE: impossible to buffer infinitely with AsyncGenerator
    if buffer_maxsize is None and isinstance(stream, AsyncGenerator):
        buffer_maxsize = 0

    worker_time_s = 0.005
    await asyncio.sleep(worker_time_s)
    async with async_timeout.timeout(1.0):
        await ctx.__aexit__(None, None, None)

    output = [value async for value in stream]

    assert output == TEST_VALUES[:buffer_maxsize]
    await asyncio.wait_for(asyncio.get_running_loop().shutdown_default_executor(), 1.0)
