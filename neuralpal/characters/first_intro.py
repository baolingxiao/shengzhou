# -*- coding: utf-8 -*-
"""伴侣首次自我介绍：生成、暂存与一次性投递。"""

from __future__ import annotations

from neuralpal.characters.mbti_intros import build_intro_paragraphs
from neuralpal.characters.models import AICharacter
from neuralpal.characters.session_greeting import prepare_intro_paragraphs_for_delivery
from neuralpal.characters.store import get_character_store


def ensure_intro_paragraphs(char: AICharacter) -> list[str]:
    """确保角色已缓存自我介绍段落（不标记已投递）。"""
    if char.first_intro_paragraphs:
        return list(char.first_intro_paragraphs)
    return build_intro_paragraphs(char.name, char.user_mbti)


def peek_pending_intro(character_id: str) -> list[str]:
    """尚未投递的首次自我介绍段落（预览，不改变状态）。"""
    store = get_character_store()
    char = store.get_character(character_id.strip())
    if not char or char.intro_delivered:
        return []
    paragraphs = ensure_intro_paragraphs(char)
    if not paragraphs:
        return []
    if not char.first_intro_paragraphs:
        store.save_intro_paragraphs(char.id, paragraphs)
    return paragraphs


def consume_pending_intro(
    character_id: str,
    *,
    session_id: str = "default",
) -> list[str]:
    """读取并标记首次自我介绍已投递（仅应在前端实际展示后调用）。"""
    paragraphs = peek_pending_intro(character_id)
    if not paragraphs:
        return []
    cid = character_id.strip()
    char = get_character_store().get_character(cid)
    if char:
        paragraphs = prepare_intro_paragraphs_for_delivery(
            paragraphs, char, session_id=session_id
        )
    get_character_store().mark_intro_delivered(cid)
    return paragraphs
