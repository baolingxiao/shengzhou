# -*- coding: utf-8 -*-
"""本机 / 网页 / 混合链任务编排。"""

from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from neuralpal.config import get_settings
from neuralpal.desktop.claude_executor import run_claude_computer_task
from neuralpal.desktop.claude_web_search import run_claude_web_search
from neuralpal.desktop.computer_use_helpers import (
    build_computer_use_prompt,
    computer_use_completed,
    prepare_computer_use_environment,
)
from neuralpal.desktop.local_apps import run_local_app_task
from neuralpal.desktop.local_files import run_local_file_task
from neuralpal.desktop.openai_executor import run_openai_web_task
from neuralpal.desktop.routing import is_web_search_only, needs_computer_use

if TYPE_CHECKING:
    from neuralpal.tools.agent.models import ActionProposal

logger = logging.getLogger(__name__)


def execute_proposal(proposal: ActionProposal) -> str:
    goal = proposal.goal.strip()
    if not goal:
        return "【执行失败】任务目标为空。"

    surface = proposal.surface
    logger.info(
        "execute_proposal task_id=%s surface=%s risk=%s search_only=%s",
        proposal.task_id,
        surface,
        proposal.risk_level,
        is_web_search_only(proposal),
    )

    s = get_settings()
    mock = bool(s.agent_mock_mode)

    # 纯文件 / 仅打开 App：不依赖 Computer Use
    if surface == "local" and not needs_computer_use(proposal):
        for runner in (run_local_file_task, run_local_app_task):
            local_result = runner(proposal)
            if local_result is not None:
                return local_result

    # 纯联网搜索：Claude web_search，无需 Mac 辅助功能/录屏
    if surface == "web" and is_web_search_only(proposal):
        return run_claude_web_search(_web_search_goal(proposal), mock=mock)

    if not mock:
        from neuralpal.system.permissions import get_permissions_snapshot, is_jarvis_app_process

        perms = get_permissions_snapshot()
        if perms.get("platform") == "Darwin":
            if not is_jarvis_app_process() and not s.agent_allow_terminal:
                return (
                    "【执行失败】当前不是从「贾维斯.app」启动，系统权限无法绑定到贾维斯。"
                    "请双击 dist/贾维斯.app 打开（或运行 ./scripts/macos/make_jarvis_app.sh 构建）。"
                )
            if not perms.get("agent_control_available"):
                tcc = perms.get("tcc_identity") or "贾维斯"
                return (
                    f"【执行失败】缺少 Mac 系统权限（辅助功能 / 屏幕录制）。"
                    f"请在系统设置 → 隐私与安全性 中打开「{tcc}」开关，然后在贾维斯内点「一键授权」重试。"
                )

    if surface == "local":
        cu_goal = build_computer_use_prompt(proposal)
        prep = prepare_computer_use_environment(proposal)
        if prep:
            cu_goal = prep + "\n\n" + cu_goal
        from neuralpal.desktop import claude_executor as ce

        result = run_claude_computer_task(cu_goal, mock=mock)
        if not computer_use_completed(
            result,
            goal=proposal.goal or "",
            actions_taken=ce.LAST_ACTION_COUNT,
        ):
            return result if result.startswith("【执行未完成】") else (
                f"【执行未完成】代操未达成目标（已操作 {ce.LAST_ACTION_COUNT} 步）。\n{result[:600]}"
            )
        return result

    if surface == "web":
        return _run_web_browser_task(proposal, mock=mock)

    if surface == "chain":
        parts: list[str] = []
        local_steps = [s for s in proposal.steps if _looks_local(s)]
        web_steps = [s for s in proposal.steps if not _looks_local(s)]
        if local_steps:
            local_goal = goal + "\n\n本机步骤：\n" + "\n".join(f"- {x}" for x in local_steps)
            parts.append("【本机阶段】\n" + run_claude_computer_task(local_goal, mock=mock))
        if web_steps:
            web_goal = goal + "\n\n网页步骤：\n" + "\n".join(f"- {x}" for x in web_steps)
            if is_web_search_only(proposal):
                parts.append("【联网搜索】\n" + run_claude_web_search(web_goal, mock=mock))
            else:
                parts.append("【网页浏览器】\n" + _run_web_browser_task(proposal, mock=mock, goal=web_goal))
        if not parts:
            parts.append(run_claude_computer_task(goal, mock=mock))
            parts.append(run_claude_web_search(goal, mock=mock))
        return "\n\n---\n".join(parts)

    return run_claude_computer_task(_computer_use_goal(proposal), mock=mock)


def _web_search_goal(proposal: ActionProposal) -> str:
    goal = (proposal.goal or "").strip()
    steps = [str(s).strip() for s in (proposal.steps or []) if str(s).strip()]
    if not steps:
        return goal
    return goal + "\n\n请覆盖以下要点：\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))


def _run_web_browser_task(
    proposal: ActionProposal,
    *,
    mock: bool,
    goal: str | None = None,
) -> str:
    """需在浏览器里点按/登录：优先 OpenAI 云端浏览器，否则 Claude 本机代操。"""
    text = (goal or _computer_use_goal(proposal)).strip()
    openai_result = run_openai_web_task(text, mock=mock)
    if not openai_result.startswith("【执行失败】"):
        return openai_result
    browser_goal = (
        f"【网页浏览器任务】{text}\n"
        "请使用 Safari 或 Chrome 的新空白标签页完成，不要在贾维斯对话页（127.0.0.1）内操作。"
    )
    from neuralpal.desktop import claude_executor as ce

    result = run_claude_computer_task(browser_goal, mock=mock)
    if not computer_use_completed(result, goal=proposal.goal or "", actions_taken=ce.LAST_ACTION_COUNT):
        return result if result.startswith("【执行未完成】") else (
            f"【执行未完成】网页代操未达成目标（已操作 {ce.LAST_ACTION_COUNT} 步）。\n{result[:600]}"
        )
    return result


def _computer_use_goal(proposal: ActionProposal) -> str:
    """把 steps 一并交给 Computer Use，避免模型只看到 goal 标题。"""
    goal = (proposal.goal or "").strip()
    steps = [str(s).strip() for s in (proposal.steps or []) if str(s).strip()]
    if not steps:
        return goal
    body = goal + "\n\n请按顺序执行：\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
    return body


def _looks_local(step: str) -> bool:
    keys = (
        "本机", "桌面", "finder", "微信", "备忘录", "终端", "打开 app",
        "本地", "文件", "mac", "safari", "chrome",
    )
    low = step.lower()
    return any(k in step or k in low for k in keys)
