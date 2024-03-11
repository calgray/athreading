"""Execute computations asnychronously on a background thread."""

from .callable import call
from .generator import ThreadedAsyncGenerator, generate
from .iterator import ThreadedAsyncIterator, _fiterate, _iterate_decorator, iterate

__version__ = "0.1.2"


__all__ = (
    "call",
    "iterate",
    "_iterate_decorator",
    "_fiterate",
    "generate",
    "ThreadedAsyncIterator",
    "ThreadedAsyncGenerator",
)
