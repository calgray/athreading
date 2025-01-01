# athreading

[![Test and build](https://github.com/calgray/athreading/actions/workflows/ci.yml/badge.svg)](https://github.com/calgray/athreading/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/athreading.svg)](https://pypi.python.org/pypi/athreading)
[![PyPI python versions](https://img.shields.io/pypi/pyversions/athreading.svg?style=flat&logo=python&logoColor=white)](https://pypi.python.org/pypi/athreading)
[![License](https://img.shields.io/badge/license-BSD_3--clause-blue.svg)](https://opensource.org/license/bsd-3-clause/)
[![Codecov](https://codecov.io/gh/calgray/athreading/branch/main/graph/badge.svg)](https://app.codecov.io/github/calgray/athreading)

[![Code style](https://img.shields.io/badge/code_style-black-000000.svg)](https://github.com/psf/black)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Pydocstyle](https://img.shields.io/badge/pydocstyle-enabled-AD4CD3)](http://www.pydocstyle.org/en/stable/)

`athreading` is a Python library that allows you to run synchronous I/O functions asynchronously using `asyncio` via background threads. It provides decorators to adapt synchronous functions and generators, enabling them to operate without blocking the event loop.

## Features

- **`@athreading.call`**: Converts a synchronous function into an asynchronous function.
- **`@athreading.iterate`**: Converts a synchronous iterator into an asynchronous iterator.
- **`@athreading.generate`**: Converts a synchronous generator into an asynchronous generator.

*Note*: Due to Python's Global Interpreter Lock (GIL), this library does not provide multi-threaded CPU parallelism unless using Python 3.9 with `nogil` or Python 3.13 with free threading enabled.

## Installation

`athreading` can be installed using pip:

```bash
pip install athreading
```

## Usage

`athreading` enables running synchronous functions and iterators asynchronously using `asyncio`.

### 1. Converting a Synchronous Function

The `@athreading.call` decorator to convert a synchronous function into an asynchronous function.

```python
import athreading
import time
import math
import asyncio

@athreading.call
def compute_sqrt(x):
    time.sleep(0.5)  # Simulate a blocking I/O operation
    return math.sqrt(x)

async def amain():
    results = await asyncio.gather(
        compute_sqrt(2),
        compute_sqrt(3),
        compute_sqrt(4)
    )
    print(results)

asyncio.run(amain())
```

In this example, `compute_sqrt` is a synchronous function that sleeps for 0.5 seconds to simulate a blocking I/O operation. By decorating it with `@athreading.call`, it can be awaited within an asynchronous context, allowing multiple calls to run concurrently without blocking the event loop.

### 2. Converting a Synchronous Iterator

The `@athreading.iterate` decorator transforms a synchronous iterator into an asynchronous iterator.

```python
import athreading
import time
import datetime
import asyncio

@athreading.iterate
def time_generator(n, label):
    for _ in range(n):
        time.sleep(0.5)  # Simulate a blocking I/O operation
        yield f"{label}: {datetime.datetime.now()}"

async def amain():
    async def print_stream(label):
        async with time_generator(10, label) as stream:
            async for current_time in stream:
                print(current_time)

    await asyncio.gather(
        print_stream("Stream 1"),
        print_stream("Stream 2"),
        print_stream("Stream 3"),
    )

asyncio.run(amain())
```

This example demonstrates running three asynchronous streams concurrently. Each stream processes the `time_generator` function independently, and the decorator ensures iteration occurs without blocking the event loop.

### 3. Converting a Synchronous Generator

The `@athreading.generate` decorator converts a synchronous generator function into an asynchronous generator function that supports `asend`.

```python
import athreading
import time
import asyncio

@athreading.generate
def controlled_counter(start, step):
    current = start
    while True:
        time.sleep(0.5)  # Simulate a blocking I/O operation
        received = yield current
        current = received if received is not None else current + step

async def amain():
    async with controlled_counter(0, 1) as async_gen:
        print(await async_gen.asend(None))  # Start the generator
        print(await async_gen.asend(None))  # Advance with default step
        print(await async_gen.asend(10))   # Send a new value to control the counter
        print(await async_gen.asend(None))  # Continue from the new value

asyncio.run(amain())
```

This example demonstrates how `@athreading.generate` transforms a synchronous generator into an asynchronous generator. The `asend` method sends values to control the generator's state dynamically, enabling interactive workflows while avoiding blocking the event loop.

## Maintenance

This is a minimal Python library that uses [poetry](https://python-poetry.org) for packaging and dependency management. It also provides [pre-commit](https://pre-commit.com/) hooks (for [isort](https://pycqa.github.io/isort/), [Black](https://black.readthedocs.io/en/stable/), [Flake8](https://flake8.pycqa.org/en/latest/) and [mypy](https://mypy.readthedocs.io/en/stable/)) and automated tests using [pytest](https://pytest.org/) and [GitHub Actions](https://github.com/features/actions). Pre-commit hooks are automatically kept updated with a dedicated GitHub Action, this can be removed and replace with [pre-commit.ci](https://pre-commit.ci) if using an public repo. It was developed by the [Imperial College Research Computing Service](https://www.imperial.ac.uk/admin-services/ict/self-service/research-support/rcs/).

### Testing

To modify, test and request changes to this repository:

1. [Download and install Poetry](https://python-poetry.org/docs/#installation) following the instructions for the target OS.
2. Clone `git@github.com:calgray/athreading.git` and make it the working directory.
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

## License

This project is licensed under the BSD-3-Clause License.

For more information and examples, please visit the [athreading GitHub repository](https://github.com/calgray/athreading).
