# -*- coding: utf-8 -*-
"""ContextVar：当前请求绑定的 ExecutionTraceRecorder。"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from neuralpal.trace.recorder import ExecutionTraceRecorder

_current_trace: ContextVar[ExecutionTraceRecorder | None] = ContextVar(
    "execution_trace", default=None
)


def get_trace() -> ExecutionTraceRecorder | None:
    return _current_trace.get()


def set_trace(recorder: ExecutionTraceRecorder | None) -> None:
    _current_trace.set(recorder)


def clear_trace() -> None:
    _current_trace.set(None)


@contextmanager
def trace_scope(recorder: ExecutionTraceRecorder) -> Iterator[ExecutionTraceRecorder]:
    token = _current_trace.set(recorder)
    try:
        yield recorder
    finally:
        _current_trace.reset(token)
