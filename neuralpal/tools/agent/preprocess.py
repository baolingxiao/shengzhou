# -*- coding: utf-8 -*-
"""chat_turn 前的确认/取消预处理。"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from neuralpal.characters.prompt_bridge import resolve_character_for_session
from neuralpal.config import get_settings
from neuralpal.desktop.orchestrator import execute_proposal
from neuralpal.tools.agent.confirm import ConfirmIntent, parse_confirm_intent
from neuralpal.tools.agent.gate import check_execute, check_proposal
from neuralpal.tools.agent.pending import clear_pending, load_pending, save_pending
from neuralpal.tools.agent.reply import format_execution_reply, execution_succeeded

logger = logging.getLogger(__name__)

_EXECUTABLE_ON_CONFIRM = frozenset({"awaiting_confirm", "confirmed"})


@dataclass
class PreprocessResult:
    handled: bool
    augmented_user_text: str
    system_note: str = ""
    pending_action: dict | None = None
    execution_summary: str = ""
    direct_reply: str = ""


def _run_pending_execution(
    pending,
    *,
    session_id: str,
    character,
) -> PreprocessResult:
    gate = check_proposal(pending, character)
    if not gate.allowed:
        clear_pending(session_id)
        note = f"[系统] 任务 {pending.task_id} 被拒绝：{gate.message}"
        return PreprocessResult(
            handled=True,
            direct_reply=gate.message,
            augmented_user_text=f"{note}\n\n用户原话：确认",
            system_note=note,
        )

    pending.status = "confirmed"
    save_pending(pending)

    exec_gate = check_execute(pending, character)
    if not exec_gate.allowed:
        note = f"[系统] 无法执行：{exec_gate.message}"
        return PreprocessResult(
            handled=True,
            direct_reply=exec_gate.message,
            augmented_user_text=f"{note}\n\n用户原话：确认",
            system_note=note,
            pending_action=pending.to_dict(),
        )

    pending.status = "running"
    save_pending(pending)
    try:
        summary = execute_proposal(pending)
        reply = format_execution_reply(
            goal=pending.goal,
            summary=summary,
            task_id=pending.task_id,
        )
        ok = execution_succeeded(summary, goal=pending.goal or "")
        if ok:
            clear_pending(session_id)
        else:
            pending.status = "failed"
            pending.execution_summary = summary[:12000]
            pending.error = summary[:500]
            save_pending(pending)
        note = (
            f"[系统] 任务 {pending.task_id} "
            + ("已执行完成。\n" if ok else "执行未成功。\n")
            + f"执行摘要：\n{summary[:4000]}"
        )
        return PreprocessResult(
            handled=True,
            direct_reply=reply,
            augmented_user_text=(
                f"{note}\n\n"
                + (
                    "【重要】上一代办已在本轮开始前执行完毕。"
                    "请直接向用户汇报上述执行摘要，禁止再 propose_action 新任务。\n\n"
                    if ok
                    else "【重要】执行未成功，请向用户说明原因，不要谎称已完成。\n\n"
                )
                + "用户原话：确认"
            ),
            system_note=note,
            execution_summary=summary if ok else "",
        )
    except Exception as exc:
        logger.exception("preprocess execute failed")
        pending.status = "failed"
        pending.error = str(exc)
        save_pending(pending)
        note = f"[系统] 任务 {pending.task_id} 执行失败：{exc}"
        reply = format_execution_reply(
            goal=pending.goal,
            summary=f"【执行失败】{exc}",
            task_id=pending.task_id,
        )
        return PreprocessResult(
            handled=True,
            direct_reply=reply,
            augmented_user_text=f"{note}\n\n用户原话：确认",
            system_note=note,
            pending_action=pending.to_dict(),
        )


def preprocess_agent_turn(
    user_text: str,
    *,
    session_id: str,
    character_id: str | None,
) -> PreprocessResult:
    if not get_settings().agent_enabled:
        return PreprocessResult(handled=False, augmented_user_text=user_text)

    pending = load_pending(session_id)
    intent = parse_confirm_intent(user_text)

    if pending is not None and pending.is_expired():
        clear_pending(session_id)
        pending = None

    character = resolve_character_for_session(session_id, character_id=character_id)

    if intent == ConfirmIntent.CANCEL:
        if pending is None:
            return PreprocessResult(
                handled=True,
                direct_reply="当前没有待取消的代办任务。",
                augmented_user_text=user_text,
            )
        clear_pending(session_id)
        note = f"[系统] 用户已取消代办任务 {pending.task_id}。"
        return PreprocessResult(
            handled=True,
            direct_reply=f"好，已取消任务 {pending.task_id}。",
            augmented_user_text=f"{note}\n\n用户原话：{user_text}",
            system_note=note,
        )

    if pending is not None and intent == ConfirmIntent.MODIFY:
        note = (
            f"[系统] 用户希望修改待确认任务 {pending.task_id}。"
            "请根据用户最新说明重新 propose_action，或询问缺什么信息。"
        )
        return PreprocessResult(
            handled=False,
            augmented_user_text=f"{note}\n\n用户原话：{user_text}",
            system_note=note,
            pending_action=pending.to_dict(),
        )

    if pending is not None and intent == ConfirmIntent.CONFIRM:
        if pending.status == "completed" and pending.execution_summary:
            reply = format_execution_reply(
                goal=pending.goal,
                summary=pending.execution_summary,
                task_id=pending.task_id,
            )
            clear_pending(session_id)
            return PreprocessResult(
                handled=True,
                direct_reply=reply,
                augmented_user_text=user_text,
                execution_summary=pending.execution_summary,
            )

        if pending.status in _EXECUTABLE_ON_CONFIRM:
            return _run_pending_execution(pending, session_id=session_id, character=character)

        if pending.status == "running":
            return PreprocessResult(
                handled=True,
                direct_reply=f"任务 {pending.task_id} 正在执行中，请稍候。",
                augmented_user_text=user_text,
                pending_action=pending.to_dict(),
            )

        if pending.status == "failed":
            from neuralpal.desktop.routing import is_web_search_only

            if is_web_search_only(pending):
                pending.status = "awaiting_confirm"
                pending.error = ""
                save_pending(pending)
                return _run_pending_execution(pending, session_id=session_id, character=character)
            msg = pending.error or pending.execution_summary[:400] or "未知错误"
            return PreprocessResult(
                handled=True,
                direct_reply=f"上一任务 {pending.task_id} 已失败：{msg}\n如需重试，请重新描述任务或说「取消」后重来。",
                augmented_user_text=user_text,
                pending_action=pending.to_dict(),
            )

    if intent == ConfirmIntent.CONFIRM and pending is None:
        note = (
            "[系统] 用户回复了「确认」，但当前会话没有待执行的 pending 任务。"
            "请勿凭空 propose 新任务；请请用户重新说明要做什么，"
            "或调用 get_action_status 查看是否已有结果。"
        )
        return PreprocessResult(
            handled=True,
            direct_reply=(
                "我这边没有收到已登记的代办计划，所以还不能直接执行。"
                "请再说一次具体要做什么（例如：把媒体文件里的「雨天垂钓」移到桌面），"
                "我会先列出步骤，请你确认后再动手。"
            ),
            augmented_user_text=f"{note}\n\n用户原话：{user_text}",
            system_note=note,
        )

    if pending is None:
        return PreprocessResult(handled=False, augmented_user_text=user_text)

    return PreprocessResult(
        handled=False,
        augmented_user_text=user_text,
        pending_action=pending.to_dict() if pending.status == "awaiting_confirm" else None,
    )
