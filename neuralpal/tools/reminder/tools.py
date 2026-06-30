# -*- coding: utf-8 -*-
"""提醒工具占位（reminder 插件未完整迁移时避免 import 失败）。"""

from __future__ import annotations

from typing import Any, List


def build_reminder_langchain_tools(
    chat_id: int,
    user_id: int,
) -> List[Any]:
    return []
