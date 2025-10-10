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


@athreading.single_callback(executor=executor)
def arun(callback: Callable[[int], None]) -> None:
    run_with_callback(callback, interval=0.1)


def test_callback_run():
    outputs = []
    run_with_callback(outputs.append)
    assert outputs == [1]


@pytest.mark.asyncio
async def test_acallback_run():
    outputs = []
    outputs.append(await arun())
    assert outputs == [1]
