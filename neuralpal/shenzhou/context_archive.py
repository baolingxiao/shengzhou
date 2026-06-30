# -*- coding: utf-8 -*-
"""沈昼 life context 分层归档：日原始 + 周/月/年压缩摘要。"""

from __future__ import annotations

import gzip
import json
import logging
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from neuralpal.config import get_settings

logger = logging.getLogger(__name__)

_STATE_NAME = ".life_context_archive_state.json"


def _tz() -> ZoneInfo:
    return ZoneInfo(get_settings().shenzhou_timezone)


def _cache_dir() -> Path:
    p = get_settings().shenzhou_cache_dir
    p.mkdir(parents=True, exist_ok=True)
    return p


def _archive_root() -> Path:
    p = _cache_dir() / "archive"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _state_path() -> Path:
    return _cache_dir() / _STATE_NAME


def _default_state() -> dict[str, Any]:
    return {
        "compressed_raw_days": [],
        "weekly_generated": [],
        "monthly_generated": [],
        "yearly_generated": [],
        "last_run_at": "",
    }


def _load_state() -> dict[str, Any]:
    p = _state_path()
    if not p.is_file():
        return _default_state()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _default_state()
        out = _default_state()
        out.update(data)
        return out
    except Exception:
        return _default_state()


def _save_state(state: dict[str, Any]) -> None:
    p = _state_path()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def _daily_raw_path(day: date) -> Path:
    return _cache_dir() / f"life_context_{day.isoformat()}.json"


def _daily_gzip_path(day: date) -> Path:
    root = _archive_root() / "raw" / f"{day.year:04d}"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"life_context_{day.isoformat()}.json.gz"


def _all_days() -> set[date]:
    out: set[date] = set()
    for p in _cache_dir().glob("life_context_*.json"):
        if not p.is_file():
            continue
        s = p.stem.replace("life_context_", "", 1)
        try:
            out.add(date.fromisoformat(s))
        except ValueError:
            continue
    for p in (_archive_root() / "raw").glob("**/life_context_*.json.gz"):
        if not p.is_file():
            continue
        name = p.name.replace("life_context_", "", 1).replace(".json.gz", "")
        try:
            out.add(date.fromisoformat(name))
        except ValueError:
            continue
    return out


def _load_day_context(day: date) -> dict[str, Any] | None:
    raw = _daily_raw_path(day)
    if raw.is_file():
        try:
            return json.loads(raw.read_text(encoding="utf-8"))
        except Exception:
            logger.debug("invalid raw life context %s", raw, exc_info=True)
    gz = _daily_gzip_path(day)
    if gz.is_file():
        try:
            with gzip.open(gz, "rt", encoding="utf-8", errors="replace") as f:
                return json.load(f)
        except Exception:
            logger.debug("invalid gzip life context %s", gz, exc_info=True)
    return None


def _extract_titles(items: Any, *, key: str = "title", fallback: str = "summary", limit: int = 12) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    if not isinstance(items, list):
        return out
    for x in items:
        if not isinstance(x, dict):
            continue
        text = str(x.get(key) or x.get(fallback) or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text[:120])
        if len(out) >= limit:
            break
    return out


def _period_summary(days: list[date], *, label: str) -> str:
    contexts = [c for c in (_load_day_context(d) for d in days) if isinstance(c, dict)]
    if not contexts:
        return ""
    key_events: list[str] = []
    key_threads: list[str] = []
    mentionables: list[str] = []
    categories: Counter[str] = Counter()
    for ctx in contexts:
        life_events = ctx.get("lifeEvents") or []
        key_events.extend(_extract_titles(life_events))
        for e in life_events:
            if isinstance(e, dict):
                cat = str(e.get("category") or e.get("eventCategory") or "").strip()
                if cat:
                    categories[cat] += 1
        key_threads.extend(_extract_titles(ctx.get("activeThreads"), fallback="nextStep"))
        view = ctx.get("shenzhouView") or {}
        if isinstance(view, dict):
            mentionables.extend(_extract_titles(view.get("mentionableEvents"), fallback="description"))

    def unique(seq: list[str], n: int) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for x in seq:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
            if len(out) >= n:
                break
        return out

    event_lines = unique(key_events, 15)
    thread_lines = unique(key_threads, 12)
    mention_lines = unique(mentionables, 12)
    top_categories = [f"{k}({v})" for k, v in categories.most_common(8)]

    return (
        f"# {label}\n\n"
        f"## 覆盖天数\n- {len(days)} 天\n\n"
        "## 关键生活事件\n"
        + ("\n".join(f"- {x}" for x in (event_lines or ["-"])) if event_lines else "- -")
        + "\n\n## 进行中事务线\n"
        + ("\n".join(f"- {x}" for x in (thread_lines or ["-"])) if thread_lines else "- -")
        + "\n\n## 可主动提起候选\n"
        + ("\n".join(f"- {x}" for x in (mention_lines or ["-"])) if mention_lines else "- -")
        + "\n\n## 分类统计\n"
        + ("\n".join(f"- {x}" for x in (top_categories or ["-"])) if top_categories else "- -")
        + "\n"
    )


def _weekly_path(week_key: str) -> Path:
    p = _archive_root() / "weekly"
    p.mkdir(parents=True, exist_ok=True)
    return p / f"weekly_context_{week_key}.md"


def _monthly_path(month_key: str) -> Path:
    p = _archive_root() / "monthly"
    p.mkdir(parents=True, exist_ok=True)
    return p / f"monthly_context_{month_key}.md"


def _yearly_path(year_key: str) -> Path:
    p = _archive_root() / "yearly"
    p.mkdir(parents=True, exist_ok=True)
    return p / f"yearly_context_{year_key}.md"


def _write_text(path: Path, text: str, *, dry_run: bool) -> None:
    if dry_run:
        return
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _compress_old_daily(today: date, *, dry_run: bool) -> dict[str, int]:
    keep_days = int(get_settings().shenzhou_context_keep_raw_days)
    cutoff = today - timedelta(days=keep_days)
    compressed = 0
    removed = 0
    for p in _cache_dir().glob("life_context_*.json"):
        if not p.is_file():
            continue
        s = p.stem.replace("life_context_", "", 1)
        try:
            day = date.fromisoformat(s)
        except ValueError:
            continue
        if day >= cutoff:
            continue
        gz = _daily_gzip_path(day)
        if not gz.is_file():
            if not dry_run:
                raw = p.read_bytes()
                with gzip.open(gz, "wb") as f:
                    f.write(raw)
            compressed += 1
        if not dry_run:
            p.unlink(missing_ok=True)
        removed += 1
    return {"compressed": compressed, "removed_raw": removed}


def _week_key(d: date) -> str:
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _month_key(d: date) -> str:
    return d.strftime("%Y-%m")


def _year_key(d: date) -> str:
    return d.strftime("%Y")


def _closed_targets(today: date) -> tuple[str, str, str]:
    prev_week_day = today - timedelta(days=7)
    prev_month_last = date(today.year, today.month, 1) - timedelta(days=1)
    prev_year_last = date(today.year - 1, 12, 31)
    return _week_key(prev_week_day), _month_key(prev_month_last), _year_key(prev_year_last)


def _days_for_week(week_key: str, all_days: set[date]) -> list[date]:
    return sorted(d for d in all_days if _week_key(d) == week_key)


def _days_for_month(month_key: str, all_days: set[date]) -> list[date]:
    return sorted(d for d in all_days if _month_key(d) == month_key)


def _days_for_year(year_key: str, all_days: set[date]) -> list[date]:
    return sorted(d for d in all_days if _year_key(d) == year_key)


def run_context_archive(
    *,
    now: datetime | None = None,
    dry_run: bool = False,
    backfill: bool = False,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.shenzhou_context_archive_enabled:
        return {"ok": False, "status": "disabled"}
    tz = _tz()
    now_local = (now or datetime.now(tz)).astimezone(tz)
    today = now_local.date()
    state = _load_state()
    stats: dict[str, Any] = {"ok": True, "compressed": {}, "generated": {"weekly": 0, "monthly": 0, "yearly": 0}}
    stats["compressed"] = _compress_old_daily(today, dry_run=dry_run)

    days = _all_days()
    if not days:
        state["last_run_at"] = now_local.isoformat()
        if not dry_run:
            _save_state(state)
        stats["status"] = "no_context_files"
        return stats

    weekly_done: set[str] = set(state.get("weekly_generated") or [])
    monthly_done: set[str] = set(state.get("monthly_generated") or [])
    yearly_done: set[str] = set(state.get("yearly_generated") or [])

    if backfill:
        week_targets = sorted({_week_key(d) for d in days})
        month_targets = sorted({_month_key(d) for d in days})
        year_targets = sorted({_year_key(d) for d in days})
    else:
        wk, mk, yk = _closed_targets(today)
        week_targets = [wk]
        month_targets = [mk]
        year_targets = [yk]

    for wk in week_targets:
        if wk in weekly_done:
            continue
        wdays = _days_for_week(wk, days)
        body = _period_summary(wdays, label=f"每周生活上下文压缩 {wk}")
        if not body:
            continue
        _write_text(_weekly_path(wk), body, dry_run=dry_run)
        weekly_done.add(wk)
        stats["generated"]["weekly"] += 1

    for mk in month_targets:
        if mk in monthly_done:
            continue
        mdays = _days_for_month(mk, days)
        body = _period_summary(mdays, label=f"月度生活上下文压缩 {mk}")
        if not body:
            continue
        _write_text(_monthly_path(mk), body, dry_run=dry_run)
        monthly_done.add(mk)
        stats["generated"]["monthly"] += 1

    for yk in year_targets:
        if yk in yearly_done:
            continue
        ydays = _days_for_year(yk, days)
        body = _period_summary(ydays, label=f"年度生活上下文压缩 {yk}")
        if not body:
            continue
        _write_text(_yearly_path(yk), body, dry_run=dry_run)
        yearly_done.add(yk)
        stats["generated"]["yearly"] += 1

    state["weekly_generated"] = sorted(weekly_done)
    state["monthly_generated"] = sorted(monthly_done)
    state["yearly_generated"] = sorted(yearly_done)
    compressed_days: list[str] = []
    for p in (_archive_root() / "raw").glob("**/life_context_*.json.gz"):
        name = p.name.replace("life_context_", "", 1).replace(".json.gz", "")
        try:
            date.fromisoformat(name)
        except ValueError:
            continue
        compressed_days.append(name)
    state["compressed_raw_days"] = sorted(set(compressed_days))
    state["last_run_at"] = now_local.isoformat()
    if not dry_run:
        _save_state(state)
    stats["status"] = "ok"
    return stats
