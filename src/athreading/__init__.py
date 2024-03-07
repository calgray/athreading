"""Execute computations asnychronously on a background thread."""

from .callable import call, wrap_callable
from .generator import ThreadedAsyncGenerator, generate
from .iterator import ThreadedAsyncIterator, fiterate, iterate, wrap_iterator

__version__ = "0.1.2"


__all__ = (
    "call",
    "wrap_callable",
    "iterate",
    "wrap_iterator",
    "fiterate",
    "generate",
    "ThreadedAsyncIterator",
    "ThreadedAsyncGenerator",
)
