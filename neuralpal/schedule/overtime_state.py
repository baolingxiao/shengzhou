# -*- coding: utf-8 -*-
"""会话级加班状态（待执行任务 + 是否已授权加班）。"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from neuralpal.config import get_settings

logger = logging.getLogger(__name__)


def _state_dir() -> Path:
    root = get_settings().agent_state_dir
    root.mkdir(parents=True, exist_ok=True)
    return root


def _path_for_session(session_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id.strip())[:120]
    safe = safe or "default"
    return _state_dir() / f"{safe}_overtime.json"


@dataclass
class OvertimeState:
    session_id: str
    deferred_task_text: str = ""
    awaiting_overtime_consent: bool = False
    overtime_active: bool = False
    overtime_granted_at: str = ""
    overtime_expires_at: str = ""
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OvertimeState:
        return cls(
            session_id=str(data.get("session_id") or "default"),
            deferred_task_text=str(data.get("deferred_task_text") or ""),
            awaiting_overtime_consent=bool(data.get("awaiting_overtime_consent")),
            overtime_active=bool(data.get("overtime_active")),
            overtime_granted_at=str(data.get("overtime_granted_at") or ""),
            overtime_expires_at=str(data.get("overtime_expires_at") or ""),
            updated_at=str(data.get("updated_at") or datetime.now(timezone.utc).isoformat()),
        )


def load_overtime_state(session_id: str) -> OvertimeState:
    path = _path_for_session(session_id)
    sid = (session_id or "default").strip()[:120] or "default"
    if not path.is_file():
        return OvertimeState(session_id=sid)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        state = OvertimeState.from_dict(data)
        state.session_id = sid
        return state
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("load_overtime_state failed session=%s: %s", session_id, exc)
        return OvertimeState(session_id=sid)


def save_overtime_state(state: OvertimeState) -> None:
    path = _path_for_session(state.session_id)
    state.updated_at = datetime.now(timezone.utc).isoformat()
    try:
        path.write_text(
            json.dumps(state.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        logger.error("save_overtime_state failed: %s", exc)
        raise


def clear_overtime_state(session_id: str) -> None:
    path = _path_for_session(session_id)
    try:
        if path.is_file():
            path.unlink()
    except OSError as exc:
        logger.warning("clear_overtime_state failed session=%s: %s", session_id, exc)


def clear_deferred_task(session_id: str) -> None:
    state = load_overtime_state(session_id)
    state.deferred_task_text = ""
    state.awaiting_overtime_consent = False
    if not state.overtime_active:
        clear_overtime_state(session_id)
        return
    save_overtime_state(state)


__all__ = [
    "OvertimeState",
    "clear_deferred_task",
    "clear_overtime_state",
    "load_overtime_state",
    "save_overtime_state",
]
