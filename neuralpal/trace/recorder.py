# -*- coding: utf-8 -*-
"""Execution Trace 记录器：采集全链路步骤、耗时与数据快照。"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from neuralpal.trace.sanitize import sanitize_dict, sanitize_messages
from neuralpal.trace.storage import deep_merge, load_trace, save_trace

logger = logging.getLogger(__name__)


def new_trace_id() -> str:
    return str(uuid.uuid4())


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_document(
    *,
    trace_id: str,
    user_input: str = "",
    session_id: str = "",
    character_id: str = "",
) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "created_at": _utc_now(),
        "user_input": user_input,
        "session_id": session_id,
        "character_id": character_id,
        "timings": {
            "total_ms": 0,
            "preprocess_ms": 0,
            "memory_ms": 0,
            "prompt_build_ms": 0,
            "route_ms": 0,
            "llm_ms": 0,
            "compliance_ms": 0,
            "postprocess_ms": 0,
            "tts_total_ms": 0,
        },
        "prompt": {
            "system_prompt": "",
            "messages": [],
        },
        "memory": {
            "short_term": [],
            "long_term": [],
            "chroma_results": [],
        },
        "llm": {
            "provider": "",
            "model": "",
            "parameters": {},
            "raw_response": "",
            "final_response": "",
        },
        "postprocess": {
            "segments": [],
            "final_text_for_tts": "",
        },
        "tts": {
            "enabled": False,
            "provider": None,
            "model": None,
            "chunks": [],
        },
        "pipeline": {
            "work_preprocess": None,
            "agent_preprocess": None,
            "route_classifier": None,
            "backend_request_received_at": None,
            "backend_response_at": None,
            "frontend": {
                "request_sent_at": None,
                "response_received_at": None,
                "response_ms": None,
                "tts_triggered": None,
            },
            "api_response": None,
        },
        "errors": [],
    }


class ExecutionTraceRecorder:
    """单次请求的 Trace 采集器（线程内通过 ContextVar 传递）。"""

    def __init__(
        self,
        trace_id: str,
        *,
        user_input: str = "",
        session_id: str = "",
        character_id: str = "",
    ) -> None:
        self.trace_id = trace_id
        self._data = _empty_document(
            trace_id=trace_id,
            user_input=user_input,
            session_id=session_id,
            character_id=character_id,
        )
        self._t0 = time.perf_counter()
        self._marks: dict[str, float] = {"_start": self._t0}
        self._span_starts: dict[str, float] = {}

    def log_marker(self) -> None:
        logger.info("[TRACE] %s", self.trace_id)

    def mark(self, name: str) -> None:
        self._marks[name] = time.perf_counter()

    def span_start(self, name: str) -> None:
        self._span_starts[name] = time.perf_counter()

    def span_end(self, name: str, timing_key: str) -> float:
        start = self._span_starts.pop(name, None)
        if start is None:
            return 0.0
        ms = (time.perf_counter() - start) * 1000.0
        self._data["timings"][timing_key] = round(
            self._data["timings"].get(timing_key, 0) + ms, 2
        )
        return ms

    def elapsed_since_start_ms(self) -> float:
        return round((time.perf_counter() - self._t0) * 1000.0, 2)

    def record_backend_received(self) -> None:
        self._data["pipeline"]["backend_request_received_at"] = _utc_now()
        self.mark("backend_received")

    def record_work_preprocess(self, payload: dict[str, Any] | None) -> None:
        self._data["pipeline"]["work_preprocess"] = sanitize_dict(payload) if payload else None

    def record_agent_preprocess(self, payload: dict[str, Any] | None) -> None:
        self._data["pipeline"]["agent_preprocess"] = sanitize_dict(payload) if payload else None

    def record_memory(
        self,
        *,
        short_term: list[dict[str, str]] | None = None,
        long_term: list[Any] | None = None,
        chroma_results: list[dict[str, Any]] | None = None,
    ) -> None:
        if short_term is not None:
            self._data["memory"]["short_term"] = sanitize_messages(short_term)
        if long_term is not None:
            self._data["memory"]["long_term"] = long_term
        if chroma_results is not None:
            self._data["memory"]["chroma_results"] = [
                sanitize_dict(c) if isinstance(c, dict) else c for c in chroma_results
            ]

    def record_prompt(self, system_prompt: str, messages: list[dict[str, str]]) -> None:
        self._data["prompt"]["system_prompt"] = system_prompt
        self._data["prompt"]["messages"] = sanitize_messages(messages)

    def record_route(self, route: str, provider: str, model: str, parameters: dict | None = None) -> None:
        self._data["pipeline"]["route_classifier"] = route
        self._data["llm"]["provider"] = provider
        self._data["llm"]["model"] = model
        if parameters:
            self._data["llm"]["parameters"] = sanitize_dict(parameters)

    def record_llm_raw(self, raw: str) -> None:
        self._data["llm"]["raw_response"] = raw

    def record_llm_final(self, text: str) -> None:
        self._data["llm"]["final_response"] = text

    def record_postprocess(self, segments: list[str], final_text_for_tts: str) -> None:
        self._data["postprocess"]["segments"] = segments
        self._data["postprocess"]["final_text_for_tts"] = final_text_for_tts

    def record_api_response(self, payload: dict[str, Any]) -> None:
        self._data["pipeline"]["api_response"] = sanitize_dict(payload)

    def record_tts_meta(
        self,
        *,
        enabled: bool,
        provider: str | None,
        model: str | None,
        input_text: str,
        chunk_texts: list[str] | None = None,
    ) -> None:
        self._data["tts"]["enabled"] = enabled
        self._data["tts"]["provider"] = provider
        self._data["tts"]["model"] = model
        if not self._data["postprocess"]["final_text_for_tts"]:
            self._data["postprocess"]["final_text_for_tts"] = input_text
        if chunk_texts is not None:
            existing = {c.get("index"): c for c in self._data["tts"]["chunks"]}
            for i, text in enumerate(chunk_texts):
                prev = existing.get(i, {})
                existing[i] = {
                    "index": i,
                    "text": text,
                    "request_ms": prev.get("request_ms", 0),
                    "audio_duration_ms": prev.get("audio_duration_ms", 0),
                    "played": prev.get("played", False),
                    "play_start_at": prev.get("play_start_at"),
                    "play_end_at": prev.get("play_end_at"),
                }
            self._data["tts"]["chunks"] = [existing[i] for i in sorted(existing)]

    def record_tts_chunk_request(
        self,
        index: int,
        text: str,
        request_ms: float,
        *,
        cached: bool = False,
    ) -> None:
        chunks = {c.get("index"): c for c in self._data["tts"]["chunks"]}
        prev = chunks.get(index, {})
        chunks[index] = {
            "index": index,
            "text": text,
            "request_ms": round(request_ms, 2),
            "cached": cached,
            "audio_duration_ms": prev.get("audio_duration_ms", 0),
            "played": prev.get("played", False),
            "play_start_at": prev.get("play_start_at"),
            "play_end_at": prev.get("play_end_at"),
        }
        self._data["tts"]["chunks"] = [chunks[i] for i in sorted(chunks)]
        total = sum(c.get("request_ms", 0) for c in self._data["tts"]["chunks"])
        self._data["timings"]["tts_total_ms"] = round(total, 2)

    def record_error(self, step: str, error: str, *, exc_type: str | None = None) -> None:
        self._data["errors"].append(
            {
                "step": step,
                "error": error,
                "type": exc_type,
                "at": _utc_now(),
            }
        )

    def to_dict(self) -> dict[str, Any]:
        self._data["timings"]["total_ms"] = self.elapsed_since_start_ms()
        self._data["pipeline"]["backend_response_at"] = _utc_now()
        return self._data

    def save(self) -> None:
        path = save_trace(self.trace_id, self.to_dict())
        logger.info("[TRACE] saved %s", path)

    @classmethod
    def from_existing(cls, trace_id: str) -> ExecutionTraceRecorder:
        data = load_trace(trace_id) or _empty_document(trace_id=trace_id)
        rec = cls(
            trace_id,
            user_input=str(data.get("user_input") or ""),
            session_id=str(data.get("session_id") or ""),
            character_id=str(data.get("character_id") or ""),
        )
        rec._data = data
        return rec

    def merge_client(self, patch: dict[str, Any]) -> dict[str, Any]:
        existing = load_trace(self.trace_id) or self._data
        merged = deep_merge(existing, patch)
        self._data = merged
        save_trace(self.trace_id, merged)
        return merged


def merge_client_patch(trace_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    existing = load_trace(trace_id) or _empty_document(trace_id=trace_id)
    merged = deep_merge(existing, patch)
    save_trace(trace_id, merged)
    logger.info("[TRACE] client patch %s", trace_id)
    return merged
