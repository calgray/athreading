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


@athreading.call()
def asquare2(x: float, delay: float = 0.0) -> float:
    return square(x, delay)


@athreading.call
def asquare3(x: float, delay: float = 0.0) -> float:
    return square(x, delay)


def test_square():
    assert 4 == square(2)
    assert 4 == square(2, 0.5)


@pytest.mark.asyncio
async def test_asquare():
    assert 4 == await asquare(2)
    assert 4 == await asquare2(2)
    assert 4 == await asquare3(2)

    assert 4 == await asquare(2, delay=0.5)
    assert 4 == await asquare2(2, delay=0.5)
    assert 4 == await asquare3(2, delay=0.5)
