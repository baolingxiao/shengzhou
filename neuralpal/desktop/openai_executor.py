# -*- coding: utf-8 -*-
"""OpenAI Computer Using Agent（网页任务）。"""

from __future__ import annotations

import logging

from neuralpal.config import get_settings
from neuralpal.desktop.claude_executor import run_claude_computer_task
from neuralpal.desktop.mac_control import get_display_size, mock_execute

logger = logging.getLogger(__name__)


def _openai_computer_use_unavailable(exc: Exception, err: str) -> bool:
    """账号无 Computer Use 模型权限时不应静默改成本机 Claude 代操。"""
    low = err.lower()
    if "does not exist or you do not have access" in low:
        return True
    if "computer-use-preview" in low and "model_not_found" in low:
        return True
    name = type(exc).__name__
    return name in ("NotFoundError", "PermissionDeniedError") and "computer" in low


def run_openai_web_task(goal: str, *, mock: bool = False) -> str:
    s = get_settings()
    if mock or s.agent_mock_mode:
        return mock_execute(f"[网页] {goal}")

    if not (s.openai_api_key or "").strip():
        logger.info("OPENAI_API_KEY missing; fallback to local browser via Claude")
        return run_claude_computer_task(
            f"【网页任务，请打开 Safari 或 Chrome 完成】{goal}",
            mock=False,
        )

    width, height = get_display_size()
    try:
        from openai import OpenAI

        client = OpenAI(api_key=s.openai_api_key)
        model = s.agent_openai_model

        if hasattr(client, "responses") and hasattr(client.responses, "create"):
            response = client.responses.create(
                model=model,
                truncation="auto",
                tools=[
                    {
                        "type": "computer_use_preview",
                        "display_width": width,
                        "display_height": height,
                        "environment": "browser",
                    }
                ],
                input=goal,
            )
            text = getattr(response, "output_text", None)
            if text:
                return str(text).strip()
            out = getattr(response, "output", None)
            if out:
                return str(out)[:8000]
            return "网页任务已提交，请查看执行结果。"

        logger.warning("OpenAI responses API unavailable; fallback to Claude local browser")
    except Exception as exc:
        logger.exception("OpenAI web task failed: %s", exc)
        err = str(exc)
        if _openai_computer_use_unavailable(exc, err):
            return (
                "【执行失败】OpenAI Computer Use（computer-use-preview）当前账号不可用。"
                "该模型需 OpenAI Usage Tier 3–5 且须单独开通，不是普通 ChatGPT API 密钥默认就有。"
                "因此网页任务无法走 OpenAI 云端浏览器，也未自动改成本机代操。"
                f"\n原始错误：{err[:280]}"
            )
        return run_claude_computer_task(
            f"【网页任务（OpenAI 不可用，改本机浏览器）】{goal}\n上次错误：{exc}",
            mock=False,
        )

    return run_claude_computer_task(
        f"【网页任务，请打开浏览器完成】{goal}",
        mock=False,
    )
