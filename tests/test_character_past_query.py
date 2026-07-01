# -*- coding: utf-8 -*-
from neuralpal.characters.character_rules import is_character_past_query
from neuralpal.characters.prompt_bridge import build_character_system_addon
from neuralpal.characters.store import get_character_store
from neuralpal.characters.constants import DEFAULT_CHARACTER_ID


def test_past_query_detection():
    assert is_character_past_query("你小时候是什么样的？")
    assert is_character_past_query("讲讲你爸爸的事")
    assert is_character_past_query("「昼」这个名字什么意思")
    assert not is_character_past_query("你是谁")
    assert not is_character_past_query("自我介绍一下")
    assert not is_character_past_query("帮我查一下销量")


def test_memory_not_in_default_addon():
    char = get_character_store().get_character(DEFAULT_CHARACTER_ID)
    assert char is not None
    default_addon = build_character_system_addon(char, include_background_memory=False)
    assert "[[NEURALPAL_CHARACTER_MEMORY_V1]]" not in default_addon
    past_addon = build_character_system_addon(char, include_background_memory=True)
    assert "[[NEURALPAL_CHARACTER_MEMORY_V1]]" in past_addon
