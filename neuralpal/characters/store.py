# -*- coding: utf-8 -*-
"""AI 角色本地 JSON 存储。"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from neuralpal.characters.models import AICharacter, CharacterCreateRequest, CharacterUpdateRequest
from neuralpal.characters.mbti_intros import build_intro_paragraphs
from neuralpal.config import get_settings


def _characters_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    settings = get_settings()
    custom = getattr(settings, "characters_data_path", None)
    if custom:
        return Path(custom)
    return root / "data" / "characters" / "characters.json"


class CharacterStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _characters_path()
        self._lock = threading.Lock()

    def _ensure_file(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("[]", encoding="utf-8")

    def _read_all(self) -> list[AICharacter]:
        self._ensure_file()
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
        out: list[AICharacter] = []
        for item in raw:
            try:
                out.append(AICharacter.model_validate(item))
            except Exception:
                continue
        return out

    def _write_all(self, items: list[AICharacter]) -> None:
        self._ensure_file()
        payload = [c.model_dump() for c in items]
        self._path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_characters(self) -> list[AICharacter]:
        with self._lock:
            items = self._read_all()
        return sorted(items, key=lambda c: c.created_at, reverse=True)

    def get_character(self, character_id: str) -> AICharacter | None:
        with self._lock:
            for c in self._read_all():
                if c.id == character_id:
                    return c
        return None

    def create_character(self, req: CharacterCreateRequest) -> AICharacter:
        intro = build_intro_paragraphs(req.name.strip(), req.user_mbti)
        char = AICharacter(
            name=req.name.strip(),
            user_mbti=req.user_mbti,
            ai_type=req.ai_type.strip(),
            personality_description=req.personality_description.strip(),
            intimacy=req.intimacy,
            initiative=req.initiative,
            emotion_expression=req.emotion_expression,
            rationality=req.rationality,
            humor=req.humor,
            independent_world=req.independent_world,
            quiet_companion=req.quiet_companion,
            first_intro_paragraphs=intro,
            intro_delivered=False,
        )
        with self._lock:
            items = self._read_all()
            existing_ids = {c.id for c in items}
            while char.id in existing_ids:
                char = char.model_copy(update={"id": uuid4().hex[:12]})
            items.append(char)
            self._write_all(items)
        return char

    def update_character(
        self, character_id: str, req: CharacterUpdateRequest
    ) -> AICharacter | None:
        with self._lock:
            items = self._read_all()
            for idx, c in enumerate(items):
                if c.id != character_id:
                    continue
                data = c.model_dump()
                updates = req.model_dump(exclude_unset=True)
                for key, val in updates.items():
                    if val is not None:
                        if key == "ending_signature":
                            data[key] = (val or "").strip() or None
                        elif key in ("name", "personality_description", "ai_type") and isinstance(
                            val, str
                        ):
                            data[key] = val.strip()
                        else:
                            data[key] = val
                data["updated_at"] = datetime.now(timezone.utc).isoformat()
                updated = AICharacter.model_validate(data)
                items[idx] = updated
                self._write_all(items)
                return updated
        return None

    def save_intro_paragraphs(self, character_id: str, paragraphs: list[str]) -> AICharacter | None:
        with self._lock:
            items = self._read_all()
            for idx, c in enumerate(items):
                if c.id != character_id:
                    continue
                data = c.model_dump()
                data["first_intro_paragraphs"] = [p.strip() for p in paragraphs if p.strip()]
                data["updated_at"] = datetime.now(timezone.utc).isoformat()
                updated = AICharacter.model_validate(data)
                items[idx] = updated
                self._write_all(items)
                return updated
        return None

    def mark_intro_delivered(self, character_id: str) -> AICharacter | None:
        with self._lock:
            items = self._read_all()
            for idx, c in enumerate(items):
                if c.id != character_id:
                    continue
                data = c.model_dump()
                data["intro_delivered"] = True
                data["updated_at"] = datetime.now(timezone.utc).isoformat()
                updated = AICharacter.model_validate(data)
                items[idx] = updated
                self._write_all(items)
                return updated
        return None

    def delete_character(self, character_id: str) -> bool:
        with self._lock:
            items = self._read_all()
            new_items = [c for c in items if c.id != character_id]
            if len(new_items) == len(items):
                return False
            self._write_all(new_items)
            return True


_store: CharacterStore | None = None


def get_character_store() -> CharacterStore:
    global _store
    if _store is None:
        _store = CharacterStore()
    return _store
