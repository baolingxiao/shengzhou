# -*- coding: utf-8 -*-
"""开发模式：伴侣/记忆/生活上下文加载状态（不含用户聊天正文）。"""

from __future__ import annotations

from typing import Any

from neuralpal.config import get_settings


def is_dev_context_status_enabled() -> bool:
    return bool(getattr(get_settings(), "neuralpal_dev_context_status_enabled", False))


def build_dev_context_status(
    session_id: str,
    *,
    character_id: str | None = None,
    persona_loaded: bool | None = None,
    short_term_loaded: bool | None = None,
    long_term_loaded: bool | None = None,
    life_context_loaded: bool | None = None,
    shared_memory_loaded: bool | None = None,
) -> dict[str, Any]:
    from neuralpal.characters.prompt_bridge import resolve_character_for_session
    from neuralpal.chat.response_signature import resolve_ending_signature
    from neuralpal.companion_life.bridge import resolve_companion_instance_id_for_session
    from neuralpal.companion_life.config import is_companion_life_enabled
    from neuralpal.companion_life.identity import resolve_profile_key_for_character

    sid = (session_id or "default").strip()[:120] or "default"
    char = resolve_character_for_session(sid, character_id=character_id)
    iid = resolve_companion_instance_id_for_session(sid) if char else None
    pk = resolve_profile_key_for_character(char) if char else ""

    if persona_loaded is None:
        persona_loaded = char is not None

    if short_term_loaded is None:
        try:
            from neuralpal.memory.character_palace import palace_paths_for_character_id

            root, _, _ = palace_paths_for_character_id(character_id)
            snap = root / "01_短期记忆" / f"{sid}.md"
            short_term_loaded = snap.is_file()
        except Exception:
            short_term_loaded = False

    if long_term_loaded is None:
        try:
            from neuralpal.memory.chroma_runtime import get_chroma_client
            from neuralpal.memory.character_palace import palace_paths_for_character_id
            from neuralpal.memory.constants import LONG_TERM_COLLECTION_NAME

            _, chroma_path, _ = palace_paths_for_character_id(character_id)
            client = get_chroma_client(chroma_path)
            col = client.get_collection(LONG_TERM_COLLECTION_NAME)
            long_term_loaded = col.count() > 0
        except Exception:
            try:
                from neuralpal.memory.chroma_runtime import get_chroma_client
                from neuralpal.config import get_settings as gs

                s = gs()
                client = get_chroma_client(Path(s.long_term_memory_chroma_path))
                col = client.get_collection("neuralpal_long_term_memory")
                long_term_loaded = col.count() > 0
            except Exception:
                long_term_loaded = False

    if life_context_loaded is None:
        life_context_loaded = False
        if is_companion_life_enabled() and iid:
            try:
                from datetime import date

                from neuralpal.companion_life.companion_life_service import get_companion_life_service

                svc = get_companion_life_service()
                diary = svc.get_today_diary(sid, iid)
                state = svc.get_current_state(sid, iid)
                life_context_loaded = diary is not None or bool(
                    (state.focus_topic or "").strip()
                )
            except Exception:
                life_context_loaded = False

    if shared_memory_loaded is None:
        shared_memory_loaded = False
        if iid:
            try:
                from neuralpal.companion_life.repositories import SharedMemoryRepository

                repo = SharedMemoryRepository()
                shared_memory_loaded = len(repo.recent(sid, iid, limit=1)) > 0
            except Exception:
                shared_memory_loaded = False

    sig = resolve_ending_signature(char) if char else ""

    return {
        "session_id": sid,
        "companion_instance_id": iid or "",
        "character_name": char.name if char else "",
        "profile_key": pk,
        "ending_signature": sig,
        "persona_loaded": bool(persona_loaded),
        "short_term_memory_loaded": bool(short_term_loaded),
        "long_term_memory_loaded": bool(long_term_loaded),
        "life_context_loaded": bool(life_context_loaded),
        "shared_memory_loaded": bool(shared_memory_loaded),
    }


def format_dev_context_status_lines(status: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Companion Instance ID: {status.get('companion_instance_id') or '—'}",
            f"Character Name: {status.get('character_name') or '—'}",
            f"Profile Key: {status.get('profile_key') or '—'}",
            f"Ending Signature: {status.get('ending_signature') or '—'}",
            f"Persona Loaded: {status.get('persona_loaded')}",
            f"Short-Term Memory Loaded: {status.get('short_term_memory_loaded')}",
            f"Long-Term Memory Loaded: {status.get('long_term_memory_loaded')}",
            f"Life Context Loaded: {status.get('life_context_loaded')}",
            f"Shared Memory Loaded: {status.get('shared_memory_loaded')}",
        ]
    )


def log_dev_context_status(session_id: str, **kwargs: object) -> None:
    if not is_dev_context_status_enabled():
        return
    status = build_dev_context_status(session_id, **kwargs)
    import sys

    print(
        "[NeuralPal·dev-context]\n" + format_dev_context_status_lines(status),
        file=sys.stderr,
    )
