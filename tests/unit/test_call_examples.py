import time
from concurrent.futures import ThreadPoolExecutor

import pytest

import athreading

executor = ThreadPoolExecutor()


def square(x: float, delay: float = 0):
    time.sleep(0.5)
    return x * x


@athreading.wrap_callable(executor=executor)
def asquare(x: float):
    return square(x)


def test_square():
    assert 4 == square(2)


@pytest.mark.asyncio
async def test_asquare():
    assert 4 == await asquare(2)
