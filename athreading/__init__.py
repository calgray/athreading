"""Execute computations asnychronously on a background thread."""

from .call import call
from .generator import ThreadedAsyncGenerator, generate
from .iterator import ThreadedAsyncIterator, fiterate, iterate

__version__ = "0.1.0"


__all__ = (
    "call",
    "iterate",
    "fiterate",
    "generate",
    "ThreadedAsyncIterator",
    "ThreadedAsyncGenerator",
)
