"""Tests for the main module."""

from importlib.metadata import version

from athreading import __version__

PACKAGE_VER = version("athreading")


def test_module_version():
    """Check that the module and package versions match."""
    assert __version__ == PACKAGE_VER
