"""Execute computations asnychronously on a background thread."""

from .callable import wrap_callable
from .generator import ThreadedAsyncGenerator, generate
from .iterator import ThreadedAsyncIterator, _fiterate, iterate

__version__ = "0.1.2"


__all__ = (
    "wrap_callable",
    "iterate",
    "_fiterate",
    "generate",
    "ThreadedAsyncIterator",
    "ThreadedAsyncGenerator",
)
