import time
from concurrent.futures import ThreadPoolExecutor

import pytest

import athreading

executor = ThreadPoolExecutor()


def square(x: float, delay: float = 0.0):
    time.sleep(delay)
    return x * x


@athreading.call(executor=executor)
def asquare(x: float, delay: float = 0.0) -> float:
    return square(x, delay)


def test_square():
    assert square(2) == 4
    assert square(2, 0.5) == 4


@pytest.mark.asyncio
async def test_asquare():
    assert await asquare(2) == 4
    assert await asquare(2, delay=0.5) == 4
