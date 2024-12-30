import asyncio
import time
from collections.abc import Iterable

import aiostream
import pytest
import threaded

import athreading

threadpool = threaded.ThreadPooled()
threadpool.configure(4)
executor = threadpool.executor


def square(x: float, delay: float = 0.0):
    time.sleep(delay)
    return x * x


def square_iterate(iterator: Iterable[float], delay: float = 0.0):
    for item in iterator:
        time.sleep(delay)
        yield square(item)


@athreading.iterate(executor=executor)
def asquare_iterate_athreading(values: Iterable[float], delay: float = 0.0):
    yield from square_iterate(values, delay)


def asquare_iterate_aiostream(iterator: Iterable[float], delay: float = 0.0):
    return aiostream.stream.iterate(square_iterate(iterator, delay)).stream()


async def asquare_list_athreading(length: int):
    async with asquare_iterate_athreading(range(length), 0.001) as it:
        return [v async for v in it]


async def asquare_list_aiostream(length: int):
    return await aiostream.stream.list(asquare_iterate_aiostream(range(length), 0.001))


@pytest.mark.benchmark(group="iterate", disable_gc=True, warmup=False)
@pytest.mark.parametrize("impl", [asquare_list_athreading, asquare_list_aiostream])
@pytest.mark.parametrize("stream_length", [100])
@pytest.mark.parametrize("num_streams", [1, 4, 16])
def test_iterate_benchmark(benchmark, impl, num_streams: int, stream_length: int):
    async def atask():
        return await asyncio.gather(*(impl(stream_length) for _ in range(num_streams)))

    expected = list(square_iterate(range(stream_length)))
    results = benchmark(lambda: asyncio.run(atask()))
    for result in results:
        assert expected == result
