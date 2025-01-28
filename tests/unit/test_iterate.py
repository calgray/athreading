import asyncio
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

import athreading

if sys.version_info > (3, 10):
    from contextlib import nullcontext
else:
    from tests.compat import nullcontext

TEST_VALUES = [1, None, "", 2.0]

custom_executor = ThreadPoolExecutor()


def generator(delay=0.0, repeats=1):
    for _ in range(repeats):
        for item in TEST_VALUES:
            time.sleep(delay)
            yield item


async def agenerate_naive(delay=0.0, repeats=1):
    for value in generator(delay, repeats):
        yield value
        await asyncio.sleep(0.0)


@athreading.iterate(executor=custom_executor)
def aiterate(delay=0.0, repeats=1):
    yield from generator(delay, repeats)


@athreading.iterate()
def aiterate_simpler(delay=0.0, repeats=1):
    yield from generator(delay, repeats)


@athreading.iterate
def aiterate_simplest(delay=0.0, repeats=1):
    yield from generator(delay, repeats)


@athreading.generate(executor=custom_executor)
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
            time.sleep(main_delay)
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
            async for value in stream:
                outputs.append(value)
        assert outputs == TEST_VALUES

    # set timeout between thread time and total thread time to ensure
    # execution exhibits parallelism for thread sleeps
    thread_time = worker_delay * len(TEST_VALUES)
    total_thread_time = max_workers * thread_time
    timeout = thread_time + 0.5 * (total_thread_time - thread_time)

    await asyncio.wait_for(
        asyncio.gather(*[process() for i in range(max_workers)]),
        timeout=timeout,
    )
    await asyncio.wait_for(asyncio.get_running_loop().shutdown_default_executor(), 1.0)
