# -*- coding: utf-8 -*-
"""LangChain 代办工具定义。"""

from __future__ import annotations

import logging
from typing import Annotated

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from neuralpal.characters.prompt_bridge import resolve_character_for_session
from neuralpal.config import get_settings
from neuralpal.desktop.orchestrator import execute_proposal
from neuralpal.tools.agent.gate import check_execute, check_proposal
from neuralpal.tools.agent.models import ActionProposal, ActionSurface, RiskLevel, new_task_id
from neuralpal.tools.agent.pending import clear_pending, load_pending, save_pending

logger = logging.getLogger(__name__)


class ProposeActionInput(BaseModel):
    goal: str = Field(description="用户委托的目标，一句话概括")
    surface: ActionSurface = Field(description="local=本机 | web=网页 | chain=混合")
    steps: list[str] = Field(description="人类可读的执行步骤列表")
    risk_level: RiskLevel = Field(description="L3只读 L2编辑发送 L1付款删除等")
    reason: str = Field(description="为何判断需要代操（简短）")


class ExecuteActionInput(BaseModel):
    task_id: str = Field(description="propose_action 返回的任务编号")


class CancelActionInput(BaseModel):
    task_id: str = Field(default="", description="要取消的任务编号；空则取消当前 pending")


class ActionToolContext:
    def __init__(self, *, session_id: str, character_id: str | None) -> None:
        self.session_id = session_id
        self.character_id = character_id

    def _character(self):
        return resolve_character_for_session(self.session_id, character_id=self.character_id)


def build_agent_langchain_tools(ctx: ActionToolContext) -> list[StructuredTool]:
    if not get_settings().agent_enabled:
        return []

    def propose_action(
        goal: str,
        surface: ActionSurface,
        steps: list[str],
        risk_level: RiskLevel,
        reason: str,
    ) -> str:
        existing = load_pending(ctx.session_id)
        if existing and existing.status not in ("failed", "cancelled"):
            if existing.status == "completed" and existing.execution_summary:
                return (
                    f"【上一任务 {existing.task_id} 已完成，请先向用户汇报结果】\n"
                    f"{existing.execution_summary[:2000]}"
                )
            return (
                f"【已有任务 {existing.task_id} · 状态={existing.status}】"
                "请先请用户确认/取消，或等当前任务结束，再提交新任务。\n"
                + existing.summary_for_user()
            )

        proposal = ActionProposal(
            task_id=new_task_id(),
            goal=goal.strip(),
            surface=surface,
            steps=[str(s).strip() for s in steps if str(s).strip()],
            risk_level=risk_level,
            reason=reason.strip(),
            session_id=ctx.session_id,
            character_id=ctx.character_id,
        )
        gate = check_proposal(proposal, ctx._character())
        if not gate.allowed:
            return f"【门控拒绝】{gate.message}"

        if gate.requires_confirm:
            proposal.status = "awaiting_confirm"
        else:
            proposal.status = "confirmed"

        save_pending(proposal)
        confirm_hint = "请用户回复「确认」后开始执行。" if gate.requires_confirm else "已通过门控，可调用 execute_action。"
        return (
            f"【已创建任务 {proposal.task_id}】\n"
            + proposal.summary_for_user()
            + f"\n\n{confirm_hint}"
        )

    def execute_action(task_id: str) -> str:
        pending = load_pending(ctx.session_id)
        if pending is None:
            return "【错误】当前会话没有待执行任务。"
        if task_id.strip() and pending.task_id != task_id.strip():
            return f"【错误】任务编号不匹配。当前 pending={pending.task_id}"

        if pending.status == "awaiting_confirm":
            return "【错误】用户尚未确认。请先请用户回复「确认」。"

        if pending.status == "completed":
            return f"【已完成 {pending.task_id}】\n{pending.execution_summary[:4000]}"

        if pending.status == "running":
            return f"【执行中】任务 {pending.task_id} 正在运行，请稍后再查。"

        gate = check_execute(pending, ctx._character())
        if not gate.allowed:
            return f"【门控拒绝】{gate.message}"

        pending.status = "running"
        save_pending(pending)
        try:
            summary = execute_proposal(pending)
            pending.status = "completed"
            pending.execution_summary = summary[:12000]
            save_pending(pending)
            return f"【执行完成 {pending.task_id}】\n{summary}"
        except Exception as exc:
            logger.exception("execute_action failed")
            pending.status = "failed"
            pending.error = str(exc)
            save_pending(pending)
            return f"【执行失败】{exc}"

    def cancel_action(task_id: str = "") -> str:
        pending = load_pending(ctx.session_id)
        if pending is None:
            return "当前没有待取消的任务。"
        if task_id.strip() and pending.task_id != task_id.strip():
            return f"【错误】任务编号不匹配。当前 pending={pending.task_id}"
        clear_pending(ctx.session_id)
        return f"【已取消】任务 {pending.task_id}。"

    def get_action_status(task_id: str = "") -> str:
        pending = load_pending(ctx.session_id)
        if pending is None:
            return "当前会话无代办任务。"
        if task_id.strip() and pending.task_id != task_id.strip():
            return f"未找到任务 {task_id}。当前 pending={pending.task_id}"
        extra = ""
        if pending.execution_summary:
            extra = f"\n\n最近结果：\n{pending.execution_summary[:2000]}"
        if pending.error:
            extra = f"\n\n错误：{pending.error}"
        return f"任务 {pending.task_id} · 状态={pending.status}\n{pending.summary_for_user()}{extra}"

    return [
        StructuredTool.from_function(
            func=propose_action,
            name="propose_action",
            description=(
                "用户委托代操本机或网页时，创建代办计划。"
                "必须提供 goal/surface/steps/risk_level。"
                "创建后须等用户确认再 execute。"
            ),
            args_schema=ProposeActionInput,
        ),
        StructuredTool.from_function(
            func=execute_action,
            name="execute_action",
            description="用户已明确确认后，执行 propose_action 创建的任务。未确认时禁止调用。",
            args_schema=ExecuteActionInput,
        ),
        StructuredTool.from_function(
            func=cancel_action,
            name="cancel_action",
            description="取消当前或指定 pending 任务。",
            args_schema=CancelActionInput,
        ),
        StructuredTool.from_function(
            func=get_action_status,
            name="get_action_status",
            description="查询当前会话代办任务状态与执行结果。",
        ),
    ]
