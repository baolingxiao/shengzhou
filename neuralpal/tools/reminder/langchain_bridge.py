# -*- coding: utf-8 -*-
"""
主模型调用桥接：挂载提醒工具 + 沈昼代办工具，并执行 tool-call 闭环。
"""

from __future__ import annotations

import logging
import sys
from typing import Any, List, Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, ToolMessage

from neuralpal.config import get_settings

logger = logging.getLogger(__name__)

_MAX_TOOL_ROUNDS = 8


def _verbose_print(verbose: bool, message: str) -> None:
    if verbose:
        print(f"\n[NeuralPal·verbose] {message}", file=sys.stderr, flush=True)


def _tool_calls_from_message(msg: BaseMessage) -> List[dict[str, Any]]:
    raw = getattr(msg, "tool_calls", None)
    if not raw:
        return []
    out: List[dict[str, Any]] = []
    for tc in raw:
        if isinstance(tc, dict):
            out.append(tc)
            continue
        try:
            if hasattr(tc, "model_dump"):
                d = tc.model_dump()
                out.append(
                    {
                        "name": str(d.get("name") or ""),
                        "id": str(d.get("id") or ""),
                        "args": d.get("args") if isinstance(d.get("args"), dict) else {},
                    }
                )
                continue
        except Exception:
            pass
        name = getattr(tc, "name", None) or getattr(tc, "function", None)
        tid = getattr(tc, "id", "") or ""
        args = getattr(tc, "args", None)
        if args is None and hasattr(tc, "get"):
            args = tc.get("args")  # type: ignore[assignment]
        if isinstance(name, str):
            out.append({"name": name, "id": tid, "args": args if isinstance(args, dict) else {}})
    return out


def _collect_tools(
    *,
    verbose: bool,
    session_id: str,
    character_id: str | None,
    chat_id: int | None,
    user_id: int | None,
    agent_tools_allowed: bool = True,
) -> list[Any]:
    tools: list[Any] = []
    s = get_settings()

    if s.reminder_enabled and chat_id is not None:
        from neuralpal.tools.reminder.tools import build_reminder_langchain_tools

        uid = int(user_id) if user_id is not None else int(chat_id)
        tools.extend(build_reminder_langchain_tools(chat_id=int(chat_id), user_id=uid))

    if s.agent_enabled and agent_tools_allowed:
        from neuralpal.tools.agent.tools import ActionToolContext, build_agent_langchain_tools

        ctx = ActionToolContext(session_id=session_id, character_id=character_id)
        agent_tools = build_agent_langchain_tools(ctx)
        tools.extend(agent_tools)
        _verbose_print(verbose, f"[AGENT_TOOLS] loaded count={len(agent_tools)}")

    return tools


def invoke_with_neuralpal_tools(
    llm: BaseChatModel,
    messages: Sequence[BaseMessage],
    *,
    verbose: bool,
    session_id: str = "default",
    character_id: str | None = None,
    chat_id: int | None = None,
    user_id: int | None = None,
    agent_tools_allowed: bool = True,
) -> BaseMessage:
    tools = _collect_tools(
        verbose=verbose,
        session_id=session_id,
        character_id=character_id,
        chat_id=chat_id,
        user_id=user_id,
        agent_tools_allowed=agent_tools_allowed,
    )
    if not tools:
        return llm.invoke(list(messages))

    tool_by_name = {t.name: t for t in tools}
    llm_tools = llm.bind_tools(tools)
    msgs: List[BaseMessage] = list(messages)

    last_ai: BaseMessage | None = None
    for round_idx in range(_MAX_TOOL_ROUNDS):
        last_ai = llm_tools.invoke(msgs)
        calls = _tool_calls_from_message(last_ai)
        if not calls:
            break
        _verbose_print(verbose, f"[NEURALPAL_TOOLS] round={round_idx + 1} tool_calls={len(calls)}")
        msgs.append(last_ai)
        for tc in calls:
            name = str(tc.get("name") or "")
            tid = str(tc.get("id") or "")
            args = tc.get("args") if isinstance(tc.get("args"), dict) else {}
            tool = tool_by_name.get(name)
            if tool is None:
                body = f"[错误] 未知工具：{name}"
            else:
                try:
                    body = str(tool.invoke(args or {}))
                except Exception as exc:
                    logger.exception("Tool invoke failed name=%s", name)
                    body = f"[错误] 工具执行失败：{exc}"
            msgs.append(ToolMessage(content=body[:12000], tool_call_id=tid or f"call_{round_idx}"))
    if last_ai is None:
        return llm.invoke(list(messages))
    return last_ai


def invoke_claude_with_optional_reminder_tools(
    llm: BaseChatModel,
    messages: Sequence[BaseMessage],
    *,
    verbose: bool,
    chat_id: int | None,
    user_id: int | None,
    session_id: str = "default",
    character_id: str | None = None,
) -> BaseMessage:
    """向后兼容别名；现统一走 invoke_with_neuralpal_tools。"""
    return invoke_with_neuralpal_tools(
        llm,
        messages,
        verbose=verbose,
        session_id=session_id,
        character_id=character_id,
        chat_id=chat_id,
        user_id=user_id,
    )
