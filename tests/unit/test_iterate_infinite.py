import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, nullcontext

import pytest

import athreading

custom_executor = ThreadPoolExecutor()


def generate_infinite(delay=0.0):
    item = 0
    while True:
        time.sleep(delay)
        item += 1
        yield item


@asynccontextmanager
async def agenerate_infinite_naive(delay=0.0):
    stopped = False

    async def agenerator():
        for value in generate_infinite(delay):
            yield value
            if stopped:
                break
            await asyncio.sleep(0.0)

    yield agenerator()
    stopped = True


@pytest.mark.parametrize("worker_delay", [0.0, 0.1])
@pytest.mark.parametrize("main_delay", [0.0, 0.1])
@pytest.mark.parametrize(
    "streamcontext",
    [
        lambda delay: agenerate_infinite_naive(delay),
        lambda delay: athreading.iterate(generate_infinite)(delay),
        lambda delay: athreading.generate(generate_infinite)(delay),
    ],
    ids=["naive", "iterate", "generate"],
)
@pytest.mark.asyncio
async def test_iterate_cancel(streamcontext, worker_delay, main_delay):
    output = []
    async with streamcontext(worker_delay) as stream:
        async for v in stream:
            time.sleep(main_delay)
            output.append(v)
            break
    assert output == [1]
    await asyncio.wait_for(asyncio.get_running_loop().shutdown_default_executor(), 1.0)


@pytest.mark.parametrize("worker_delay", [0.0, 0.1])
@pytest.mark.parametrize("main_delay", [0.0, 0.1])
@pytest.mark.parametrize(
    "streamcontext",
    [
        lambda delay: nullcontext(agenerate_infinite_naive(delay)),
        lambda delay: athreading.iterate(generate_infinite)(delay),
        lambda delay: athreading.generate(generate_infinite)(delay),
    ],
    ids=["naive", "iterate", "generate"],
)
@pytest.mark.asyncio
async def test_iterate_exception(streamcontext, worker_delay, main_delay):
    output = []
    with pytest.raises(TypeError):
        async with streamcontext(worker_delay, repeats="invalid") as stream:
            async for v in stream:
                time.sleep(main_delay)
                output.append(v)
                break
    await asyncio.wait_for(asyncio.get_running_loop().shutdown_default_executor(), 1.0)
