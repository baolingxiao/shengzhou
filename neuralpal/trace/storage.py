# -*- coding: utf-8 -*-
"""Trace JSON 持久化。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TRACE_DIR: Path | None = None


def traces_dir() -> Path:
    global _TRACE_DIR
    if _TRACE_DIR is None:
        root = Path(__file__).resolve().parents[2]
        _TRACE_DIR = root / "data" / "traces"
        _TRACE_DIR.mkdir(parents=True, exist_ok=True)
    return _TRACE_DIR


def trace_path(trace_id: str) -> Path:
    safe = "".join(c for c in trace_id if c.isalnum() or c in "-_")
    return traces_dir() / f"{safe}.json"


def save_trace(trace_id: str, data: dict[str, Any]) -> Path:
    path = trace_path(trace_id)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_trace(trace_id: str) -> dict[str, Any] | None:
    path = trace_path(trace_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("读取 trace 失败 %s: %s", trace_id, exc)
        return None


def _merge_chunk_lists(existing: list[Any], incoming: list[Any]) -> list[Any]:
    by_idx: dict[Any, dict[str, Any]] = {}
    for c in existing:
        if isinstance(c, dict):
            by_idx[c.get("index")] = dict(c)
    for c in incoming:
        if isinstance(c, dict):
            idx = c.get("index")
            by_idx[idx] = {**by_idx.get(idx, {}), **c}
    return [by_idx[i] for i in sorted(by_idx)]


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, val in patch.items():
        if key in out and isinstance(out[key], dict) and isinstance(val, dict):
            merged = deep_merge(out[key], val)
            if key == "tts" and "chunks" in val and isinstance(val.get("chunks"), list):
                prev_chunks = out[key].get("chunks") if isinstance(out[key].get("chunks"), list) else []
                merged["chunks"] = _merge_chunk_lists(prev_chunks, val["chunks"])
            out[key] = merged
        elif key in out and isinstance(out[key], list) and isinstance(val, list):
            if key == "errors":
                out[key] = out[key] + val
            elif val and isinstance(val[0], dict) and "index" in val[0]:
                out[key] = _merge_chunk_lists(out[key], val)
            else:
                out[key] = val
        else:
            out[key] = val
    return out
