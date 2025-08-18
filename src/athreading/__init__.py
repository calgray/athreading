"""Execute computations asnychronously on a background thread."""

from .aliases import AsyncGeneratorContext, AsyncIteratorContext
from .callable import call
from .callback_iterator import CallbackThreadedAsyncIterator, iterate_callback
from .generator import ThreadedAsyncGenerator, generate
from .iterator import ThreadedAsyncIterator, iterate

__version__ = "0.2.1"


__all__ = (
    "call",
    "iterate_callback",
    "iterate",
    "generate",
    "AsyncIteratorContext",
    "AsyncGeneratorContext",
    "ThreadedAsyncIterator",
    "CallbackThreadedAsyncIterator",
    "ThreadedAsyncGenerator",
)
