# -*- coding: utf-8 -*-
"""Realtime prompt 单元测试。"""

from server.realtime_prompt import (
    build_realtime_instructions,
    estimate_instruction_tokens,
)


def test_build_realtime_instructions_uses_realtime_exclusive_style():
    text = build_realtime_instructions("34750dfcf3be", "test-session")
    assert "Realtime 语音专属规则" in text
    assert "其实啊" in text
    assert "让我想想" in text
    assert "小提问" in text
    assert len(text) > 200


def test_instructions_do_not_inject_text_chat_persona():
    text = build_realtime_instructions("34750dfcf3be", "test-session")
    assert "NEURALPAL_RULES_INTEGRITY_V1" not in text
    assert "[[NEURALPAL_CHARACTER_MEMORY_V1]]" not in text
    assert "人格要点" not in text
    assert "信任关系" not in text
    assert "集团总裁高级特助" not in text


def test_instructions_include_agent_when_enabled(monkeypatch):
    monkeypatch.setenv("NEURALPAL_AGENT_ENABLED", "true")
    from neuralpal.config import get_settings

    get_settings.cache_clear()
    try:
        text = build_realtime_instructions("34750dfcf3be", "test-session")
        assert "[[NEURALPAL_AGENT_DESKTOP_V1]]" in text
        assert "propose_action" in text
    finally:
        get_settings.cache_clear()


def test_instructions_under_openai_token_limit():
    text = build_realtime_instructions("34750dfcf3be", "test-session")
    tokens = estimate_instruction_tokens(text)
    assert tokens < 16_384, f"instructions too long: ~{tokens} tokens"
