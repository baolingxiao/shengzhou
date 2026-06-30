# -*- coding: utf-8 -*-
"""
OpenAI Realtime WebRTC — 后端 ephemeral token 签发。

官方流程（https://developers.openai.com/api/docs/guides/realtime-webrtc）：
  1. 本服务 POST /v1/realtime/client_secrets（Bearer 真实 OPENAI_API_KEY）
  2. 返回 response.value 给前端作为 ephemeral key
  3. 浏览器直连 POST /v1/realtime/calls（Bearer ephemeral + SDP）
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from openai import OpenAI

from neuralpal.config import get_settings
from server.realtime_prompt import build_realtime_instructions

logger = logging.getLogger(__name__)

OPENAI_CLIENT_SECRETS_PATH = "/realtime/client_secrets"


@dataclass(frozen=True)
class RealtimeSessionResult:
    client_secret: str
    model: str
    voice: str
    expires_at: str
    session_id: str


def _safety_identifier(session_id: str) -> str:
    """OpenAI-Safety-Identifier：稳定、脱敏的用户标识。"""
    raw = (session_id or "default").strip()[:120] or "default"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _expires_at_iso(expires_at: int) -> str:
    return datetime.fromtimestamp(int(expires_at), tz=timezone.utc).isoformat()


def create_realtime_session(
    *,
    character_id: str | None,
    session_id: str,
    mode: str = "voice_chat",
) -> RealtimeSessionResult:
    """
    向 OpenAI 申请 Realtime client secret（ephemeral token）。

    绝不记录或返回真实 OPENAI_API_KEY。
    """
    settings = get_settings()
    api_key = (settings.openai_api_key or "").strip()
    if not api_key:
        raise ValueError("未配置 OPENAI_API_KEY，无法创建 Realtime 会话")

    model = (settings.openai_realtime_model or "gpt-realtime").strip()
    voice = (settings.openai_realtime_voice or "alloy").strip()
    speed = float(settings.openai_realtime_speed or 1.0)
    speed = max(0.25, min(1.5, speed))
    sid = (session_id or "default").strip()[:120] or "default"

    logger.info("[RealtimeSession] request received mode=%s", mode)
    logger.info("[RealtimeSession] character_id=%s", character_id or "")
    logger.info("[RealtimeSession] session_id=%s", sid)
    logger.info("[RealtimeSession] model=%s voice=%s speed=%s", model, voice, speed)

    instructions = build_realtime_instructions(character_id, sid)
    est_tokens = len(instructions) // 2  # 粗估，仅日志
    logger.info("[RealtimeSession] instructions_chars=%s est_tokens~%s", len(instructions), est_tokens)

    session_body: dict = {
        "type": "realtime",
        "model": model,
        "instructions": instructions,
        "audio": {
            "input": {
                "turn_detection": {
                    "type": "server_vad",
                    "interrupt_response": True,
                    "create_response": True,
                    "silence_duration_ms": 500,
                },
            },
            "output": {"voice": voice, "speed": speed},
        },
    }

    client = OpenAI(api_key=api_key)
    try:
        resp = client.realtime.client_secrets.create(
            session=session_body,
            extra_headers={"OpenAI-Safety-Identifier": _safety_identifier(sid)},
        )
    except Exception as exc:
        logger.error("[RealtimeSession] error %s", type(exc).__name__)
        raise RuntimeError(f"OpenAI Realtime client_secrets 失败：{exc}") from exc

    secret = (resp.value or "").strip()
    if not secret:
        logger.error("[RealtimeSession] error empty client secret")
        raise RuntimeError("OpenAI 未返回有效的 ephemeral client secret")

    expires_iso = _expires_at_iso(resp.expires_at)
    logger.info("[RealtimeSession] token created expires_at=%s", expires_iso)

    return RealtimeSessionResult(
        client_secret=secret,
        model=model,
        voice=voice,
        expires_at=expires_iso,
        session_id=sid,
    )
