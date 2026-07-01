# -*- coding: utf-8 -*-
"""沈昼等角色的记忆宫殿后台服务。"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from neuralpal.characters.constants import DEFAULT_CHARACTER_NAME
from neuralpal.characters.store import get_character_store
from neuralpal.memory.character_palace import (
    ensure_character_palace,
    get_character_chroma_path,
    get_character_palace_root,
)
from neuralpal.memory.memory_maintenance import MemoryMaintenanceService
from neuralpal.memory.palace_browser import (
    MemoryEntry,
    MemoryTier,
    delete_palace_memory,
    list_memory_entries,
    read_memory_detail,
    set_palace_scope,
    toggle_memory_mark,
)


def resolve_character_name(character_id: str | None = None) -> str:
    if character_id:
        char = get_character_store().get_character(character_id.strip())
        if char and char.name.strip():
            return char.name.strip()
    return DEFAULT_CHARACTER_NAME


@contextmanager
def character_palace_scope(character_name: str) -> Iterator[Path]:
    root = ensure_character_palace(character_name)
    chroma = get_character_chroma_path(character_name)
    set_palace_scope(palace_root=root, chroma_path=chroma)
    try:
        yield root
    finally:
        set_palace_scope(palace_root=None, chroma_path=None)


def _entry_to_dict(entry: MemoryEntry, palace_root: Path) -> dict[str, Any]:
    from neuralpal.memory.memory_ids import ensure_memory_id, memory_id_from_meta
    from neuralpal.memory.palace_browser import _split_frontmatter

    text = entry.path.read_text(encoding="utf-8", errors="replace")
    meta, _ = _split_frontmatter(text)
    mid = memory_id_from_meta(meta) or ensure_memory_id(palace_root, entry.path, entry.tier)
    return {
        "id": entry.id,
        "memory_id": mid,
        "tier": entry.tier.value,
        "tier_label": entry.tier.label,
        "rel_path": entry.rel_path,
        "title": entry.display_title,
        "date_label": entry.date_label,
        "preview": entry.preview,
        "marked": entry.marked,
        "modified_at": entry.modified_at,
        "category": _category_from_rel(entry.rel_path),
    }


def _category_from_rel(rel_path: str) -> str:
    parts = rel_path.replace("\\", "/").split("/")
    if len(parts) >= 2 and parts[0] == "03_长期记忆":
        return parts[1] if len(parts) > 2 else "长期记忆"
    if parts[0] == "01_短期记忆":
        return "短期会话"
    if parts[0] == "02_中期记忆":
        return "中期摘要"
    return parts[0]


def list_memories(character_name: str, tier: str) -> list[dict[str, Any]]:
    try:
        mem_tier = MemoryTier(tier.strip().lower())
    except ValueError as exc:
        raise ValueError(f"无效 tier: {tier}") from exc
    with character_palace_scope(character_name) as root:
        from neuralpal.memory.memory_ids import backfill_memory_ids

        backfill_memory_ids(root)
        return [_entry_to_dict(e, root) for e in list_memory_entries(mem_tier)]


def get_memory_detail(character_name: str, rel_path: str) -> dict[str, Any]:
    root = ensure_character_palace(character_name)
    fp = (root / rel_path).resolve()
    if not fp.is_file() or not str(fp).startswith(str(root)):
        raise FileNotFoundError(rel_path)
    with character_palace_scope(character_name) as palace_root:
        from neuralpal.memory.memory_ids import ensure_memory_id, memory_id_from_meta
        from neuralpal.memory.palace_browser import _split_frontmatter

        title, body = read_memory_detail(fp)
        tier = MemoryTier.SHORT
        if rel_path.replace("\\", "/").startswith("02_"):
            tier = MemoryTier.MEDIUM
        elif rel_path.replace("\\", "/").startswith("03_"):
            tier = MemoryTier.LONG
        meta, _ = _split_frontmatter(fp.read_text(encoding="utf-8"))
        mid = memory_id_from_meta(meta) or ensure_memory_id(palace_root, fp, tier)
    return {
        "rel_path": rel_path,
        "memory_id": mid,
        "title": title,
        "body": body,
        "category": _category_from_rel(rel_path),
    }


def get_memory_by_id(character_name: str, memory_id: str) -> dict[str, Any]:
    root = ensure_character_palace(character_name)
    with character_palace_scope(character_name):
        from neuralpal.memory.memory_ids import resolve_memory_by_id

        row = resolve_memory_by_id(root, memory_id)
        if row is None:
            raise FileNotFoundError(memory_id)
        detail = get_memory_detail(character_name, row["rel_path"])
        return {**detail, **row}


def delete_memory(character_name: str, rel_path: str) -> None:
    root = ensure_character_palace(character_name)
    fp = (root / rel_path).resolve()
    if not str(fp).startswith(str(root)):
        raise PermissionError("路径越界")
    with character_palace_scope(character_name):
        delete_palace_memory(fp)


def mark_memory(character_name: str, rel_path: str) -> bool:
    root = ensure_character_palace(character_name)
    fp = (root / rel_path).resolve()
    if not str(fp).startswith(str(root)):
        raise PermissionError("路径越界")
    with character_palace_scope(character_name):
        return toggle_memory_mark(fp)


def _maintenance_service_for(character_name: str) -> MemoryMaintenanceService:
    from neuralpal.memory.memory_system import LongTermMemoryEngine

    root = ensure_character_palace(character_name)
    chroma = get_character_chroma_path(character_name)
    lt = LongTermMemoryEngine(verbose=False, palace_root=root, chroma_path=chroma)
    return MemoryMaintenanceService(root=root, long_term_engine=lt, verbose=False)


def run_maintenance(
    character_name: str,
    *,
    action: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    svc = _maintenance_service_for(character_name)
    now = datetime.now()
    action = action.strip().lower()
    if action == "daily":
        result = svc.run_daily_maintenance(now=now, dry_run=dry_run)
    elif action == "weekly":
        result = svc.run_weekly_maintenance(now=now, dry_run=dry_run)
    elif action == "monthly":
        result = svc.run_monthly_maintenance(now=now, dry_run=dry_run)
    elif action == "yearly":
        result = svc.run_yearly_maintenance(now=now, dry_run=dry_run)
    elif action == "catchup":
        result = svc.run_startup_catchup(now=now, dry_run=dry_run)
    else:
        raise ValueError(f"未知维护动作: {action}")
    return result


def summarize_tiers(character_name: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for tier in MemoryTier:
        counts[tier.value] = len(list_memories(character_name, tier.value))
    return counts


def delete_memory_messages(
    character_name: str,
    rel_path: str,
    indices: list[int],
) -> dict[str, Any]:
    """从短期记忆文件删除指定下标的消息。"""
    from neuralpal.memory.memory_chat_edit import delete_messages_at_indices

    root = ensure_character_palace(character_name)
    with character_palace_scope(character_name):
        return delete_messages_at_indices(
            palace_root=root,
            rel_path=rel_path,
            indices=indices,
        )


def optimize_memory_titles(character_name: str, *, limit: int = 24) -> int:
    """为待命名条目生成 AI 展示标题，返回更新条数。"""
    from neuralpal.memory.palace_browser import entries_needing_ai_titles
    from neuralpal.memory.palace_title_service import ensure_display_title

    updated = 0
    with character_palace_scope(character_name):
        all_entries: list[MemoryEntry] = []
        for tier in MemoryTier:
            all_entries.extend(list_memory_entries(tier))
        pending = entries_needing_ai_titles(all_entries, limit=limit)
        for entry in pending:
            try:
                ensure_display_title(entry.path, use_ai=True)
                updated += 1
            except Exception:
                continue
    return updated


def serialize_messages(messages: list[BaseMessage]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for msg in messages:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        out.append({"role": role, "content": content})
    return out


def bootstrap_character_memory_maintenance(character_id: str | None = None) -> None:
    """服务启动时补跑日/周/月维护并启动后台 scheduler（仅一次）。"""
    from neuralpal.config import get_settings
    from neuralpal.memory.character_palace import palace_paths_for_character_id

    settings = get_settings()
    if not getattr(settings, "memory_maintenance_enabled", True):
        return
    _, _, name = palace_paths_for_character_id(character_id)
    svc = _maintenance_service_for(name)
    dry = bool(getattr(settings, "memory_maintenance_dry_run", False))
    try:
        svc.run_startup_catchup(dry_run=dry)
    except Exception:
        import logging

        logging.getLogger(__name__).exception("memory maintenance startup catchup failed")
    try:
        svc.start_background_scheduler(
            interval_seconds=int(getattr(settings, "memory_maintenance_interval_seconds", 600)),
            dry_run=dry,
        )
    except Exception:
        import logging

        logging.getLogger(__name__).exception("memory maintenance scheduler start failed")


def list_memory_transparency(character_name: str, session_id: str, *, limit: int = 80) -> list[dict[str, Any]]:
    root = ensure_character_palace(character_name)
    with character_palace_scope(character_name):
        from neuralpal.memory.memory_transparency import list_transparency_records

        return list_transparency_records(root, session_id, limit=limit)


def default_maintenance_hint() -> str:
    return (
        "分层管线：对话仅存短期；每 7 天将短期（优先★标记）豆包总结入中期；"
        "每月初将上月中期总结入长期并写入向量库。"
    )
