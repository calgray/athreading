"""Execute computations asnychronously on a background thread."""

from .aliases import AsyncGeneratorContext, AsyncIteratorContext
from .callable import call
from .callback_iterator import CallbackThreadedAsyncIterator, iterate_callback
from .callback_single import single_callback
from .generator import ThreadedAsyncGenerator, generate
from .iterator import ThreadedAsyncIterator, iterate

__version__ = "0.3.0"


__all__ = (
    "AsyncGeneratorContext",
    "AsyncIteratorContext",
    "CallbackThreadedAsyncIterator",
    "ThreadedAsyncGenerator",
    "ThreadedAsyncIterator",
    "call",
    "generate",
    "iterate",
    "iterate_callback",
    "single_callback",
)
