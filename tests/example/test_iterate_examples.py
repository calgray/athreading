import time
from concurrent.futures import ThreadPoolExecutor

import pytest

import athreading

DATA_VALUES = [1, 2, 3, 4]

executor = ThreadPoolExecutor()


def iterator(interval=0.0):
    for item in DATA_VALUES:
        time.sleep(interval)
        yield item


@athreading.iterate(executor=executor)
def aiterator(interval=0.0):
    return iterator(interval)


def test_iterate():
    output = []
    for v in iterator(interval=0.5):
        output.append(v)
    assert output == DATA_VALUES


@pytest.mark.asyncio
async def test_aiterate():
    output = []
    async with aiterator(interval=0.5) as stream:
        # can switch to other tasks while waiting for stream
        async for value in stream:
            output.append(value)
    assert output == DATA_VALUES
