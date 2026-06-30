# -*- coding: utf-8 -*-
"""任务型请求检测（非工作时间拦截用）。"""

from __future__ import annotations

import re

# 明确闲聊 / 身份问询 — 不算任务
_CHAT_ONLY_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"^你是谁",
        r"自我介绍",
        r"介绍一下你",
        r"^在吗[？?]?$",
        r"^你好[！!]?$",
        r"^嗨[！!]?$",
        r"晚安|早安|午安",
        r"想你了|在干嘛|吃了吗",
        r"^谢谢",
        r"^哈哈",
        r"陪我聊",
        r"随便聊",
        r"无聊",
    )
)

# 任务 / 代办信号
_TASK_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"帮我",
        r"麻烦你",
        r"请你去",
        r"你去",
        r"调查",
        r"搜索|搜一下|查一下|查下|查查|检索",
        r"调研|比价|销量|价格|报价",
        r"打开|启动|运行|执行|操作",
        r"整理|归类|归档|备份|删除文件",
        r"下载|上传|发送|发消息|发微信|微信里",
        r"看看.*(?:桌面|文件夹|文件|网页|网站)",
        r"联网|上网查",
        r"写代码|修 bug|debug",
        r"控制电脑|操控电脑|代操",
        r"propose_action",
    )
)

# 用户同意加班
_OVERTIME_CONSENT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"加班",
        r"加个班",
        r"麻烦.*班",
        r"那就.*班",
        r"辛苦.*班",
        r"好的.*班",
        r"让你加班",
        r"准你加班",
        r"同意加班",
        r"行.*加班",
        r"可以.*加班",
        r"继续办",
        r"继续查",
        r"继续执行",
    )
)

# 用户拒绝加班 / 改聊别的
_OVERTIME_DECLINE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"不加班",
        r"不用加班",
        r"算了",
        r"那算了",
        r"先不",
        r"不用了",
        r"取消",
        r"别做了",
    )
)


def _normalize(text: str) -> str:
    return (text or "").strip()


def is_chat_only_message(text: str) -> bool:
    t = _normalize(text)
    if not t:
        return True
    return any(p.search(t) for p in _CHAT_ONLY_PATTERNS)


def is_task_request(text: str) -> bool:
    """用户是否在请求执行类任务（搜索 / 代操 / 调研等）。"""
    t = _normalize(text)
    if not t or len(t) < 3:
        return False
    if is_chat_only_message(t):
        return False
    return any(p.search(t) for p in _TASK_PATTERNS)


def is_overtime_consent(text: str) -> bool:
    t = _normalize(text)
    if not t:
        return False
    if any(p.search(t) for p in _OVERTIME_DECLINE_PATTERNS):
        return False
    return any(p.search(t) for p in _OVERTIME_CONSENT_PATTERNS)


def is_overtime_decline(text: str) -> bool:
    t = _normalize(text)
    if not t:
        return False
    return any(p.search(t) for p in _OVERTIME_DECLINE_PATTERNS)


__all__ = [
    "is_chat_only_message",
    "is_overtime_consent",
    "is_overtime_decline",
    "is_task_request",
]
