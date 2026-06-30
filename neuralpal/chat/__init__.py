# -*- coding: utf-8 -*-
"""聊天输出后处理（伴侣可见回复）。"""

from neuralpal.chat.response_signature import (
    SYSTEM_DEFAULT_ENDING_SIGNATURE,
    append_companion_signature,
    finalize_companion_user_reply,
    resolve_ending_signature,
    should_append_companion_signature,
)

__all__ = [
    "SYSTEM_DEFAULT_ENDING_SIGNATURE",
    "append_companion_signature",
    "finalize_companion_user_reply",
    "resolve_ending_signature",
    "should_append_companion_signature",
]
