"""Tests for the main module."""

from importlib.metadata import version

import athreading

PACKAGE_VER = version(athreading.__name__)


def test_module_version():
    """Check that the module and package versions match."""
    assert athreading.__version__ == PACKAGE_VER
