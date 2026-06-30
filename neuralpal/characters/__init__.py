# -*- coding: utf-8 -*-
"""AI 伴侣角色管理。"""

from neuralpal.characters.models import AICharacter
from neuralpal.characters.personality import recommend_for_mbti
from neuralpal.characters.prompt_bridge import build_character_system_addon, resolve_character_for_session
from neuralpal.characters.session_binding import get_session_character_binding
from neuralpal.characters.store import get_character_store

__all__ = [
    "AICharacter",
    "build_character_system_addon",
    "get_character_store",
    "get_session_character_binding",
    "recommend_for_mbti",
    "resolve_character_for_session",
]
