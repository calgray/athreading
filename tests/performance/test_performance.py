import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
import threaded

import athreading

executor = ThreadPoolExecutor()


def square(x: float, delay: float = 0.0):
    time.sleep(delay)
    return x * x


@athreading.wrap_callable(executor=executor)
def athreading_asquare(x: float, delay: float = 0.0):
    return square(x, delay)


@threaded.threadpooled()
def threaded_asquare(x: float, delay: float = 0.0):
    return square(x, delay)


def test_athreading_benchmark(benchmark):
    def main():
        return asyncio.run(athreading_asquare(2, 0.0))

    assert 4 == benchmark(main)


def test_threaded_benchmark(benchmark):
    def main():
        async def amain():
            return await asyncio.wrap_future(threaded_asquare(2, 0.0))

        return asyncio.run(amain())

    assert 4 == benchmark(main)
