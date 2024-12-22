"""Interfaces"""

from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import AbstractAsyncContextManager
from typing import TypeVar

_YieldT = TypeVar("_YieldT")
_SendT = TypeVar("_SendT")


class AsyncIteratorContext(
    AsyncIterator[_YieldT], AbstractAsyncContextManager[AsyncIterator[_YieldT]]
):
    """Interface for safe-use of a athreading AsyncIterator"""


# AsyncIteratorContext = AbstractAsyncContextManager[AsyncIterator[_YieldT]]


class AsyncGeneratorContext(
    AsyncGenerator[_YieldT, _SendT],
    AbstractAsyncContextManager[AsyncGenerator[_YieldT, _SendT]],
):
    """Interface for safe-use of a athreading AsyncGenerator"""


# AsyncGeneratorContext = AbstractAsyncContextManager[AsyncGenerator[_YieldT, _SendT]]
