# -*- coding: utf-8 -*-
"""Computer Use 任务简报、环境准备与完成判定。"""

from __future__ import annotations

import re
import subprocess

from neuralpal.desktop.local_apps import open_mac_application
from neuralpal.desktop.routing import proposal_blob

_COMPUTER_USE_BRIEFING = """
【代操环境说明 · 必读】
· 你控制的是用户真实的 macOS 桌面，不是浏览器里的网页模拟器。
· 若当前截图是「贾维斯 / 沈昼 / Ask anything / 127.0.0.1」聊天页，那是控制面板，不是任务 App；请立即 Cmd+Tab 或点 Dock 切换到目标 App（如 WeChat/微信）。
· 必须实际操作直到用户目标达成，禁止只输出计划或分析就 stop。
· 全部完成后，用一句中文汇报结果（例：「已在微信向 xxx 发送：…」）；未完成则不要说已完成。
""".strip()

_INCOMPLETE_RE = re.compile(
    r"(Step\s*\d|第\s*[一二三四五1-5]\s*步|我需要|现在我需要|I need to|Now I need|"
    r"can clearly see|Let me |我将|打算|准备点击|点击.?退出|沈昼|贾维斯|"
    r"Ask anything|127\.0\.0\.1|Thinking|未发送|还没有|尚未|not yet|"
    r"directly operate|assistant interface|AI assistant)",
    re.IGNORECASE,
)

_SUCCESS_RE = re.compile(
    r"(已在微信|微信向|消息已发送|已发送消息|发送成功|成功发送|已将消息|"
    r"message has been sent|sent the message|已完成：|已完成：已打开|"
    r"已将「|移到桌面|移入「)",
    re.IGNORECASE,
)


def is_wechat_ui_task(proposal) -> bool:
    blob = proposal_blob(proposal).lower()
    return "微信" in blob or "wechat" in blob


def prepare_computer_use_environment(proposal) -> str:
    """执行前准备（如先打开并激活微信），返回可拼进日志的前置说明。"""
    notes: list[str] = []
    if is_wechat_ui_task(proposal):
        notes.append(open_mac_application("微信"))
        for app in ("WeChat", "微信"):
            try:
                subprocess.run(
                    ["osascript", "-e", f'tell application "{app}" to activate'],
                    capture_output=True,
                    timeout=8,
                )
                notes.append(f"已尝试将「{app}」置于前台。")
                break
            except OSError:
                continue
    return "\n".join(n for n in notes if n)


def build_computer_use_prompt(proposal) -> str:
    goal = (proposal.goal or "").strip()
    steps = [str(s).strip() for s in (proposal.steps or []) if str(s).strip()]
    parts = [_COMPUTER_USE_BRIEFING, f"【用户目标】\n{goal}"]
    if steps:
        parts.append("【步骤】\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1)))
    if is_wechat_ui_task(proposal):
        parts.append(
            "【微信任务】先确保 WeChat/微信 窗口在前台（不是浏览器聊天页），"
            "再搜索联系人、进入会话、输入并发送消息。"
        )
    return "\n\n".join(parts)


def computer_use_completed(
    summary: str,
    *,
    goal: str = "",
    actions_taken: int = 0,
) -> bool:
    s = (summary or "").strip()
    if not s:
        return False
    if s.startswith("【执行失败】") or s.startswith("【执行未完成】"):
        return False
    if "已达最大步数" in s:
        return False
    if "Claude Computer Use 调用失败" in s:
        return False

    blob = f"{goal}\n{s}".lower()
    is_wechat = "微信" in blob or "wechat" in blob or "发消息" in blob

    if is_wechat:
        if _SUCCESS_RE.search(s):
            return True
        if actions_taken < 3:
            return False
        return False

    if _INCOMPLETE_RE.search(s) and not _SUCCESS_RE.search(s):
        return False

    if len(s) > 500 and not _SUCCESS_RE.search(s):
        return False

    if actions_taken == 0 and is_wechat:
        return False

    # 本地快捷通道的成功句式
    if s.startswith("已完成：") or s.startswith("已完成：将"):
        return True
    if _SUCCESS_RE.search(s):
        return True

    # 纯 end_turn 且无成功信号 → 未完成
    if is_wechat or actions_taken > 0:
        return bool(_SUCCESS_RE.search(s))

    return True
