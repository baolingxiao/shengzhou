# -*- coding: utf-8 -*-
"""
④ 瞬时记忆层（工作缓存）

单轮对话内的临时键值缓存：用于编排器在当轮流程中暂存中间态（如用户原文、草稿等）。
对话轮次结束必须 clear，**不得**写入 Chroma、不得写入 knowledge_palace、不得进入 LangChain 窗口记忆。
"""

from __future__ import annotations

from typing import Any


class TransientBuffer:
    """④ 瞬时记忆容器：仅内存 dict，生命周期为「单轮 chat_turn」。"""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def pop(self, key: str, default: Any = None) -> Any:
        return self._data.pop(key, default)

    def clear(self) -> None:
        self._data.clear()

    def snapshot(self) -> dict[str, Any]:
        return dict(self._data)
