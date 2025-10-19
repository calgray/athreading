from __future__ import annotations

import asyncio
import functools
import sys
import time
from collections.abc import AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from typing import Callable, Union

import pytest

import athreading
from athreading.callback_iterator import CallbackThreadedAsyncIterator

if sys.version_info >= (3, 11):
    from contextlib import nullcontext
else:
    from tests.compat import nullcontext

TestData = Union[int, str, float, None]

TEST_VALUES = [1, None, "", 2.0]


custom_executor = ThreadPoolExecutor()


def iterate_with_callback(
    callback: Callable[[TestData], None], delay=0.0, exc_idx: int | None = None
) -> None:
    """Create an iterator over test values.

    Args:
        callback: output callback.
        delay: delay between yields. Defaults to 0.0.
        exc_idx: elemetn to raise exception at. Defaults to None.

    Raises:
        ValueError: _description_
    """
    for idx, item in enumerate(TEST_VALUES):
        time.sleep(delay)
        if idx == exc_idx:
            raise ValueError(item)
        callback(item)


async def agenerate_naive(delay=0.0, exc_idx=None) -> AsyncGenerator[TestData, None]:
    """Naive conversion to async generator. Generator blocks the
    io loop resulting in poor performance."""
    q = Queue[TestData]()
    iterate_with_callback(q.put, delay, exc_idx)
    while not q.empty():
        yield q.get()
        await asyncio.sleep(0.0)


@athreading.iterate_callback(executor=custom_executor)
def aiterate(callback: Callable[[TestData], None], delay=0.0, exc_idx=None):
    iterate_with_callback(callback, delay, exc_idx)


@athreading.iterate_callback()
def aiterate_simpler(callback: Callable[[TestData], None], delay=0.0, exc_idx=None):
    iterate_with_callback(callback, delay, exc_idx)


@athreading.iterate_callback
def aiterate_simplest(callback: Callable[[TestData], None], delay=0.0, exc_idx=None):
    iterate_with_callback(callback, delay, exc_idx)


@pytest.mark.parametrize("worker_delay", [0.0, 0.1])
@pytest.mark.parametrize("main_delay", [0.0, 0.1])
@pytest.mark.parametrize(
    "streamcontext",
    [
        lambda delay: nullcontext(agenerate_naive(delay)),
        lambda delay: CallbackThreadedAsyncIterator(
            functools.partial(iterate_with_callback, delay=delay)
        ),
        lambda delay: athreading.iterate_callback(iterate_with_callback)(delay),
        lambda delay: aiterate(delay),
        lambda delay: aiterate_simpler(delay),
        lambda delay: aiterate_simplest(delay),
    ],
    ids=[
        "naive",
        "aiterator",
        "iterate",
        "aiterate",
        "aiterate_simpler",
        "aiterate_simplest",
    ],
)
@pytest.mark.asyncio
async def test_callback_iterate(streamcontext, worker_delay, main_delay):
    output = []
    async with streamcontext(worker_delay) as stream:
        async for v in stream:
            time.sleep(main_delay)
            output.append(v)
    assert output == TEST_VALUES
    await asyncio.wait_for(asyncio.get_running_loop().shutdown_default_executor(), 1.0)


@pytest.mark.parametrize(
    "streamcontext",
    [
        lambda delay, _: CallbackThreadedAsyncIterator(
            functools.partial(iterate_with_callback, delay=delay)
        ),
        lambda delay, e: athreading.iterate_callback(iterate_with_callback, executor=e)(
            delay=delay
        ),
        lambda delay, e: athreading.iterate_callback(executor=e)(iterate_with_callback)(
            delay=delay
        ),
    ],
    ids=["iterator_constructor", "iterate", "iterate_lazy"],
)
@pytest.mark.asyncio
async def test_callback_iterate_parallel(streamcontext):
    max_workers = 8
    worker_delay = 1.0
    executor = ThreadPoolExecutor(max_workers=max_workers)

    async def process():
        outputs = []
        async with streamcontext(worker_delay, executor) as stream:
            async for value in stream:
                outputs.append(value)
        assert outputs == TEST_VALUES

    # set timeout between thread time and total thread time to ensure
    # execution exhibits parallelism for thread sleeps
    thread_time = worker_delay * len(TEST_VALUES)
    total_thread_time = max_workers * thread_time
    timeout = thread_time + 0.5 * (total_thread_time - thread_time)

    await asyncio.wait_for(
        asyncio.gather(*[process() for i in range(max_workers)]),
        timeout=timeout,
    )
    await asyncio.wait_for(asyncio.get_running_loop().shutdown_default_executor(), 1.0)


@pytest.mark.asyncio
async def test_callback_iterate_exception():
    yielded = []

    with pytest.raises(ValueError):
        async with aiterate_simplest(0, 3) as istream:
            yielded.extend([res async for res in istream])

    assert yielded == []

    with pytest.raises(ValueError):  # noqa: PT012
        async with aiterate_simplest(0, 3) as istream:
            async for res in istream:
                yielded.append(res)  # noqa: PERF401

    assert yielded == TEST_VALUES[:3]
