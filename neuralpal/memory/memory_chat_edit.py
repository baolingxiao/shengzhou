# -*- coding: utf-8 -*-
"""短期记忆文件中的单条 / 批量对话消息编辑。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from neuralpal.memory.palace_layout import sync_short_term_snapshot
from neuralpal.memory.palace_browser import (
    _split_frontmatter,
    delete_palace_memory,
)

_CHAT_BLOCK_RE = re.compile(
    r"^###\s*(用户|助手)\s*\r?\n([\s\S]*?)(?=^###\s*(?:用户|助手)\s*\r?\n|$)",
    re.MULTILINE,
)
_SESSION_ID_RE = re.compile(r"会话[：:]\s*[`'\"]?([^`\"'\n]+)")


def parse_memory_chat_messages(body: str) -> list[dict[str, str]]:
    """解析正文中的用户/助手消息块。"""
    stripped = body.replace("\r\n", "\n")
    if stripped.startswith("---"):
        _, stripped = _split_frontmatter(stripped)
    stripped = stripped.strip()

    out: list[dict[str, str]] = []
    for match in _CHAT_BLOCK_RE.finditer(stripped):
        role = "user" if match.group(1) == "用户" else "assistant"
        content = match.group(2).strip()
        if content:
            out.append({"role": role, "content": content})

    if out:
        return out

    for line in stripped.splitlines():
        s = line.strip()
        if s.startswith("用户：") or s.startswith("用户:"):
            out.append({"role": "user", "content": s.split("：", 1)[-1].split(":", 1)[-1].strip()})
        elif s.startswith("助手：") or s.startswith("助手:"):
            out.append({"role": "assistant", "content": s.split("：", 1)[-1].split(":", 1)[-1].strip()})
    return out


def _session_id_from_body(body: str, fallback: str) -> str:
    m = _SESSION_ID_RE.search(body)
    if m:
        return m.group(1).strip()
    return fallback


def _to_langchain_messages(messages: list[dict[str, str]]) -> list[BaseMessage]:
    lc: list[BaseMessage] = []
    for m in messages:
        if m.get("role") == "user":
            lc.append(HumanMessage(content=m["content"]))
        else:
            lc.append(AIMessage(content=m["content"]))
    return lc


def delete_messages_at_indices(
    *,
    palace_root: Path,
    rel_path: str,
    indices: list[int],
) -> dict[str, Any]:
    """
    从短期记忆文件中删除指定下标的消息（0-based）。
    若删空则删除整个文件。
    """
    fp = (palace_root / rel_path).resolve()
    root = palace_root.resolve()
    if not fp.is_file() or not str(fp).startswith(str(root)):
        raise FileNotFoundError(rel_path)

    raw = fp.read_text(encoding="utf-8")
    meta, body = _split_frontmatter(raw)
    messages = parse_memory_chat_messages(body)
    if not messages:
        raise ValueError("该文件不含可删除的对话消息")

    to_remove = sorted({int(i) for i in indices if 0 <= int(i) < len(messages)}, reverse=True)
    if not to_remove:
        raise ValueError("无效的消息下标")

    for idx in to_remove:
        messages.pop(idx)

    session_slug = fp.stem
    session_id = _session_id_from_body(body, session_slug)

    if not messages:
        delete_palace_memory(fp)
        return {
            "deleted_count": len(to_remove),
            "remaining": 0,
            "file_removed": True,
            "rel_path": rel_path,
            "session_id": session_id,
        }

    rolled: list[str] = []
    rolled_marker = "## 已滚出窗口的摘要"
    if rolled_marker in body:
        tail = body.split(rolled_marker, 1)[-1]
        for line in tail.splitlines():
            s = line.strip()
            if s.startswith("- "):
                rolled.append(s[2:].strip())

    sync_short_term_snapshot(
        session_id=session_id,
        messages=_to_langchain_messages(messages),
        rolled_summaries=rolled or None,
        palace_root=palace_root,
    )

    if meta:
        new_fp = (palace_root / rel_path).resolve()
        if new_fp.is_file():
            new_body = new_fp.read_text(encoding="utf-8")
            if not new_body.startswith("---"):
                fm_lines = ["---", *[f"{k}: {v}" for k, v in meta.items()], "---", ""]
                new_fp.write_text("\n".join(fm_lines) + new_body.lstrip("\n"), encoding="utf-8")

    return {
        "deleted_count": len(to_remove),
        "remaining": len(messages),
        "file_removed": False,
        "rel_path": rel_path,
        "session_id": session_id,
    }
