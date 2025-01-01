"""Execute computations asnychronously on a background thread."""

from .callable import call
from .generator import ThreadedAsyncGenerator, generate
from .iterator import ThreadedAsyncIterator, iterate
from .type_aliases import AsyncGeneratorContext, AsyncIteratorContext

__version__ = "0.2.1"


__all__ = (
    "call",
    "iterate",
    "generate",
    "AsyncIteratorContext",
    "AsyncGeneratorContext",
    "ThreadedAsyncIterator",
    "ThreadedAsyncGenerator",
)
