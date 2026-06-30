# -*- coding: utf-8 -*-
"""Execution Trace — 全链路请求追踪（用户输入 → LLM → TTS）。"""

from neuralpal.trace.context import clear_trace, get_trace, set_trace, trace_scope
from neuralpal.trace.recorder import ExecutionTraceRecorder, merge_client_patch, new_trace_id

__all__ = [
    "ExecutionTraceRecorder",
    "clear_trace",
    "get_trace",
    "merge_client_patch",
    "new_trace_id",
    "set_trace",
    "trace_scope",
]
