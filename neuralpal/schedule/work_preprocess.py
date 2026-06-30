# -*- coding: utf-8 -*-
"""chat_turn 前的上下班 / 加班预处理。"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from neuralpal.characters.prompt_bridge import resolve_character_for_session
from neuralpal.schedule.overtime_state import (
    clear_deferred_task,
    load_overtime_state,
    save_overtime_state,
)
from neuralpal.schedule.task_detect import (
    is_overtime_consent,
    is_overtime_decline,
    is_task_request,
)
from neuralpal.schedule.work_mode import (
    WorkModeSnapshot,
    build_off_hours_refusal,
    grant_overtime_window,
    resolve_work_mode,
    schedule_config_for_character,
)

logger = logging.getLogger(__name__)


@dataclass
class WorkScheduleResult:
    """上下班调度预处理结果。"""

    handled: bool = False
    direct_reply: str = ""
    effective_user_text: str = ""
    work_mode: str = "companion"
    agent_tools_allowed: bool = False
    trust_delta: int | None = None
    trust_points: int | None = None
    system_note: str = ""


def _apply_overtime_tp_cost(character_id: str | None, cost: int) -> tuple[int | None, int | None]:
    try:
        from neuralpal.characters.constants import DEFAULT_CHARACTER_ID
        from neuralpal.characters.trust_points import apply_trust_delta

        snap = apply_trust_delta(
            (character_id or DEFAULT_CHARACTER_ID).strip(),
            -abs(int(cost)),
            reason="非工作时间同意加班执行任务",
        )
        delta = int(snap.get("trust_delta") or -abs(int(cost)))
        tp = int(snap.get("trust_points") or 0)
        return delta, tp
    except Exception as exc:
        logger.warning("overtime TP deduction failed: %s", exc)
        return None, None


def preprocess_work_schedule(
    user_text: str,
    *,
    session_id: str,
    character_id: str | None,
) -> WorkScheduleResult:
    raw = (user_text or "").strip()
    character = resolve_character_for_session(session_id, character_id=character_id)
    snap = resolve_work_mode(session_id, character=character)
    cfg = schedule_config_for_character(character)
    tp_cost = int(cfg.get("overtime_tp_cost") or 5)
    state = load_overtime_state(session_id)

    base = WorkScheduleResult(
        effective_user_text=raw,
        work_mode=snap.mode,
        agent_tools_allowed=snap.agent_tools_allowed,
    )

    # 用户放弃加班 / 取消待办
    if state.awaiting_overtime_consent and is_overtime_decline(raw):
        deferred = state.deferred_task_text
        clear_deferred_task(session_id)
        return WorkScheduleResult(
            handled=True,
            direct_reply="好，那今晚不加班。刚才那件事先放着，有事我们聊点别的。",
            work_mode="companion",
            agent_tools_allowed=False,
            system_note=f"[系统] 用户拒绝加班，已清除待办：{deferred[:200]}",
        )

    # 用户同意加班 → 扣 TP，恢复代办能力，继续执行暂存任务
    if state.awaiting_overtime_consent and is_overtime_consent(raw):
        deferred = (state.deferred_task_text or "").strip()
        trust_delta, trust_points = _apply_overtime_tp_cost(character_id, tp_cost)
        grant_overtime_window(session_id, character_name=(character.name if character else "沈昼"))
        state = load_overtime_state(session_id)
        state.deferred_task_text = ""
        save_overtime_state(state)

        if deferred:
            note = f"[系统] 用户已同意非工作时间加班（TP-{tp_cost}），继续执行：{deferred}"
            return WorkScheduleResult(
                handled=False,
                effective_user_text=deferred,
                work_mode="overtime",
                agent_tools_allowed=True,
                trust_delta=trust_delta,
                trust_points=trust_points,
                system_note=note,
            )

        return WorkScheduleResult(
            handled=True,
            direct_reply="行，加班批准了。你要我办什么事，直接说。",
            work_mode="overtime",
            agent_tools_allowed=True,
            trust_delta=trust_delta,
            trust_points=trust_points,
            system_note=f"[系统] 用户同意加班但未发现暂存任务（TP-{tp_cost}）",
        )

    # 上班 / 已激活加班：直接放行
    if snap.agent_tools_allowed:
        return base

    # 下班陪伴：任务型请求 → 拒绝并暂存
    if is_task_request(raw):
        state.deferred_task_text = raw
        state.awaiting_overtime_consent = True
        state.overtime_active = False
        save_overtime_state(state)
        reply = build_off_hours_refusal(character, tp_cost=tp_cost)
        return WorkScheduleResult(
            handled=True,
            direct_reply=reply,
            work_mode="companion",
            agent_tools_allowed=False,
            system_note=f"[系统] 非办公时段拦截任务，已暂存待加班确认：{raw[:300]}",
        )

    # 纯闲聊
    return WorkScheduleResult(
        effective_user_text=raw,
        work_mode="companion",
        agent_tools_allowed=False,
    )


def sync_overtime_after_agent(session_id: str) -> None:
    """代办完成后若无 pending，结束加班窗口。"""
    from neuralpal.tools.agent.pending import load_pending

    if load_pending(session_id) is not None:
        return
    state = load_overtime_state(session_id)
    if not state.overtime_active:
        return
    state.overtime_active = False
    state.awaiting_overtime_consent = False
    state.deferred_task_text = ""
    save_overtime_state(state)


__all__ = ["WorkScheduleResult", "preprocess_work_schedule", "sync_overtime_after_agent"]
