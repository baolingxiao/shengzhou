# -*- coding: utf-8 -*-
"""会话 ↔ AI 角色绑定（本地 JSON）。"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from neuralpal.config import get_settings


def _binding_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    custom = getattr(get_settings(), "characters_data_path", None)
    if custom:
        return Path(custom).parent / "session_bindings.json"
    return root / "data" / "characters" / "session_bindings.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionCharacterBinding:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _binding_path()
        self._lock = threading.Lock()

    def _ensure(self) -> dict[str, object]:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("{}", encoding="utf-8")
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}

    def _write(self, data: dict[str, object]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _normalize_entry(raw: object) -> dict[str, str] | None:
        if isinstance(raw, str):
            cid = raw.strip()
            return {"character_id": cid, "activated_at": ""} if cid else None
        if isinstance(raw, dict):
            cid = str(raw.get("character_id", "") or "").strip()
            if not cid:
                return None
            return {
                "character_id": cid,
                "activated_at": str(raw.get("activated_at", "") or ""),
            }
        return None

    def bind(self, session_id: str, character_id: str, *, activate: bool = False) -> None:
        sid = (session_id or "default").strip()[:120] or "default"
        cid = (character_id or "").strip()
        if not cid:
            return
        with self._lock:
            data = self._ensure()
            entry: dict[str, str] = {"character_id": cid}
            if activate:
                entry["activated_at"] = _now_iso()
            else:
                prev = self._normalize_entry(data.get(sid))
                if prev and prev.get("activated_at"):
                    entry["activated_at"] = prev["activated_at"]
            data[sid] = entry
            self._write(data)

    def activate(self, session_id: str, character_id: str) -> None:
        self.bind(session_id, character_id, activate=True)

    def unbind(self, session_id: str) -> None:
        sid = (session_id or "default").strip()[:120] or "default"
        with self._lock:
            data = self._ensure()
            data.pop(sid, None)
            self._write(data)

    def get_character_id(self, session_id: str) -> str | None:
        sid = (session_id or "default").strip()[:120] or "default"
        with self._lock:
            entry = self._normalize_entry(self._ensure().get(sid))
            return entry["character_id"] if entry else None

    def get_activated_at(self, session_id: str) -> str | None:
        sid = (session_id or "default").strip()[:120] or "default"
        with self._lock:
            entry = self._normalize_entry(self._ensure().get(sid))
            if not entry:
                return None
            ts = entry.get("activated_at", "").strip()
            return ts or None


_binding: SessionCharacterBinding | None = None


def get_session_character_binding() -> SessionCharacterBinding:
    global _binding
    if _binding is None:
        _binding = SessionCharacterBinding()
    return _binding
