import time
from concurrent.futures import ThreadPoolExecutor

import pytest

import athreading

DATA_VALUES = [1, 2, 3, 4]

executor = ThreadPoolExecutor()


# Simulated blocking function that emits data via callback
def run_with_callback(callback, interval=0.01):
    for item in DATA_VALUES:
        time.sleep(interval)  # Blocking operation
        callback(item)


@athreading.iterate_callback(executor=executor)
def arun(callback):
    run_with_callback(callback)


def test_iterate():
    outputs = []
    run_with_callback(outputs.append)
    assert outputs == DATA_VALUES


@pytest.mark.asyncio
async def test_aiterate():
    outputs = []
    async with arun() as stream:
        # Can switch to other tasks while waiting for stream
        async for value in stream:
            outputs.append(value)
    assert outputs == DATA_VALUES
