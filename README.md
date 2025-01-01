# athreading

[![Test and build](https://github.com/calgray/athreading/actions/workflows/ci.yml/badge.svg)](https://github.com/calgray/athreading/actions/workflows/ci.yml)
[![PyPI version shields.io](https://img.shields.io/pypi/v/athreading.svg)](https://pypi.python.org/pypi/athreading)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/athreading.svg)](https://pypi.python.org/pypi/athreading)

`athreading` is a Python library that allows you to run synchronous I/O functions asynchronously using `asyncio`. It provides decorators to adapt synchronous functions and generators, enabling them to operate without blocking the event loop.

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

async def main():
    results = await asyncio.gather(
        compute_sqrt(2),
        compute_sqrt(3),
        compute_sqrt(4)
    )
    print(results)

asyncio.run(main())
```

In this example, `compute_sqrt` is a synchronous function that sleeps for 0.5 seconds to simulate a blocking I/O operation. By decorating it with `@athreading.call`, it can be awaited within an asynchronous context, allowing multiple calls to run concurrently without blocking the event loop.

## 2. Converting a Synchronous Iterator

The `@athreading.iterate` decorator transforms a synchronous iterator into an asynchronous iterator.

```python
import athreading
import time
import datetime
import asyncio

@athreading.iterate
def time_generator(n):
    for _ in range(n):
        time.sleep(0.5)  # Simulate a blocking I/O operation
        yield datetime.datetime.now()

async def main():
    async for current_time in time_generator(3):
        print(current_time)

asyncio.run(main())
```

Here, `time_generator` is a synchronous generator function that yields the current time after sleeping for 0.5 seconds. By decorating it with `@athreading.iterate`, it becomes an asynchronous generator that can be iterated over without blocking the event loop.

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
