import asyncio
import time

import pytest

import athreading


def calculate(x: float, worker_delay: float):
    time.sleep(worker_delay)
    return x * x


@pytest.mark.parametrize("worker_delay", [0.0, 0.2])
@pytest.mark.parametrize("main_delay", [0.0, 0.2])
@pytest.mark.asyncio
async def test_threaded_async_call_single(worker_delay: float, main_delay: float):
    threaded_calculate_value = athreading.wrap_callable(calculate)
    time.sleep(main_delay)
    result = await threaded_calculate_value(5, worker_delay)
    assert result == 25.0


@pytest.mark.parametrize("worker_delay", [0.2])
@pytest.mark.parametrize("main_delay", [0.0, 0.2])
@pytest.mark.asyncio
async def test_threaded_async_call_cancel(worker_delay: float, main_delay: float):
    threaded_calculate_value = athreading.wrap_callable(calculate)
    time.sleep(main_delay)
    task = asyncio.create_task(threaded_calculate_value(5, worker_delay))
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
