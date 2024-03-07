import time
from concurrent.futures import ThreadPoolExecutor

import pytest

import athreading

TEST_VALUES = [1, None, "", 2.0]

executor = ThreadPoolExecutor()


def iterator(delay=0.0):
    for item in TEST_VALUES:
        time.sleep(delay)
        yield item


@athreading.wrap_iterator(executor=executor)
def aiterator(delay=0.0):
    return iterator(delay)


@pytest.mark.asyncio
async def test_aiterate():
    output = []
    async with aiterator(delay=0.0) as stream:
        async for v in stream:
            output.append(v)
    assert output == TEST_VALUES
