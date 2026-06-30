# -*- coding: utf-8 -*-
"""代操回复与合规审查的衔接。"""

from __future__ import annotations

import re

from neuralpal.tools.agent.pending import load_pending

COMPLIANCE_FALLBACK_SNIPPET = "未能通过安全校验"

_AGENT_DENIAL_RE = re.compile(
    r"(我无法代你|不能代你|无法向他人发送|不能向他人发送|不能替您发送|不能代您|"
    r"不应由.{0,4}代发|第三方代发|身份与授权|沟通真实性|代理个人通信|"
    r"我不能控制你的电脑|我无法操作本机|我只是 AI 助手不能代劳)",
    re.IGNORECASE,
)

_AGENT_USER_RE = re.compile(
    r"(帮(我|你把)|你去|打开|整理|存放|存储|移动|桌面|文件夹|代(我|劳)|控制.{0,6}电脑|"
    r"看看.{0,8}成果|执行|确认|取消)",
    re.IGNORECASE,
)


def is_agent_delegation_user_text(text: str) -> bool:
    return bool(_AGENT_USER_RE.search((text or "").strip()))


def is_agent_capability_denial(text: str) -> bool:
    return bool(_AGENT_DENIAL_RE.search(text or ""))


def agent_denial_fallback(session_id: str) -> str:
    pending = load_pending(session_id)
    if pending is not None and pending.status == "awaiting_confirm":
        return (
            "可以代操，计划已登记如下：\n"
            f"{pending.summary_for_user()}\n\n"
            "请回复「确认」后我会通过工具执行（含微信内发消息）；回复「取消」可放弃。"
        )
    return (
        "可以代操。你已在贾维斯 App 内授权本机操作。"
        "请说明具体任务，我会先列出步骤；你回复「确认」后通过工具执行，"
        "不会在未授权时代发消息。"
    )


def is_compliance_fallback_text(text: str) -> bool:
    return COMPLIANCE_FALLBACK_SNIPPET in (text or "")


def execution_succeeded(summary: str, *, goal: str = "", actions_taken: int = 0) -> bool:
    s = (summary or "").strip()
    if not s:
        return False
    if s.startswith("【联网搜索完成"):
        return True
    if s.startswith("【执行失败】") or s.startswith("【执行未完成】"):
        return False
    if "未找到文件名含" in s:
        return False
    if s.startswith("【门控拒绝】"):
        return False
    if "未能打开" in s and "已完成" not in s:
        return False
    if "已达最大步数" in s:
        return False

    # 仅 Computer Use / 本机代操结果才走完成判定；联网搜索不走截图逻辑
    if s.startswith("【联网搜索") or "Claude Computer Use" in s or "已操作" in s[:80]:
        pass
    elif goal or actions_taken or "微信" in s:
        try:
            from neuralpal.desktop.computer_use_helpers import computer_use_completed

            return computer_use_completed(s, goal=goal, actions_taken=actions_taken)
        except ImportError:
            pass
    return True


def _failure_hint(*, goal: str, summary: str) -> str:
    g = (goal or "").lower()
    short = summary.strip()
    if short.startswith("【执行未完成】"):
        short = short.replace("【执行未完成】", "", 1).strip()
    if short.startswith("【执行失败】"):
        short = short.replace("【执行失败】", "", 1).strip()

    if any(k in g for k in ("微信", "wechat", "发消息")):
        if len(short) > 280 or "127.0.0.1" in short or "Step" in short:
            return (
                "代操停留在贾维斯网页或中途停步，未在微信内完成发送。"
                "请先手动把微信窗口切到前台，再说「确认」重试。"
            )
    if any(k in g for k in ("搜索", "查询", "比价", "调研", "品牌", "价格", "官网")):
        return (short[:360] + "…") if len(short) > 360 else short or "联网搜索未返回有效结果，请再说「确认」重试。"

    if len(short) > 280 or "127.0.0.1" in short:
        return (short[:360] + "…") if len(short) > 360 else short

    return short[:240] if short else "执行未成功，请说明要重试还是修改任务。"


def format_execution_reply(*, goal: str, summary: str, task_id: str = "") -> str:
    """用户确认后直接向用户展示执行结果（沈昼口吻，简洁）。"""
    ok = execution_succeeded(summary, goal=goal)
    body = summary.strip()

    if ok and body.startswith("【联网搜索"):
        from neuralpal.desktop.claude_web_search import strip_web_search_wrapper

        conclusion = strip_web_search_wrapper(body)
        return conclusion or body

    head = "任务已完成。" if ok else "任务未成功。"
    if task_id:
        head = f"{head}（{task_id}）"
    if not ok:
        short = _failure_hint(goal=goal, summary=summary)
        goal_line = f"目标：{goal.strip()}\n" if goal.strip() else ""
        return f"{head}\n{goal_line}说明：{short}".strip()

    goal_line = f"目标：{goal.strip()}\n" if goal.strip() else ""
    if len(body) > 6000:
        body = body[:6000] + "…"
    return f"{head}\n{goal_line}{body}".strip()


def reconcile_agent_reply_text(text: str, session_id: str) -> str:
    """
    代操计划已写入 pending，但合规模块误杀展示文案时，用任务摘要替代兜底错误话。
    模型否认代操能力时，替换为正确引导。
    """
    from neuralpal.config import get_settings

    if get_settings().agent_enabled and is_agent_capability_denial(text or ""):
        return agent_denial_fallback(session_id)

    pending = load_pending(session_id)
    if pending is None:
        return text

    if pending.status == "awaiting_confirm":
        if is_compliance_fallback_text(text) or not (text or "").strip():
            return (
                "我已拟定代办计划：\n"
                f"{pending.summary_for_user()}\n\n"
                "请回复「确认」后开始执行；回复「取消」可放弃。"
            )
        return text

    if pending.status == "completed" and pending.execution_summary:
        if is_compliance_fallback_text(text):
            return pending.execution_summary[:4000]
        return text

    if pending.status == "failed" and pending.error:
        if is_compliance_fallback_text(text):
            return f"任务执行失败：{pending.error}"
        return text

    return text
