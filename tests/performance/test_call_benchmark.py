import asyncio
import time

import pytest
import threaded

import athreading

threadpool = threaded.ThreadPooled()
threadpool.configure(4)
executor = threadpool.executor


def square(x: float, delay: float = 0.0):
    time.sleep(delay)
    return x * x


@athreading.call(executor=executor)
def athreading_asquare(x: float, delay: float = 0.0):
    return square(x, delay)


@threaded.threadpooled()
def threaded_asquare(x: float, delay: float = 0.0):
    return square(x, delay)


@pytest.mark.benchmark(group="call", disable_gc=True, warmup=False)
def test_call_athreading_benchmark(benchmark):
    def main():
        return asyncio.run(athreading_asquare(2, 0.0))

    assert 4 == benchmark(main)


@pytest.mark.benchmark(group="call", disable_gc=True, warmup=False)
def test_call_threaded_benchmark(benchmark):
    async def atask():
        return await asyncio.wrap_future(threaded_asquare(2, 0.0))

    assert 4 == benchmark(lambda: asyncio.run(atask()))
