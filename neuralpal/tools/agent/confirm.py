# -*- coding: utf-8 -*-
"""用户确认/取消语句解析。"""

from __future__ import annotations

import re
from enum import Enum


class ConfirmIntent(str, Enum):
    NONE = "none"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    MODIFY = "modify"


_CONFIRM_PATTERNS = (
    r"^(确认|确定|可以|行|好的|好|去吧|执行|开始|没问题|ok|yes|go)$",
    r"^(嗯，?确认|好，?确认|按你说的|就这样)$",
)

_CANCEL_PATTERNS = (
    r"^(算了|取消|别[了做]?|不要|停止|停下|不用了|等等|先别)$",
    r"^(不[用了要行]|先取消|撤销)$",
)

_MODIFY_PATTERNS = (
    r"改一下|修改|换成|不要.*要",
)


def parse_confirm_intent(text: str) -> ConfirmIntent:
    t = (text or "").strip()
    if not t:
        return ConfirmIntent.NONE
    compact = re.sub(r"\s+", "", t.lower())
    for pat in _CANCEL_PATTERNS:
        if re.search(pat, compact, re.IGNORECASE) or re.search(pat, t, re.IGNORECASE):
            return ConfirmIntent.CANCEL
    for pat in _MODIFY_PATTERNS:
        if re.search(pat, t, re.IGNORECASE):
            return ConfirmIntent.MODIFY
    for pat in _CONFIRM_PATTERNS:
        if re.search(pat, compact, re.IGNORECASE) or re.search(pat, t, re.IGNORECASE):
            return ConfirmIntent.CONFIRM
    if len(t) <= 8 and t in ("确认", "行", "好", "可以", "去吧", "执行"):
        return ConfirmIntent.CONFIRM
    return ConfirmIntent.NONE
