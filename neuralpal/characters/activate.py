# -*- coding: utf-8 -*-
"""激活 AI 伴侣角色：绑定会话 + 标记激活时间。"""

from __future__ import annotations

from neuralpal.characters.models import AICharacter
from neuralpal.characters.session_binding import get_session_character_binding
from neuralpal.characters.store import get_character_store


def activate_character_for_session(session_id: str, character_id: str) -> AICharacter:
    store = get_character_store()
    char = store.get_character(character_id.strip())
    if not char:
        raise ValueError("角色不存在")
    get_session_character_binding().activate(session_id, char.id)
    return char
