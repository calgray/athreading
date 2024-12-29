import time
from collections.abc import AsyncGenerator, Generator
from typing import Optional

import pytest

import athreading


def generate_infinite(delay: float) -> Generator[int, Optional[int], None]:
    while True:
        try:
            time.sleep(delay)
            yield 0
        except ZeroDivisionError:
            yield -1


async def agenerate_infinite(delay: float) -> AsyncGenerator[int, Optional[int]]:
    while True:
        try:
            time.sleep(delay)
            yield 0
        except ZeroDivisionError:
            yield -1


@pytest.mark.parametrize("worker_delay", [0.0, 0.1])
@pytest.mark.parametrize("main_delay", [0.0, 0.1])
@pytest.mark.parametrize(
    "streamcontext",
    [
        lambda delay: agenerate_infinite(delay),
        lambda delay: athreading.generate(generate_infinite)(delay),
    ],
    ids=["control", "generate"],
)
@pytest.mark.asyncio
async def test_throw_immediate(streamcontext, worker_delay, main_delay):
    outputs = []
    with pytest.raises(RuntimeError):
        async with streamcontext(worker_delay) as stream:
            await stream.asend(None)
            time.sleep(main_delay)
            outputs.append(await stream.athrow(RuntimeError))

    assert outputs == []


@pytest.mark.parametrize("worker_delay", [0.0, 0.1])
@pytest.mark.parametrize("main_delay", [0.0, 0.1])
@pytest.mark.parametrize(
    "streamcontext",
    [
        lambda delay: agenerate_infinite(delay),
        lambda delay: athreading.generate(generate_infinite)(delay),
    ],
    ids=["control", "generate"],
)
@pytest.mark.asyncio
async def test_throw_handler(streamcontext, worker_delay, main_delay):
    outputs = []
    async with streamcontext(worker_delay) as stream:
        await stream.asend(None)
        time.sleep(main_delay)
        outputs.append(await stream.athrow(ZeroDivisionError))

    assert outputs == [-1]
