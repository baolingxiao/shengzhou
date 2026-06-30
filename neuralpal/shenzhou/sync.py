# -*- coding: utf-8 -*-
"""从贾维斯记忆宫殿收集当日对话，推送到沈昼世界模型。"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from neuralpal.config import get_settings
from neuralpal.memory.character_palace import palace_paths_for_character_id
from neuralpal.memory.memory_maintenance import MemoryMaintenanceService
from neuralpal.memory.memory_system import LongTermMemoryEngine
from neuralpal.shenzhou.client import sync_user_day
from neuralpal.shenzhou.event_sync import build_event_sync_digest, save_event_sync_digest

logger = logging.getLogger(__name__)

_MSG_HEADING = re.compile(r"^###\s+(用户|助手)\s*$", re.MULTILINE)


def _parse_short_term_messages(text: str) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    role: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^###\s+(用户|助手)\s*$", line.strip())
        if m:
            if role and buf:
                messages.append({"role": "user" if role == "用户" else "assistant", "content": "\n".join(buf).strip()})
            role = m.group(1)
            buf = []
            continue
        if role:
            buf.append(line)
    if role and buf:
        messages.append({"role": "user" if role == "用户" else "assistant", "content": "\n".join(buf).strip()})
    return [m for m in messages if m.get("content")]


def _maintenance_for_character(character_id: str | None = None) -> MemoryMaintenanceService:
    root, chroma, _ = palace_paths_for_character_id(character_id)
    lt = LongTermMemoryEngine(verbose=False, palace_root=root, chroma_path=chroma)
    return MemoryMaintenanceService(root=root, long_term_engine=lt, verbose=False)


def _read_short_term_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def collect_session_day_payload(
    session_id: str,
    day: date,
    *,
    character_id: str | None = None,
    user_display_name: str | None = None,
    trust_points: int | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    palace_root, _, _ = palace_paths_for_character_id(character_id)
    short_dir = palace_root / "01_短期记忆"
    short_file = short_dir / f"{session_id}.md"
    text = _read_short_term_file(short_file)
    messages = _parse_short_term_messages(text)

    daily_summary = ""
    maint = _maintenance_for_character(character_id)
    summary_path = maint._daily_summary_path(day)  # noqa: SLF001 — 复用维护路径
    if summary_path.is_file():
        daily_summary = summary_path.read_text(encoding="utf-8", errors="replace")

    chat_lines = [f"[{m['role']}] {m['content']}" for m in messages[-40:]]
    chat_summary = "\n".join(chat_lines).strip() or daily_summary[:2000] or "今日无显著对话记录。"
    event_digest = build_event_sync_digest(day, messages=messages[-60:])
    try:
        save_event_sync_digest(event_digest)
    except Exception:
        logger.debug("save event sync digest failed", exc_info=True)
    digest_text = str(event_digest.get("summary_text") or "").strip()
    if digest_text:
        if daily_summary.strip():
            daily_summary = f"{daily_summary.strip()}\n\n{digest_text}"
        else:
            daily_summary = digest_text
        if digest_text not in chat_summary:
            chat_summary = f"{chat_summary}\n\n{digest_text}"

    return {
        "date": day.isoformat(),
        "userEntitySlug": settings.shenzhou_user_entity_slug,
        "userDisplayName": user_display_name or settings.shenzhou_user_display_name,
        "jarvisSessionId": session_id,
        "chatSummary": chat_summary,
        "messages": messages[-40:],
        "dailySummary": daily_summary[:4000] if daily_summary else "",
        "trustPoints": trust_points,
    }


def push_user_day_to_world(
    session_id: str,
    day: date | None = None,
    *,
    character_id: str | None = None,
    user_display_name: str | None = None,
    trust_points: int | None = None,
) -> dict[str, Any]:
    target = day or date.today()
    payload = collect_session_day_payload(
        session_id,
        target,
        character_id=character_id,
        user_display_name=user_display_name,
        trust_points=trust_points,
    )
    logger.info(
        "[shenzhou-sync] pushing user day session=%s date=%s messages=%d",
        session_id,
        target.isoformat(),
        len(payload.get("messages") or []),
    )
    return sync_user_day(payload)


def cache_life_context(ctx: dict[str, Any], day: date | None = None) -> Path:
    settings = get_settings()
    cache_dir = settings.shenzhou_cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)
    d = day or date.today()
    path = cache_dir / f"life_context_{d.isoformat()}.json"
    import json

    path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
