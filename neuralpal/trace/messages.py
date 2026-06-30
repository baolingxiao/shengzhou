# -*- coding: utf-8 -*-
"""将 LangChain / 内部消息序列化为 Trace 可存储结构。"""

from __future__ import annotations

from typing import Any, Iterable


def message_role(msg: Any) -> str:
    t = type(msg).__name__.lower()
    if "human" in t:
        return "user"
    if "ai" in t or "assistant" in t:
        return "assistant"
    if "system" in t:
        return "system"
    return getattr(msg, "type", t)


def message_content(msg: Any) -> str:
    raw = getattr(msg, "content", "")
    if isinstance(raw, list):
        parts: list[str] = []
        for x in raw:
            if isinstance(x, dict):
                parts.append(str(x.get("text", x)))
            else:
                parts.append(str(x))
        return "".join(parts)
    return str(raw) if raw is not None else ""


def serialize_lc_messages(messages: Iterable[Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for msg in messages:
        out.append({"role": message_role(msg), "content": message_content(msg)})
    return out


def short_term_from_messages(messages: Iterable[Any]) -> list[dict[str, str]]:
    """短期记忆注入：Human/AI 历史对。"""
    return serialize_lc_messages(messages)
