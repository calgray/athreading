# athreading

[![Test and build](https://github.com/calgray/athreading/actions/workflows/ci.yml/badge.svg)](https://github.com/calgray/athreading/actions/workflows/ci.yml)

`athreading` is an asynchronous threading library for running and synchronizing I/O threads with asyncio.

Note: Python GIL only allows multi-threaded I/O parallelism and not multi-threaded CPU parallelism.

## Usage

Synchronous I/O functions and generators using sleep/wait operations can be run asynchronously by offloading to worker threads and avoid blocking the async I/O loop.

### Callable → Coroutine

Use `athread.call` to wrap a function/`Callable` to an async function/function returning a `Coroutine`:

#### Synchronous<!--1-->

```python
def print_sqrt(x):
    time.sleep(0.5)
    result = math.sqrt(x)
    print(datetime.datetime.now(), result)
    return result

res = (print_sqrt(2), print_sqrt(3), print_sqrt(4))
print(res)
```

output:

```log
2023-12-05 14:45:57.716696 1.4142135623730951
2023-12-05 14:45:58.217192 1.7320508075688772
2023-12-05 14:45:58.717934 2.0
(1.4142135623730951 1.7320508075688772 2.0)
```

#### Asynchronous<!--1-->

```python
async def amain():
    aprint_sqrt = athreading.call(print_sqrt)
    res = await asyncio.gather(
        aprint_sqrt(2),
        aprint_sqrt(3),
        aprint_sqrt(4)
    )
    print(res)

asyncio.run(amain())
```

output:

```log
2023-12-05 14:45:59.219461 1.4142135623730951
2023-12-05 14:45:59.220492 1.7320508075688772
2023-12-05 14:45:59.221174 2.0
(1.4142135623730951 1.7320508075688772 2.0)
```

### Iterator → AsyncIterator

Use `athreading.iterate` to convert an `Generator` interface to an `AsyncGenerator` for iterating on the I/O thread.

#### Synchronous<!--2-->

```python
def worker(n):
   for i in range(n):
       time.sleep(0.5)
       yield datetime.datetime.now()

def print_stream(id, stream):
    for value in stream:
        print("stream:", id, "time:", value)

for sid in range(4):
    print_stream(sid, worker(3))
```

output:

```log
stream: 0 time: 2023-12-05 09:37:38.758954
stream: 0 time: 2023-12-05 09:37:39.259106
stream: 0 time: 2023-12-05 09:37:39.759610
stream: 1 time: 2023-12-05 09:37:40.260039
stream: 1 time: 2023-12-05 09:37:40.760152
stream: 1 time: 2023-12-05 09:37:41.260274
stream: 2 time: 2023-12-05 09:37:41.760548
stream: 2 time: 2023-12-05 09:37:42.262526
stream: 2 time: 2023-12-05 09:37:42.762736
stream: 3 time: 2023-12-05 09:37:43.262930
stream: 3 time: 2023-12-05 09:37:43.763080
stream: 3 time: 2023-12-05 09:37:44.263225
```

#### Asynchronous<!--2-->

```python
async def aprint_stream(id, stream):
    async with stream:
        async for value in stream:
            print("stream:", id, "time:", value)


async def arun():
    executor = ThreadPoolExecutor(max_workers=4)
    await asyncio.gather(
        *[
            aprint_stream(sid, athreading.iterate(worker(3), executor))
            for sid in range(4)
        ]
    )

asyncio.run(arun())
```

output:

```log
stream: 0 time: 2023-12-05 09:37:15.834115
stream: 1 time: 2023-12-05 09:37:15.835140
stream: 2 time: 2023-12-05 09:37:15.835749
stream: 3 time: 2023-12-05 09:37:15.836387
stream: 0 time: 2023-12-05 09:37:16.834371
stream: 1 time: 2023-12-05 09:37:16.835346
stream: 2 time: 2023-12-05 09:37:16.835938
stream: 3 time: 2023-12-05 09:37:16.836573
stream: 0 time: 2023-12-05 09:37:17.834634
stream: 1 time: 2023-12-05 09:37:17.835552
stream: 2 time: 2023-12-05 09:37:17.836113
stream: 3 time: 2023-12-05 09:37:17.836755
```

### Generator → AsyncGenerator

Use `athreading.generate` to convert an `Iterable` interface to an `AsyncIterator` for iterating on the I/O thread.

#### Synchronous<!--3-->

TODO

#### Asynchronous<!--3-->

TODO

## Maintenance

This is a minimal Python 3.11 application that uses [poetry](https://python-poetry.org) for packaging and dependency management. It also provides [pre-commit](https://pre-commit.com/) hooks (for [isort](https://pycqa.github.io/isort/), [Black](https://black.readthedocs.io/en/stable/), [Flake8](https://flake8.pycqa.org/en/latest/) and [mypy](https://mypy.readthedocs.io/en/stable/)) and automated tests using [pytest](https://pytest.org/) and [GitHub Actions](https://github.com/features/actions). Pre-commit hooks are automatically kept updated with a dedicated GitHub Action, this can be removed and replace with [pre-commit.ci](https://pre-commit.ci) if using an public repo. It was developed by the [Imperial College Research Computing Service](https://www.imperial.ac.uk/admin-services/ict/self-service/research-support/rcs/).

### Development

To modify, test and request changes to this repository:

1. [Download and install Poetry](https://python-poetry.org/docs/#installation) following the instructions for your OS.
2. Clone `git@github.com:calgray/athreading.git` and make it your working directory
3. Set up the virtual environment:

   ```bash
   poetry install
   ```

4. Activate the virtual environment (alternatively, ensure any python-related command is preceded by `poetry run`):

   ```bash
   poetry shell
   ```

5. Install the git hooks:

   ```bash
   pre-commit install
   ```

6. Run the tests:

   ```bash
   pytest
   ```

### Publishing

The GitHub workflow includes an action to publish on release.
To run this action, uncomment the commented portion of `publish.yml`, and modify the steps for the desired behaviour (ie. publishing a Docker image, publishing to PyPI, deploying documentation etc.)
