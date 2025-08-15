import asyncio
import datetime
import time

import athreading


@athreading.iterate_callback
def time_generator(callback, n):
    for _ in range(n):
        time.sleep(0.05)  # Simulate a blocking I/O operation
        callback(datetime.datetime.now())


async def aprint_stream(label):
    async with time_generator(10) as stream:
        async for current_time in stream:
            print(f"{label}: {current_time}")


async def amain():
    await asyncio.gather(
        aprint_stream("Stream 1"),
        aprint_stream("Stream 2"),
        aprint_stream("Stream 3"),
    )


asyncio.run(amain())
