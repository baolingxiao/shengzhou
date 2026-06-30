# -*- coding: utf-8 -*-
"""晚间同步事件摘要：新增/结束事件 + 聊天中的事件进展信号。"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from neuralpal.config import get_settings

logger = logging.getLogger(__name__)

_DONE_WORDS = ("已完成", "完成了", "搞定", "结束了", "done", "closed", "完成")
_NEW_WORDS = ("新增", "新建", "刚加了", "开始做", "立项", "新任务", "new task")


def _cache_dir() -> Path:
    p = get_settings().shenzhou_cache_dir
    p.mkdir(parents=True, exist_ok=True)
    return p


def _ctx_path(day: date) -> Path:
    return _cache_dir() / f"life_context_{day.isoformat()}.json"


def _load_ctx(day: date) -> dict[str, Any]:
    p = _ctx_path(day)
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        logger.debug("load life context failed: %s", p, exc_info=True)
        return {}


def _event_items(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def add(items: Any) -> None:
        if not isinstance(items, list):
            return
        for x in items:
            if isinstance(x, dict):
                out.append(x)

    add(ctx.get("lifeEvents"))
    add(ctx.get("activeThreads"))
    view = ctx.get("shenzhouView") or {}
    if isinstance(view, dict):
        add(view.get("lifeEvents"))
        add(view.get("activeThreads"))
        add(view.get("mentionableEvents"))
    return out


def _event_key(e: dict[str, Any]) -> str:
    raw = str(e.get("id") or "").strip()
    if raw:
        return raw
    title = str(e.get("title") or "").strip()
    summary = str(e.get("summary") or e.get("description") or "").strip()
    return f"{title}|{summary}"[:180]


def _event_title(e: dict[str, Any]) -> str:
    return str(e.get("title") or e.get("summary") or e.get("description") or "未命名事件").strip()[:120]


def _chat_signals(messages: list[dict[str, str]]) -> dict[str, list[str]]:
    done: list[str] = []
    new: list[str] = []
    for m in messages:
        if str(m.get("role") or "") != "user":
            continue
        text = str(m.get("content") or "").strip()
        if not text:
            continue
        low = text.lower()
        if any(w in text for w in _DONE_WORDS) or any(w in low for w in ("done", "closed")):
            done.append(text[:120])
        if any(w in text for w in _NEW_WORDS) or "new task" in low:
            new.append(text[:120])
    return {"done": done[:8], "new": new[:8]}


def build_event_sync_digest(
    day: date,
    *,
    messages: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    today = _load_ctx(day)
    yesterday = _load_ctx(day - timedelta(days=1))

    today_items = _event_items(today)
    y_items = _event_items(yesterday)
    today_map = {_event_key(e): e for e in today_items}
    y_map = {_event_key(e): e for e in y_items}

    new_keys = [k for k in today_map.keys() if k not in y_map]
    resolved_keys = [k for k in y_map.keys() if k not in today_map]

    new_titles = [_event_title(today_map[k]) for k in new_keys][:12]
    resolved_titles = [_event_title(y_map[k]) for k in resolved_keys][:12]

    sig = _chat_signals(messages or [])
    lines: list[str] = [
        "【事件同步摘要】",
        f"- 今日事件总数：{len(today_map)}",
        f"- 新增事件：{len(new_titles)}",
        f"- 已结束事件：{len(resolved_titles)}",
    ]
    if new_titles:
        lines.append("- 新增详情：" + "；".join(new_titles[:6]))
    if resolved_titles:
        lines.append("- 结束详情：" + "；".join(resolved_titles[:6]))
    if sig["done"]:
        lines.append("- 聊天完成信号：" + "；".join(sig["done"][:4]))
    if sig["new"]:
        lines.append("- 聊天新任务信号：" + "；".join(sig["new"][:4]))

    return {
        "date": day.isoformat(),
        "today_event_count": len(today_map),
        "new_event_count": len(new_titles),
        "resolved_event_count": len(resolved_titles),
        "new_events": new_titles,
        "resolved_events": resolved_titles,
        "chat_done_signals": sig["done"],
        "chat_new_signals": sig["new"],
        "summary_text": "\n".join(lines),
    }


def save_event_sync_digest(digest: dict[str, Any]) -> Path:
    day = str(digest.get("date") or date.today().isoformat())
    p = _cache_dir() / f"event_sync_{day}.json"
    p.write_text(json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")
    return p
