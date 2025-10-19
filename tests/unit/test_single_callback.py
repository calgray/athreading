import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

import pytest

import athreading

executor = ThreadPoolExecutor()


def run_with_callback(callback: Callable[[int], None], interval: float = 0.01) -> None:
    """Simulated blocking function that emits data via callback"""
    time.sleep(interval)  # Blocking operation
    callback(1)


async def arun_naive():
    output = []
    run_with_callback(output.append)
    return output[0]


@athreading.single_callback(executor=executor)
def arun(callback: Callable[[int], None]) -> None:
    run_with_callback(callback, interval=0.1)


@athreading.single_callback()
def arun_simpler(callback: Callable[[int], None]) -> None:
    run_with_callback(callback, interval=0.1)


@athreading.single_callback
def arun_simplest(callback: Callable[[int], None]) -> None:
    run_with_callback(callback, interval=0.1)


def test_run_with_callback():
    outputs = []
    run_with_callback(outputs.append)
    assert outputs == [1]


@pytest.mark.parametrize(
    "awaitable",
    [
        arun_naive,
        arun,
        arun_simpler,
        arun_simplest,
    ],
    ids=[
        "naive",
        "arun",
        "arun_simpler",
        "arun_simplest",
    ],
)
@pytest.mark.asyncio
async def test_arun(awaitable):
    outputs = []
    outputs.append(await awaitable())
    assert outputs == [1]
    outputs.append(await awaitable())
    assert outputs == [1, 1]
