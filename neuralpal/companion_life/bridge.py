# -*- coding: utf-8 -*-
"""沈昼世界 ↔ 贾维斯 聊天上下文桥接。"""

from __future__ import annotations

import json
import logging
import re
from datetime import date
from pathlib import Path
from typing import Any

from neuralpal.config import get_settings
from neuralpal.shenzhou.client import fetch_life_context

logger = logging.getLogger(__name__)

LIFE_STATUS_PATTERNS = [
    re.compile(p)
    for p in (
        r"你在干嘛",
        r"在做什么",
        r"今天怎么样",
        r"最近忙什么",
        r"今天发生什么",
        r"过得怎么样",
        r"今天如何",
        r"今天怎么了",
        r"刚才去哪",
        r"有什么想分享",
        r"你现在忙吗",
    )
]


def is_shenzhou_integration_enabled() -> bool:
    s = get_settings()
    return bool(s.shenzhou_integration_enabled and s.shenzhou_world_api_url.strip())


def resolve_companion_instance_id_for_session(session_id: str) -> str | None:
    if not is_shenzhou_integration_enabled():
        return None
    slug = get_settings().shenzhou_user_entity_slug.strip()
    return slug or None


def _is_life_intent(user_message: str) -> bool:
    text = (user_message or "").strip()
    if not text:
        return False
    return any(p.search(text) for p in LIFE_STATUS_PATTERNS)


def _load_cached_context(day: date) -> dict[str, Any] | None:
    path = get_settings().shenzhou_cache_dir / f"life_context_{day.isoformat()}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _format_life_addon(ctx: dict[str, Any], *, companion_name: str) -> str:
    ds = ctx.get("dailyState") or {}
    life_events = ctx.get("lifeEvents") or []
    threads = ctx.get("activeThreads") or []
    shareable = ctx.get("shareableEvents") or []
    view = ctx.get("shenzhouView") or {}

    lines = [
        "---",
        f"【沈昼世界 · 今日生活上下文 · {ctx.get('date', '')}】",
        "以下来自世界引擎数据库，回答用户关于「今天/最近生活」的问题时必须以此为准，不可编造冲突细节。",
    ]
    if ds:
        lines.append(
            f"状态：{ds.get('location', '未知')} · {ds.get('currentActivity', '未知')} · "
            f"情绪{ds.get('moodScore', '?')}/100 · 压力{ds.get('stressScore', '?')}/100"
        )
        if ds.get("morningPlan"):
            lines.append(f"上午计划：{ds['morningPlan']}")
        if ds.get("eveningPlan"):
            lines.append(f"晚间计划：{ds['eveningPlan']}")

    if life_events:
        lines.append("今日生活事件：")
        for e in life_events[:8]:
            lines.append(f"- {e.get('title', '')}：{(e.get('description') or '')[:120]}")

    mentionable = view.get("mentionableEvents") or []
    if mentionable:
        lines.append("可主动提起：")
        for e in mentionable[:6]:
            lines.append(f"- {e.get('title', '')}")

    if shareable:
        lines.append("可分享给他人的：")
        for e in shareable[:4]:
            npc = e.get("npc")
            lines.append(f"- {e.get('title', '')}" + (f"（来自{npc}）" if npc else ""))

    if threads:
        lines.append("进行中的事务线：")
        for t in threads[:5]:
            lines.append(f"- {t.get('title', '')}：{(t.get('summary') or '')[:80]}")

    lines.append(f"（{companion_name} 仅分享沈昼视角可见的信息）")
    return "\n".join(lines)


def maybe_build_life_context_for_turn(
    *,
    user_id: str,
    companion_instance_id: str,
    companion_name: str,
    user_message: str,
    recent_messages: list[str] | None = None,
) -> tuple[str, str | None]:
    del user_id, recent_messages  # 预留扩展
    if not is_shenzhou_integration_enabled():
        return "", None

    settings = get_settings()
    proactive = settings.shenzhou_proactive_life_context
    if not _is_life_intent(user_message) and not proactive:
        return "", None

    today = date.today()
    ctx = _load_cached_context(today)
    if ctx is None:
        try:
            ctx = fetch_life_context(today)
        except Exception:
            logger.debug("shenzhou life context fetch failed", exc_info=True)
            return "", None

    addon = _format_life_addon(ctx, companion_name=companion_name)
    snippet_id = f"shenzhou_{ctx.get('date', today.isoformat())}"
    return addon, snippet_id


def on_life_snippet_used(snippet_id: str | None) -> None:
    del snippet_id
