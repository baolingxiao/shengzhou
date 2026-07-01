# -*- coding: utf-8 -*-
"""记忆检索透明化：记录每轮对话选中的 ST_/MT_/LT_ 编号。"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from neuralpal.memory.palace_layout import _safe_session_slug, publish_palace_file

logger = logging.getLogger(__name__)

_LOG_DIR_NAME = ".memory_transparency"
_lock = threading.Lock()
_MAX_RECORDS = 200


def _log_dir(palace_root: Path) -> Path:
    d = palace_root.resolve() / _LOG_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def _log_file(palace_root: Path, session_id: str) -> Path:
    slug = _safe_session_slug(session_id)
    return _log_dir(palace_root) / f"{slug}.jsonl"


def append_transparency_record(
    *,
    palace_root: Path,
    session_id: str,
    user_query: str,
    memory_ids: list[str],
    reasoning: str = "",
    reply_preview: str = "",
    vector_used: bool = False,
    gate: str = "general",
) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "user_query": (user_query or "").strip()[:2000],
        "memory_ids": [m.strip().upper() for m in memory_ids if m],
        "reasoning": (reasoning or "").strip()[:1000],
        "reply_preview": (reply_preview or "").strip()[:240],
        "vector_used": bool(vector_used),
        "gate": gate,
    }
    fp = _log_file(palace_root, session_id)
    line = json.dumps(record, ensure_ascii=False)
    with _lock:
        try:
            with fp.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
            publish_palace_file(fp)
            _trim_file(fp)
        except OSError as exc:
            logger.warning("transparency log write failed: %s", exc)


def _trim_file(fp: Path) -> None:
    if not fp.is_file():
        return
    try:
        lines = fp.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    if len(lines) <= _MAX_RECORDS:
        return
    trimmed = lines[-_MAX_RECORDS:]
    fp.write_text("\n".join(trimmed) + "\n", encoding="utf-8")


def list_transparency_records(
    palace_root: Path,
    session_id: str,
    *,
    limit: int = 80,
) -> list[dict[str, Any]]:
    fp = _log_file(palace_root, session_id)
    if not fp.is_file():
        return []
    try:
        lines = fp.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in reversed(lines[-limit:]):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                out.append(row)
        except json.JSONDecodeError:
            continue
    return out
