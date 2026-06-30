# -*- coding: utf-8 -*-
"""沈昼回复字数规范与分段（微信式连发）。"""

from __future__ import annotations

import re
from typing import Literal

from neuralpal.schedule.task_detect import is_task_request

ReplyProfile = Literal["companion", "work_task", "work_report"]

_REPLY_MARKER = "[[NEURALPAL_REPLY_LENGTH_V1]]"

_REPORT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"汇报",
        r"总结",
        r"汇总",
        r"整理成",
        r"列出来",
        r"写一份",
        r"报告",
        r"盘点",
    )
)

_SPLIT_PUNCT = re.compile(r"(?<=[，。；！？、：])")


def detect_reply_profile(user_text: str, *, work_mode: str = "companion") -> ReplyProfile:
    text = (user_text or "").strip()
    if text and any(p.search(text) for p in _REPORT_PATTERNS):
        return "work_report"
    if work_mode in ("work", "overtime") and is_task_request(text):
        return "work_task"
    return "companion"


def _limits_for_profile(profile: ReplyProfile) -> tuple[int, int, int]:
    if profile == "work_task":
        return 20, 35, 300
    if profile == "work_report":
        return 20, 35, 300
    return 8, 28, 84


def build_reply_length_addon(
    user_text: str,
    *,
    work_mode: str = "companion",
) -> str:
    profile = detect_reply_profile(user_text, work_mode=work_mode)
    lo, hi, total_max = _limits_for_profile(profile)

    if profile == "work_report":
        body = f"""{_REPLY_MARKER}
### 【回复字数 · 硬性规范 · 工作汇报】
- 本轮为**工作汇报/汇总**：全文控制在 **200–300 字**以内（不得超过 {total_max} 字）。
- 仍须**分段连发**：每段单独一行，每段 **{lo}–{hi} 字**；像微信连发多条，不要一大段。
- 段与段之间**只用一个换行**分隔；禁止 Markdown、禁止项目符号标题。
- 信息密度高、可执行；语气保持沈昼公事公办。"""
    elif profile == "work_task":
        body = f"""{_REPLY_MARKER}
### 【回复字数 · 硬性规范 · 工作时间执行任务】
- 当前为**上班/加班执行任务**：每条（每行）**{lo}–{hi} 字**。
- **每次回复 2–6 行**；每行一段，段间单个换行；像连发微信，不要写成长文。
- 禁止 Markdown；需要分点用「1. 2.」或换行。
- 简洁、专业、可执行。"""
    else:
        body = f"""{_REPLY_MARKER}
### 【回复字数 · 硬性规范 · 陪伴闲聊】
- 每条（每行）**{lo}–{hi} 字**；每次回复 **2–5 行**为佳。
- 每行=一条消息，段间单个换行；像微信连发，不要大段说教。
- 禁止 Markdown；少用甜腻语气词，符合沈昼信任档位。"""

    return body.strip()


def _char_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def _split_long_chunk(chunk: str, max_len: int) -> list[str]:
    chunk = chunk.strip()
    if not chunk or _char_len(chunk) <= max_len:
        return [chunk] if chunk else []

    parts: list[str] = []
    buf = ""
    for piece in _SPLIT_PUNCT.split(chunk):
        piece = piece.strip()
        if not piece:
            continue
        candidate = f"{buf}{piece}" if buf else piece
        if _char_len(candidate) <= max_len:
            buf = candidate
        else:
            if buf:
                parts.append(buf)
            if _char_len(piece) > max_len:
                for i in range(0, len(piece), max_len):
                    parts.append(piece[i : i + max_len])
                buf = ""
            else:
                buf = piece
    if buf:
        parts.append(buf)
    return parts


def split_reply_into_segments(
    text: str,
    *,
    user_text: str = "",
    work_mode: str = "companion",
) -> list[str]:
    """
    将助手正文拆为多条气泡。优先按换行；过长段再按标点/字数切。
    返回至少一段（非空）。
    """
    raw = (text or "").strip()
    if not raw:
        return []

    profile = detect_reply_profile(user_text, work_mode=work_mode)
    lo, hi, total_max = _limits_for_profile(profile)

    lines = [ln.strip() for ln in re.split(r"\n+", raw) if ln.strip()]
    if not lines:
        lines = [raw]

    segments: list[str] = []
    for line in lines:
        if _char_len(line) > hi:
            segments.extend(_split_long_chunk(line, hi))
        else:
            segments.append(line)

  # 合并过短碎片（< lo 且可并）
    merged: list[str] = []
    for seg in segments:
        if merged and _char_len(seg) < lo and _char_len(merged[-1]) + _char_len(seg) <= hi:
            merged[-1] = merged[-1] + seg
        else:
            merged.append(seg)
    segments = merged or segments

    if profile == "work_report":
        total = 0
        clipped: list[str] = []
        for seg in segments:
            if total >= total_max:
                break
            remain = total_max - total
            if _char_len(seg) > remain:
                clipped.extend(_split_long_chunk(seg[: remain + 20], min(hi, remain)))
                total = total_max
                break
            clipped.append(seg)
            total += _char_len(seg)
        segments = clipped

    return [s for s in segments if s.strip()]


def prepare_assistant_reply(
    text: str,
    *,
    user_text: str = "",
    work_mode: str = "companion",
) -> tuple[str, list[str]]:
    """返回 (存入记忆的合并正文, 展示用分段列表)。"""
    segments = split_reply_into_segments(
        text, user_text=user_text, work_mode=work_mode
    )
    if not segments:
        return text.strip(), [text.strip()] if text.strip() else []
    joined = "\n".join(segments)
    return joined, segments


__all__ = [
    "build_reply_length_addon",
    "detect_reply_profile",
    "prepare_assistant_reply",
    "split_reply_into_segments",
]
