# -*- coding: utf-8 -*-
"""记忆维护用豆包摘要（优先已标记内容）。"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from neuralpal.config import get_settings
from neuralpal.memory.memory_chat_edit import parse_memory_chat_messages

logger = logging.getLogger(__name__)


def _format_sources(sources: list[dict[str, Any]], *, max_chars: int = 12000) -> str:
    parts: list[str] = []
    used = 0
    for src in sources:
        mid = src.get("memory_id") or "?"
        marked = "【已标记重要】" if src.get("marked") else ""
        title = src.get("title") or src.get("rel_path") or ""
        body = str(src.get("body") or "")
        msgs = parse_memory_chat_messages(body)
        if msgs:
            dialog = "\n".join(
                f"{'用户' if m['role'] == 'user' else '助手'}：{m['content']}" for m in msgs
            )
        else:
            dialog = body
        chunk = f"### {mid} {marked} {title}\n{dialog.strip()}\n"
        if used + len(chunk) > max_chars:
            break
        parts.append(chunk)
        used += len(chunk)
    return "\n".join(parts).strip()


def summarize_with_doubao(
    *,
    kind: str,
    period_label: str,
    sources: list[dict[str, Any]],
    template_sections: list[str],
) -> str:
    """
    用豆包 Lite 生成结构化摘要。
    sources 中 marked=true 的条目会排在前面传入模型。
    """
    marked = [s for s in sources if s.get("marked")]
    normal = [s for s in sources if not s.get("marked")]
    ordered = marked + normal
    blob = _format_sources(ordered)
    if not blob.strip():
        return f"# {kind} {period_label}\n\n（本期无可用记忆内容）\n"

    settings = get_settings()
    if not (settings.doubao_api_key or "").strip():
        return _fallback_summary(kind, period_label, ordered, template_sections)

    from neuralpal.llm.llm_router import _make_lite_model

    sections_hint = "\n".join(f"- {s}" for s in template_sections)
    marked_note = (
        f"其中 {len(marked)} 条为用户标记为「重要」，请优先保留其事实与结论。"
        if marked
        else "无用户标记条目。"
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是沈昼记忆宫殿的归档助手。根据输入记忆原文生成中文 Markdown 摘要。\n"
                f"任务类型：{kind}，周期：{period_label}。\n"
                f"{marked_note}\n"
                "必须包含以下章节（每章用 ## 标题，条目用 - 列表）：\n"
                f"{sections_hint}\n"
                "不要编造未出现的信息；标记重要的内容要在对应章节中优先体现。",
            ),
            ("human", "{text}"),
        ]
    )
    try:
        llm = _make_lite_model(temperature=0.2, max_tokens=2048)
        body = (prompt | llm | StrOutputParser()).invoke({"text": blob[:14000]})
        text = str(body).strip()
        if not text.startswith("#"):
            text = f"# {kind} {period_label}\n\n{text}"
        return text + "\n"
    except Exception as exc:
        logger.warning("doubao memory summary failed: %s", exc)
        return _fallback_summary(kind, period_label, ordered, template_sections)


def _fallback_summary(
    kind: str,
    period_label: str,
    sources: list[dict[str, Any]],
    template_sections: list[str],
) -> str:
    lines = [f"# {kind} {period_label}", ""]
    for sec in template_sections:
        lines.append(f"## {sec}")
        added = 0
        for src in sources:
            if added >= 5:
                break
            msgs = parse_memory_chat_messages(str(src.get("body") or ""))
            for m in msgs[:2]:
                prefix = "★ " if src.get("marked") else ""
                role = "用户" if m["role"] == "user" else "助手"
                lines.append(f"- {prefix}{role}：{m['content'][:120]}")
                added += 1
        if added == 0:
            lines.append("- -")
        lines.append("")
    return "\n".join(lines)
