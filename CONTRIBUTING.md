# Contributing

Thank you for considering contributing to Athreading! We appreciate your efforts to help improve the project. Please follow these guidelines to ensure a smooth and productive contribution process.

Reading and following these guidelines will help us make the contribution process easy and effective for everyone involved. It also communicates that you agree to respect the time of the developers managing and developing these open source projects. In return, we will reciprocate that respect by addressing your issue, assessing changes, and helping you finalize your pull requests.

## Quicklinks

* [Getting Started](#getting-started)
  * [Issues](#issues)
  * [Pull Requests](#pull-requests)
* [Maintenance](#maintenance)
  * [Testing](#testing)
  * [Publishing](#publishing)

## Getting Started

Contributions are made to this repo via Issues and Pull Requests (PRs). A few general guidelines that cover both:

* Search for existing Issues and PRs before creating your own.
* Read this repository package license and licenses of any proposed dependencies to ensure compatibility
* We work hard to makes sure issues are handled in a timely manner but, depending on the impact, it could take a while to investigate the root cause. A friendly ping in the comment thread to the submitter or a contributor can help draw attention if your issue is blocking.
* If you've never contributed to FOSS projects before, see this [the first timer's guide](https://auth0.com/blog/a-first-timers-guide-to-an-open-source-project/) for resources and tips on how to get started.

### Issues

Issues should be used to report problems with the library, request a new feature, or to discuss potential changes before a PR is created. When you create a new Issue, a template will be loaded that will guide you through collecting and providing the information we need to investigate.

If you find an Issue that addresses the problem you're having, please add your own reproduction information to the existing issue rather than creating a new one. Adding a [reaction](https://github.blog/2016-03-10-add-reactions-to-pull-requests-issues-and-comments/) can also help by indicating to our maintainers that a particular problem is affecting more than just the reporter.

### Pull Requests

PRs to our libraries are always welcome and can be a quick way to get your fix or improvement slated for the next release. In general, PRs should:

* Only fix/add the functionality in question **OR** address wide-spread whitespace/style issues, not both.
* Add unit or integration tests for fixed or changed functionality (if a test suite already exists).
* Address a single concern in the least number of changed lines as possible.
* Include documentation in the repo (**TODO** sphinx documentation).
* Be accompanied by a complete Pull Request template (loaded automatically when a PR is created).

For changes that address core functionality or would require breaking changes (e.g. a major release), it's best to open an Issue to discuss your proposal first. This is not required but can save time creating and reviewing changes.

In general, we follow the ["fork-and-pull" Git workflow](https://github.com/susam/gitpr)

1. Fork the repository to your own Github account
2. Clone the project to your machine
3. Create a branch locally with a succinct but descriptive name
4. Commit changes to the branch
5. Following any formatting and testing guidelines specific to this repo
6. Push changes to your fork
7. Open a PR in our repository and follow the PR template so that we can efficiently review the changes.

## Maintenance

This is a minimal Python library that uses [poetry](https://python-poetry.org) for packaging and dependency management. To assist automating the maintence process, this repository provides [pre-commit](https://pre-commit.com/) hooks (for [isort](https://pycqa.github.io/isort/), [Black](https://black.readthedocs.io/en/stable/), [Flake8](https://flake8.pycqa.org/en/latest/) and [mypy](https://mypy.readthedocs.io/en/stable/)) and automated tests using [pytest](https://pytest.org/) and [GitHub Actions](https://github.com/features/actions). Pre-commit hooks are automatically kept updated with a dedicated GitHub Action, this can be removed and replace with [pre-commit.ci](https://pre-commit.ci). It was developed by the [Imperial College Research Computing Service](https://www.imperial.ac.uk/admin-services/ict/self-service/research-support/rcs/).

### Testing

To modify, test and request changes to this repository:

1. [Download and install Poetry](https://python-poetry.org/docs/#installation) following the instructions for the target OS.
2. Clone `git@github.com:calgray/athreading.git` and change working directory
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

6. Run all checks and tests:

   ```bash
    pre-commit run --all-files
    pytest --benchmark-enable
   ```

### Publishing

The GitHub workflow includes an action to publish on release.

When preparing for a release, ensure:

* A suitable version increment complient with [Semantic Versioning 2.0.0](https://semver.org/) is made to `pyproject.toml` and `__init__.py`
* The Changelog is updated with the new version and contains a short developer facing summary of introduced changes
* A git tag is created in the same format as the pyproject.toml version (e.g. `0.1.0`)
* A Github release is created using the tag and with user facing release notes summary
