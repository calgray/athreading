import asyncio
import time

import threaded

import athreading

# pyinstument

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


def test_athreading_benchmark(benchmark):
    def main():
        return asyncio.run(athreading_asquare(2, 0.0))

    assert 4 == benchmark(main)


def test_to_thread_benchmark(benchmark):
    def main():
        return asyncio.run(asyncio.to_thread(square, 2, 0.0))

    assert 4 == benchmark(main)


def test_threaded_benchmark(benchmark):
    def main():
        async def amain():
            return await asyncio.wrap_future(threaded_asquare(2, 0.0))

        return asyncio.run(amain())

    assert 4 == benchmark(main)
