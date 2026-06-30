# -*- coding: utf-8 -*-
"""沈昼代办：确认解析、门控、pending 状态。"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from neuralpal.tools.agent.confirm import ConfirmIntent, parse_confirm_intent
from neuralpal.tools.agent.gate import check_proposal
from neuralpal.tools.agent.models import ActionProposal
from neuralpal.tools.agent.pending import clear_pending, load_pending, save_pending
from neuralpal.tools.agent.preprocess import preprocess_agent_turn


def test_confirm_intent():
    assert parse_confirm_intent("确认") == ConfirmIntent.CONFIRM
    assert parse_confirm_intent("行") == ConfirmIntent.CONFIRM
    assert parse_confirm_intent("算了") == ConfirmIntent.CANCEL
    assert parse_confirm_intent("今天天气怎么样") == ConfirmIntent.NONE


def test_pending_roundtrip(monkeypatch):
    tmp = Path(tempfile.mkdtemp())
    monkeypatch.setenv("NEURALPAL_AGENT_STATE_DIR", str(tmp))
    from neuralpal.config import get_settings

    get_settings.cache_clear()

    proposal = ActionProposal(
        task_id="act_test_001",
        goal="打开备忘录",
        surface="local",
        steps=["打开备忘录 App"],
        risk_level="L3",
        reason="用户委托",
        session_id="test-session",
    )
    save_pending(proposal)
    loaded = load_pending("test-session")
    assert loaded is not None
    assert loaded.task_id == "act_test_001"
    assert loaded.goal == "打开备忘录"
    clear_pending("test-session")
    assert load_pending("test-session") is None


def test_confirm_executes_confirmed_status(monkeypatch):
    tmp = Path(tempfile.mkdtemp())
    monkeypatch.setenv("NEURALPAL_AGENT_STATE_DIR", str(tmp))
    from neuralpal.config import get_settings

    get_settings.cache_clear()

    proposal = ActionProposal(
        task_id="act_confirmed",
        goal="在媒体文件中找到测试文件并移到桌面",
        surface="local",
        steps=["搜索并移动"],
        risk_level="L2",
        reason="test",
        session_id="test-session",
        status="confirmed",
    )
    save_pending(proposal)
    pre = preprocess_agent_turn("确认", session_id="test-session", character_id=None)
    assert pre.handled is True
    assert pre.direct_reply
    assert "任务" in pre.direct_reply or "未找到" in pre.direct_reply or "已完成" in pre.direct_reply

    proposal = ActionProposal(
        task_id="act_x",
        goal="帮我在淘宝确认付款",
        surface="web",
        steps=["点击支付"],
        risk_level="L1",
        reason="test",
    )
    result = check_proposal(proposal, None)
    assert result.allowed is False
