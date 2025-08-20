import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

import athreading

custom_executor = ThreadPoolExecutor()


def square(x: float, worker_delay: float) -> float:
    time.sleep(worker_delay)
    return x * x


@athreading.call(executor=custom_executor)
def asquare(x: float, worker_delay: float):
    return square(x, worker_delay)


@athreading.call()
def asquare_simpler(x: float, worker_delay: float):
    return square(x, worker_delay)


@athreading.call
def asquare_simplest(x: float, worker_delay: float):
    return square(x, worker_delay)


@pytest.mark.parametrize("worker_delay", [0.0, 0.2])
@pytest.mark.parametrize("main_delay", [0.0, 0.2])
@pytest.mark.parametrize(
    "fn", [athreading.call(square), asquare, asquare_simpler, asquare_simplest]
)
@pytest.mark.asyncio
async def test_threaded_async_call_single(fn, worker_delay: float, main_delay: float):
    time.sleep(main_delay)
    result = await fn(5, worker_delay)
    assert result == 25.0


@pytest.mark.parametrize("worker_delay", [0.2])
@pytest.mark.parametrize("main_delay", [0.0, 0.2])
@pytest.mark.parametrize(
    "fn", [athreading.call(square), asquare, asquare_simpler, asquare_simplest]
)
@pytest.mark.asyncio
async def test_threaded_async_call_cancel(fn, worker_delay: float, main_delay: float):
    fn = athreading.call(square)
    await asyncio.sleep(main_delay)
    task = asyncio.create_task(fn(5, worker_delay))
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.parametrize("worker_delay", [0.2])
@pytest.mark.parametrize("main_delay", [0.0, 0.2])
@pytest.mark.parametrize(
    "fn", [athreading.call(square), asquare, asquare_simpler, asquare_simplest]
)
@pytest.mark.asyncio
async def test_threaded_async_call_exception(
    fn, worker_delay: float, main_delay: float
):
    fn = athreading.call(square)
    await asyncio.sleep(main_delay)
    with pytest.raises(
        TypeError, match="can't multiply sequence by non-int of type 'str'"
    ):
        _ = await fn("a", worker_delay)  # pyright: ignore
