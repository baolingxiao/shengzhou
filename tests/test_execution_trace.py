# -*- coding: utf-8 -*-
"""Execution Trace 单元测试（无 LLM 调用）。"""

from __future__ import annotations

import json
from pathlib import Path

from neuralpal.trace.recorder import ExecutionTraceRecorder, merge_client_patch, new_trace_id
from neuralpal.trace.sanitize import sanitize_dict
from neuralpal.trace.storage import load_trace, trace_path


def test_new_trace_id_unique():
    a = new_trace_id()
    b = new_trace_id()
    assert a != b
    assert len(a) >= 32


def test_sanitize_redacts_secrets():
    data = {"api_key": "sk-abcdef1234567890", "password": "secret", "text": "hello"}
    out = sanitize_dict(data)
    assert out["api_key"] == "[REDACTED]"
    assert out["password"] == "[REDACTED]"
    assert out["text"] == "hello"


def test_recorder_save_and_load(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "neuralpal.trace.storage.traces_dir",
        lambda: tmp_path,
    )
    tid = new_trace_id()
    rec = ExecutionTraceRecorder(
        tid,
        user_input="你好",
        session_id="test-session",
        character_id="char-1",
    )
    rec.record_work_preprocess({"work_mode": "companion", "handled": False})
    rec.record_prompt("system", [{"role": "user", "content": "你好"}])
    rec.record_route("general", "doubao", "doubao-pro", {"temperature": 0.7})
    rec.record_llm_raw("草稿")
    rec.record_llm_final("最终回复")
    rec.record_postprocess(["最终回复"], "最终回复")
    rec.save()

    path = trace_path(tid)
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["trace_id"] == tid
    assert data["user_input"] == "你好"
    assert data["llm"]["final_response"] == "最终回复"
    assert data["pipeline"]["work_preprocess"]["work_mode"] == "companion"


def test_merge_client_patch_chunks(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "neuralpal.trace.storage.traces_dir",
        lambda: tmp_path,
    )
    tid = new_trace_id()
    rec = ExecutionTraceRecorder(tid, user_input="hi")
    rec.record_tts_meta(
        enabled=True,
        provider="elevenlabs",
        model="eleven_multilingual_v2",
        input_text="你好",
        chunk_texts=["你好"],
    )
    rec.record_tts_chunk_request(0, "你好", 120.5, cached=False)
    rec.save()

    merged = merge_client_patch(
        tid,
        {
            "pipeline": {"frontend": {"tts_triggered": True, "response_ms": 800}},
            "tts": {
                "chunks": [
                    {
                        "index": 0,
                        "played": True,
                        "audio_duration_ms": 900,
                        "play_start_at": "2026-01-01T00:00:00Z",
                        "play_end_at": "2026-01-01T00:00:01Z",
                    }
                ]
            },
        },
    )
    chunk = merged["tts"]["chunks"][0]
    assert chunk["request_ms"] == 120.5
    assert chunk["played"] is True
    assert chunk["audio_duration_ms"] == 900
    assert merged["pipeline"]["frontend"]["response_ms"] == 800


def test_from_existing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "neuralpal.trace.storage.traces_dir",
        lambda: tmp_path,
    )
    tid = new_trace_id()
    ExecutionTraceRecorder(tid, user_input="x").save()
    loaded = ExecutionTraceRecorder.from_existing(tid)
    assert loaded.trace_id == tid
    assert load_trace(tid) is not None
