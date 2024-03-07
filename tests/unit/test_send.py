import time
from collections.abc import Generator

import pytest

import athreading


def double_n(delay) -> Generator[int, int | None, None]:
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


@pytest.mark.parametrize("worker_delay", [0.0, 0.2])
@pytest.mark.parametrize("main_delay", [0.0, 0.2])
@pytest.mark.parametrize(
    "streamcontext",
    [
        lambda delay: athreading.generate(double_n(delay)),
    ],
    ids=["generator"],
)
@pytest.mark.asyncio
async def test_threaded_async_send_single(streamcontext, worker_delay, main_delay):
    outputs = []
    # first asend must be next() or send(None)
    async with streamcontext(worker_delay) as stream:
        for v in [None, 1, None, None, None, 3, None, None, None]:
            time.sleep(main_delay)
            outputs.append(await stream.asend(v))

    assert outputs == [0, 1, 2, 4, 8, 3, 6, 12, 24]
