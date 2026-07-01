# -*- coding: utf-8 -*-
"""分层记忆管线：每 7 天短期→中期，每月底中期→长期。"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from neuralpal.config import get_settings
from neuralpal.memory.memory_ids import ensure_memory_id
from neuralpal.memory.memory_summarize import summarize_with_doubao
from neuralpal.memory.palace_browser import MemoryTier, _split_frontmatter
from neuralpal.memory.palace_layout import publish_palace_file

if TYPE_CHECKING:
    from neuralpal.memory.memory_maintenance import MemoryMaintenanceService, MaintenanceResult

logger = logging.getLogger(__name__)

_WEEKLY_SECTIONS = [
    "本周标记为重要的记忆要点",
    "本周主要对话主题",
    "用户明确需求与偏好",
    "项目进展与结论",
    "待跟进事项",
]

_MONTHLY_SECTIONS = [
    "本月标记为重要的长期事实",
    "稳定偏好与习惯",
    "项目与目标进展",
    "需持续记住的实体与关系",
    "不建议长期保留的临时内容",
]


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def _iter_short_files_for_week(svc: MemoryMaintenanceService, week_key: str) -> list[Path]:
    out: list[Path] = []
    if not svc._short_dir.is_dir():
        return out
    for p in svc._short_dir.glob("*.md"):
        if not p.is_file() or p.name.startswith("."):
            continue
        try:
            mdt = datetime.fromtimestamp(p.stat().st_mtime).date()
        except OSError:
            continue
        iso = mdt.isocalendar()
        k = f"{iso.year}-W{iso.week:02d}"
        if k == week_key:
            out.append(p)
    return sorted(out)


def _iter_medium_files_for_month(svc: MemoryMaintenanceService, month_key: str) -> list[Path]:
    if not svc._middle_dir.is_dir():
        return []
    out: list[Path] = []
    for p in svc._middle_dir.glob("*.md"):
        if not p.is_file() or p.name.startswith("."):
            continue
        try:
            mdt = datetime.fromtimestamp(p.stat().st_mtime).date()
        except OSError:
            continue
        if mdt.strftime("%Y-%m") == month_key:
            out.append(p)
    return sorted(out)


def _source_from_file(svc: MemoryMaintenanceService, fp: Path, tier: MemoryTier) -> dict[str, Any]:
    text = fp.read_text(encoding="utf-8", errors="replace")
    meta, body = _split_frontmatter(text)
    from neuralpal.memory.memory_ids import memory_id_from_meta
    from neuralpal.memory.palace_browser import _is_marked, resolve_display_title

    mid = memory_id_from_meta(meta)
    if not mid:
        mid = ensure_memory_id(svc._root, fp, tier)
    title, _, _ = resolve_display_title(path=fp, meta=meta, body=body)
    rel = str(fp.relative_to(svc._root)).replace("\\", "/")
    return {
        "memory_id": mid,
        "rel_path": rel,
        "title": title,
        "marked": _is_marked(meta, text),
        "body": body,
    }


def rollup_short_to_medium(
    svc: MemoryMaintenanceService,
    week_key: str,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> MaintenanceResult:
    from neuralpal.memory.memory_maintenance import MaintenanceResult

    state = svc._load_state()
    rolled = state.setdefault("short_weekly_rolled", [])
    if week_key in rolled and not force:
        return MaintenanceResult(True, "skipped_exists")

    files = _iter_short_files_for_week(svc, week_key)
    if not files:
        return MaintenanceResult(True, "skipped_no_short_files")

    sources = [_source_from_file(svc, p, MemoryTier.SHORT) for p in files]
    body = summarize_with_doubao(
        kind="每周中期记忆总结",
        period_label=week_key,
        sources=sources,
        template_sections=_WEEKLY_SECTIONS,
    )

    out = svc._middle_dir / f"weekly_rollup_{week_key}.md"
    if not dry_run:
        _atomic_write(out, body)
        publish_palace_file(out)
        ensure_memory_id(svc._root, out, MemoryTier.MEDIUM)
        archive_dir = svc._short_dir / "_archive" / "weekly" / week_key
        archive_dir.mkdir(parents=True, exist_ok=True)
        for p in files:
            dst = archive_dir / p.name
            if dst.exists():
                dst = archive_dir / f"{p.stem}_{int(time.time())}{p.suffix}"
            p.replace(dst)
            publish_palace_file(dst)
        rolled.append(week_key)
        state["last_short_to_medium_week"] = week_key
        svc._save_state(state, dry_run=False)

    logger.info("[tiered] short→medium week=%s files=%d dry_run=%s", week_key, len(files), dry_run)
    return MaintenanceResult(True, "generated", out, f"sources={len(files)}")


def rollup_medium_to_long(
    svc: MemoryMaintenanceService,
    month_key: str,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> MaintenanceResult:
    from neuralpal.memory.memory_maintenance import MaintenanceResult

    state = svc._load_state()
    rolled = state.setdefault("medium_monthly_rolled", [])
    if month_key in rolled and not force:
        return MaintenanceResult(True, "skipped_exists")

    files = _iter_medium_files_for_month(svc, month_key)
    if not files:
        return MaintenanceResult(True, "skipped_no_medium_files")

    sources = [_source_from_file(svc, p, MemoryTier.MEDIUM) for p in files]
    body = summarize_with_doubao(
        kind="月度长期记忆总结",
        period_label=month_key,
        sources=sources,
        template_sections=_MONTHLY_SECTIONS,
    )

    out = svc._long_dir / f"monthly_rollup_{month_key}.md"
    if not dry_run:
        _atomic_write(out, body)
        publish_palace_file(out)
        ensure_memory_id(svc._root, out, MemoryTier.LONG)
        svc._index_monthly_to_chroma(month_key=month_key, text=body, file_path=out, dry_run=False)
        archive_dir = svc._middle_dir / "_archive" / "monthly" / month_key
        archive_dir.mkdir(parents=True, exist_ok=True)
        for p in files:
            dst = archive_dir / p.name
            if dst.exists():
                dst = archive_dir / f"{p.stem}_{int(time.time())}{p.suffix}"
            p.replace(dst)
            publish_palace_file(dst)
        rolled.append(month_key)
        state["last_medium_to_long_month"] = month_key
        svc._save_state(state, dry_run=False)

    logger.info("[tiered] medium→long month=%s files=%d dry_run=%s", month_key, len(files), dry_run)
    return MaintenanceResult(True, "generated", out, f"sources={len(files)}")


def run_tiered_weekly(svc: MemoryMaintenanceService, *, now: datetime | None = None, dry_run: bool = False) -> dict[str, Any]:
    n = now or datetime.now()
    target = n.date() - timedelta(days=7)
    iso = target.isocalendar()
    wk = f"{iso.year}-W{iso.week:02d}"
    gen = rollup_short_to_medium(svc, wk, dry_run=dry_run)
    return {"week": wk, "rollup": gen.status}


def run_tiered_monthly(svc: MemoryMaintenanceService, *, now: datetime | None = None, dry_run: bool = False) -> dict[str, Any]:
    n = now or datetime.now()
    first_this_month = date(n.year, n.month, 1)
    prev_month_last_day = first_this_month - timedelta(days=1)
    mk = prev_month_last_day.strftime("%Y-%m")
    # 仅在新月前几天执行（自然月切换后）
    if n.day > 3 and not dry_run:
        state = svc._load_state()
        if mk in state.get("medium_monthly_rolled", []):
            return {"month": mk, "rollup": "skipped_exists"}
    gen = rollup_medium_to_long(svc, mk, dry_run=dry_run)
    return {"month": mk, "rollup": gen.status}
