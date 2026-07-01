# -*- coding: utf-8 -*-
"""沈昼对话时按记忆编号检索上下文。"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MemoryIdSelection(BaseModel):
    """AI 选中的记忆编号。"""

    memory_ids: list[str] = Field(
        default_factory=list,
        description="0–5 个最相关的记忆编号，如 ST_0003、MT_0001；无关则空列表",
    )
    reasoning: str = Field(default="", description="简短说明为何选择这些编号")


def select_memory_ids_for_query(
    user_query: str,
    catalog: list[dict[str, Any]],
    *,
    max_ids: int = 5,
) -> MemoryIdSelection:
    """
    用轻量模型从记忆目录中挑选与本轮用户问题相关的 ST_/MT_/LT_ 编号。
    供 chat_turn 在生成回复前注入精确上下文。
    """
    query = (user_query or "").strip()
    if not query or not catalog:
        return MemoryIdSelection()

    from neuralpal.config import get_settings

    if not (get_settings().doubao_api_key or "").strip():
        return _keyword_fallback(query, catalog, max_ids=max_ids)

    from langchain_core.prompts import ChatPromptTemplate
    from neuralpal.llm.llm_router import _make_lite_model

    lines: list[str] = []
    for row in catalog[:80]:
        mid = row.get("memory_id") or "?"
        mark = "★" if row.get("marked") else ""
        lines.append(
            f"{mid}{mark} [{row.get('tier')}] {row.get('title') or ''} — {(row.get('preview') or '')[:100]}"
        )
    catalog_text = "\n".join(lines)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是沈昼的记忆检索器。根据用户问题，从记忆目录中选出最相关的编号。\n"
                "规则：\n"
                "1) 只返回目录中存在的编号；不要编造。\n"
                "2) 优先已标记★的重要记忆。\n"
                "3) 短期(ST)用于近期对话细节，中期(MT)用于周摘要，长期(LT)用于稳定事实。\n"
                f"4) 最多 {max_ids} 个；无关则返回空列表。",
            ),
            ("human", "用户问题：{q}\n\n记忆目录：\n{catalog}"),
        ]
    )
    try:
        structured = _make_lite_model(temperature=0.0, max_tokens=256).with_structured_output(
            MemoryIdSelection
        )
        result = (prompt | structured).invoke({"q": query[:2000], "catalog": catalog_text[:12000]})
        if isinstance(result, MemoryIdSelection):
            result.memory_ids = result.memory_ids[:max_ids]
            return result
        return MemoryIdSelection()
    except Exception as exc:
        logger.warning("memory id selection failed: %s", exc)
        return _keyword_fallback(query, catalog, max_ids=max_ids)


def _keyword_fallback(query: str, catalog: list[dict[str, Any]], *, max_ids: int) -> MemoryIdSelection:
    q = query.lower()
    scored: list[tuple[int, str]] = []
    for row in catalog:
        mid = str(row.get("memory_id") or "")
        blob = f"{row.get('title')} {row.get('preview')}".lower()
        score = sum(1 for token in q.split() if len(token) >= 2 and token in blob)
        if row.get("marked"):
            score += 2
        if score > 0 and mid:
            scored.append((score, mid))
    scored.sort(reverse=True)
    return MemoryIdSelection(memory_ids=[m for _, m in scored[:max_ids]])


def build_context_from_memory_ids(
    palace_root: Any,
    memory_ids: list[str],
    *,
    max_chars: int = 8000,
) -> str:
    """将选中编号对应的记忆正文拼成注入 system 的上下文块。"""
    from pathlib import Path

    from neuralpal.memory.memory_ids import resolve_memory_by_id

    root = Path(palace_root).resolve()
    parts: list[str] = []
    used = 0
    for mid in memory_ids:
        row = resolve_memory_by_id(root, mid)
        if not row:
            continue
        chunk = f"【{mid}】\n{row.get('body', '').strip()}\n"
        if used + len(chunk) > max_chars:
            break
        parts.append(chunk)
        used += len(chunk)
    if not parts:
        return ""
    return "【记忆宫殿·已选编号上下文】\n" + "\n---\n".join(parts)
