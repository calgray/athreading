"""Execute computations asnychronously on a background thread."""

from .callable import call
from .generator import ThreadedAsyncGenerator, generate
from .iterator import ThreadedAsyncIterator, _fiterate, iterate

__version__ = "0.1.2"


__all__ = (
    "call",
    "iterate",
    "_fiterate",
    "generate",
    "ThreadedAsyncIterator",
    "ThreadedAsyncGenerator",
)
