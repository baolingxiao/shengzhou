# -*- coding: utf-8 -*-
"""用户可见回复：强制纯文本，剥离 Markdown。"""

from __future__ import annotations

import re

PLAIN_TEXT_OUTPUT_RULE = """
---
### 【输出格式 · 强制】
- 展示给用户的正文必须是**纯文本**：禁止 Markdown 语法。
- 禁止出现：**、*、#、```、[]()、- 列表语法 等。
- 需要分点时用「1. 2. 3.」或「·」开头，换行分隔即可。
- 语气词、颜文字签名不受此限。
""".strip()

_MD_CODE_BLOCK = re.compile(r"```[\w-]*\n?(.*?)```", re.DOTALL)
_MD_HEADER = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_MD_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_MD_BOLD2 = re.compile(r"__([^_]+)__")
_MD_ITALIC = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_MD_ITALIC2 = re.compile(r"(?<!_)_([^_]+)_(?!_)")
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MD_INLINE_CODE = re.compile(r"`([^`]+)`")
_MD_BULLET = re.compile(r"^[\-*]\s+", re.MULTILINE)
_MD_HR = re.compile(r"^---+\s*$", re.MULTILINE)


def to_user_plain_text(text: str) -> str:
    """将模型输出转为用户可见纯文本（保留换行与编号）。"""
    s = (text or "").strip()
    if not s:
        return s

    s = _MD_CODE_BLOCK.sub(r"\1", s)
    s = _MD_HEADER.sub("", s)
    s = _MD_BOLD.sub(r"\1", s)
    s = _MD_BOLD2.sub(r"\1", s)
    s = _MD_ITALIC.sub(r"\1", s)
    s = _MD_ITALIC2.sub(r"\1", s)
    s = _MD_LINK.sub(r"\1", s)
    s = _MD_INLINE_CODE.sub(r"\1", s)
    s = _MD_BULLET.sub("· ", s)
    s = _MD_HR.sub("", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def finalize_user_visible_text(text: str) -> str:
    """所有面向用户的最终回复统一过一遍。"""
    return to_user_plain_text(text)
