import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

import aiostream
import aiostream.stream as astream
import pytest

import athreading

TEST_VALUES = [1, None, "", 2.0]


def generate(delay=0.0, repeats=1):
    for _ in range(repeats):
        for item in TEST_VALUES:
            time.sleep(delay)
            yield item


@pytest.mark.parametrize("worker_delay", [0.0, 0.2])
@pytest.mark.parametrize("main_delay", [0.0, 0.2])
@pytest.mark.parametrize(
    "streamcontext",
    [
        lambda delay: aiostream.stream.iterate(generate(delay)).stream(),
        lambda delay: athreading.fiterate(generate(delay)),
        lambda delay: athreading.iterate(generate(delay)),
        lambda delay: athreading.generate(generate(delay)),
    ],
    ids=["aiostream", "fiterate", "iterate", "generate"],
)
@pytest.mark.asyncio
async def test_threaded_async_iterate_single(streamcontext, worker_delay, main_delay):
    output = []
    async with streamcontext(worker_delay) as stream:
        async for v in stream:
            time.sleep(main_delay)
            output.append(v)
    assert output == TEST_VALUES


@pytest.mark.parametrize(
    "streamcontext",
    [
        lambda delay, e: athreading.fiterate(generate(delay), e),
        lambda delay, e: athreading.iterate(generate(delay), e),
        lambda delay, e: athreading.generate(generate(delay), e),
    ],
    ids=["fiterate", "iterate", "generate"],
)
@pytest.mark.asyncio
async def test_threaded_async_iterate_parallel(streamcontext):
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


def generate_infinite(delay=0.0):
    item = 0
    while True:
        time.sleep(delay)
        item += 1
        yield item


@pytest.mark.parametrize("worker_delay", [0.0, 0.2])
@pytest.mark.parametrize("main_delay", [0.0, 0.2])
@pytest.mark.parametrize(
    "streamcontext",
    [
        lambda delay: astream.iterate(generate_infinite(delay)).stream(),
        lambda delay: athreading.fiterate(generate_infinite(delay)),
        lambda delay: athreading.iterate(generate_infinite(delay)),
        lambda delay: athreading.generate(generate_infinite(delay)),
    ],
    ids=["aiostream", "fiterate", "iterate", "generate"],
)
@pytest.mark.asyncio
async def test_threaded_async_iterate_cancel(streamcontext, worker_delay, main_delay):
    output = []
    async with streamcontext(worker_delay) as stream:
        async for v in stream:
            time.sleep(main_delay)
            output.append(v)
            break
    assert output == [1]


@pytest.mark.parametrize("worker_delay", [0.0, 0.2])
@pytest.mark.parametrize("main_delay", [0.0, 0.2])
@pytest.mark.parametrize(
    "streamcontext",
    [
        lambda delay: astream.iterate(generate_infinite(delay)).stream(),
        lambda delay: athreading.fiterate(generate_infinite(delay)),
        lambda delay: athreading.iterate(generate_infinite(delay)),
        lambda delay: athreading.generate(generate_infinite(delay)),
    ],
    ids=["aiostream", "fiterate", "iterate", "generate"],
)
@pytest.mark.asyncio
async def test_threaded_async_iterate_exception(
    streamcontext, worker_delay, main_delay
):
    output = []
    with pytest.raises(TypeError):
        async with streamcontext(worker_delay, repeats="invalid") as stream:
            async for v in stream:
                time.sleep(main_delay)
                output.append(v)
                break
