"""Execute computations asnychronously on a background thread."""

from .aliases import AsyncGeneratorContext, AsyncIteratorContext
from .callable import call
from .generator import ThreadedAsyncGenerator, generate
from .iterator import ThreadedAsyncIterator, iterate

__version__ = "0.2.1"


__all__ = (
    "AsyncGeneratorContext",
    "AsyncIteratorContext",
    "ThreadedAsyncGenerator",
    "ThreadedAsyncIterator",
    "call",
    "generate",
    "iterate",
)
