# -*- coding: utf-8 -*-
"""Claude 联网搜索（纯信息检索，不操控浏览器）。"""

from __future__ import annotations

import logging

from neuralpal.config import get_settings
from neuralpal.desktop.mac_control import mock_execute
from neuralpal.llm.claude_client import get_anthropic_client

logger = logging.getLogger(__name__)


def run_claude_web_search(goal: str, *, mock: bool = False) -> str:
    s = get_settings()
    if mock or s.agent_mock_mode:
        return mock_execute(f"[联网搜索] {goal}")

    if not (s.anthropic_api_key or "").strip():
        return "【执行失败】未配置 ANTHROPIC_API_KEY，无法使用 Claude 联网搜索。"

    client = get_anthropic_client()
    model = (s.agent_claude_model or s.anthropic_model_sonnet).strip()
    tool_type = s.topic_radar_claude_web_search_tool_version
    max_uses = max(1, int(s.topic_radar_claude_web_search_max_uses or 5))

    prompt = (
        "你是沈昼，替用户做联网调研。\n"
        "请用 web_search 查最新公开信息，然后只输出结论。\n"
        "输出规则（必须遵守）：\n"
        "1. 禁止复述用户问题或任务目标\n"
        "2. 禁止长篇调研说明、免责、方法论；最多一句「价格以官网实时为准」\n"
        "3. 直接给结果列表，按用户要求的顺序排列\n"
        "4. 每条尽量一行：品牌名 | 网址 | 规格与参考单价\n"
        "5. 纯文本，禁止 Markdown\n"
        "6. 查不到写「待查」，不要凑字数\n\n"
        f"调研要点：{goal.strip()}"
    )

    try:
        response = client.messages.create(
            model=model,
            max_tokens=s.agent_claude_max_tokens,
            tools=[
                {
                    "type": tool_type,
                    "name": "web_search",
                    "max_uses": max_uses,
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        logger.exception("Claude web search failed: %s", exc)
        return f"【执行失败】Claude 联网搜索调用失败：{exc}"

    parts: list[str] = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(str(text).strip())

    body = "\n\n".join(p for p in parts if p).strip()
    if not body:
        return "【执行失败】联网搜索未返回可用正文。"

    searches = 0
    usage = getattr(response, "usage", None)
    server_tool = getattr(usage, "server_tool_use", None) if usage else None
    if server_tool is not None:
        searches = int(getattr(server_tool, "web_search_requests", 0) or 0)

    prefix = f"【联网搜索完成（检索 {searches} 次）】\n" if searches else "【联网搜索完成】\n"
    return prefix + body


def strip_web_search_wrapper(summary: str) -> str:
    """去掉内部状态前缀，只保留给用户看的正文。"""
    lines = (summary or "").strip().splitlines()
    while lines and lines[0].startswith("【联网搜索"):
        lines.pop(0)
    return "\n".join(lines).strip()
