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


async def asquare_blocking(x: float, delay: float = 0.0):
    return square(x, delay)


@athreading.call(executor=executor)
def asquare_athreading(x: float, delay: float = 0.0):
    return square(x, delay)


@threaded.threadpooled()
def square_athreaded(x: float, delay: float = 0.0):
    return square(x, delay)


async def asquare_threaded(x: float, delay: float = 0.0):
    return await asyncio.wrap_future(square_athreaded(x, delay))


@pytest.mark.benchmark(group="call", disable_gc=True, warmup=True)
def test_call_athreading_benchmark(benchmark):
    def test():
        return asyncio.run(asquare_athreading(2, 0.0))

    assert 4 == benchmark(test)


@pytest.mark.benchmark(group="call", disable_gc=True, warmup=True)
def test_call_threaded_benchmark(benchmark):
    def test():
        async def atest():
            return await asyncio.wrap_future(square_athreaded(2, 0.0))

        return asyncio.run(atest())

    assert 4 == benchmark(test)


@pytest.mark.benchmark(group="call", disable_gc=True, warmup=True)
@pytest.mark.parametrize(
    "impl", [asquare_blocking, asquare_threaded, asquare_athreading]
)
@pytest.mark.parametrize("delay", [0.0, 0.001])
def test_single_call_benchmark(benchmark, impl, delay):
    def test():
        return asyncio.run(impl(2, delay))

    assert 4 == benchmark(test)


@pytest.mark.benchmark(group="call", disable_gc=True, warmup=True)
@pytest.mark.parametrize(
    "impl", [asquare_blocking, asquare_threaded, asquare_athreading]
)
@pytest.mark.parametrize("delay", [0.0, 0.001])
@pytest.mark.parametrize("num_tasks", [10, 100])
def test_multi_call_benchmark(benchmark, impl, num_tasks, delay):
    def test():
        async def atest():
            tasks = tuple(impl(2, delay) for _ in range(num_tasks))
            return await asyncio.gather(*tasks)

        return asyncio.run(atest())

    results = benchmark(test)
    for result in results:
        assert 4 == result
