import asyncio
import time
from collections.abc import AsyncGenerator, Generator
from contextlib import nullcontext
from typing import Optional

import pytest

import athreading


def doubler(delay: float) -> Generator[int, Optional[int], None]:
    """
    Doubles the value sent to the generator.
    """
    yielded = 0
    while True:
        time.sleep(delay)
        sent = yield yielded
        if sent is not None:
            yielded = sent
        else:
            yielded *= 2


async def adoubler(delay: float) -> AsyncGenerator[int, Optional[int]]:
    """
    Doubles the value sent to the generator.
    """
    yielded = 0
    while True:
        await asyncio.sleep(delay)
        sent = yield yielded
        if sent is not None:
            yielded = sent
        else:
            yielded *= 2


@pytest.mark.parametrize("worker_delay", [0.0, 0.1])
@pytest.mark.parametrize("main_delay", [0.0, 0.1])
@pytest.mark.parametrize(
    "streamcontext",
    [
        lambda delay: nullcontext(adoubler(delay)),
        lambda delay: athreading.generate(doubler)(delay),
    ],
    ids=["adoubler", "generate"],
)
@pytest.mark.asyncio
async def test_send_all(streamcontext, worker_delay, main_delay):
    outputs = []
    # first usage must be __next__() or .send(None)
    async with streamcontext(worker_delay) as stream:
        for v in [None, 1, None, None, None, 3, None, None, None]:
            time.sleep(main_delay)
            outputs.append(await stream.asend(v))

    assert outputs == [0, 1, 2, 4, 8, 3, 6, 12, 24]
