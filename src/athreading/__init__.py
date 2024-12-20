"""Execute computations asnychronously on a background thread."""

from .callable import call
from .generator import ThreadedAsyncGenerator, generate
from .iterator import ThreadedAsyncIterator, iterate

__version__ = "0.2.0"


__all__ = (
    "call",
    "iterate",
    "generate",
    "ThreadedAsyncIterator",
    "ThreadedAsyncGenerator",
)
