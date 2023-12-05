# athreading

[![Test and build](https://github.com/calgray/athreading/actions/workflows/ci.yml/badge.svg)](https://github.com/calgray/athreading/actions/workflows/ci.yml)

`athreading` is asynchronous threading library for running and synchronizing worker threads with asyncio.

# Usage

```python
import athreading
import asyncio
import time
import datetime
from concurrent.futures import ThreadPoolExecutor


def worker(delay, n):
    for i in range(n):
        time.sleep(delay)
        yield datetime.datetime.now()


async def print_stream(id, stream):
    async with stream:
        async for value in stream:
            print(id, value)


async def arun():
    executor = ThreadPoolExecutor(max_workers=4)
    await asyncio.gather(
        print_stream(0, athreading.iterate(worker(1.0, 3), executor)),
        print_stream(1, athreading.iterate(worker(1.0, 3), executor)),
        print_stream(2, athreading.iterate(worker(1.0, 3), executor)),
        print_stream(3, athreading.iterate(worker(1.0, 3), executor))
   )

asyncio.run(arun())
```

output:
```
0 2023-12-05 09:37:15.834115
1 2023-12-05 09:37:15.835140
2 2023-12-05 09:37:15.835749
3 2023-12-05 09:37:15.836387
0 2023-12-05 09:37:16.834371
1 2023-12-05 09:37:16.835346
2 2023-12-05 09:37:16.835938
3 2023-12-05 09:37:16.836573
0 2023-12-05 09:37:17.834634
1 2023-12-05 09:37:17.835552
2 2023-12-05 09:37:17.836113
3 2023-12-05 09:37:17.836755
```


## Developement

This is a minimal Python 3.11 application that uses [poetry](https://python-poetry.org) for packaging and dependency management. It also provides [pre-commit](https://pre-commit.com/) hooks (for [isort](https://pycqa.github.io/isort/), [Black](https://black.readthedocs.io/en/stable/), [Flake8](https://flake8.pycqa.org/en/latest/) and [mypy](https://mypy.readthedocs.io/en/stable/)) and automated tests using [pytest](https://pytest.org/) and [GitHub Actions](https://github.com/features/actions). Pre-commit hooks are automatically kept updated with a dedicated GitHub Action, this can be removed and replace with [pre-commit.ci](https://pre-commit.ci) if using an public repo. It was developed by the [Imperial College Research Computing Service](https://www.imperial.ac.uk/admin-services/ict/self-service/research-support/rcs/).

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
