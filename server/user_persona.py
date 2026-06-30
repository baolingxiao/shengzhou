# -*- coding: utf-8 -*-
"""普通用户自定义角色（本地文件存储）。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PERSONA_PATH = ROOT / "data" / "user_personas.json"


@dataclass(frozen=True)
class UserPersona:
    username: str
    display_name: str
    style_prompt: str
    chatgpt_api_key: str
    claude_api_key: str
    deepseek_api_key: str
    doubao_api_key: str
    updated_at: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_all() -> dict[str, dict[str, str]]:
    if not PERSONA_PATH.is_file():
        return {}
    try:
        payload = json.loads(PERSONA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    out: dict[str, dict[str, str]] = {}
    for key, val in payload.items():
        if not isinstance(key, str) or not isinstance(val, dict):
            continue
        out[key.strip()] = {
            "display_name": str(val.get("display_name", "")).strip(),
            "style_prompt": str(val.get("style_prompt", "")).strip(),
            "chatgpt_api_key": str(val.get("chatgpt_api_key", "")).strip(),
            "claude_api_key": str(val.get("claude_api_key", "")).strip(),
            "deepseek_api_key": str(val.get("deepseek_api_key", "")).strip(),
            "doubao_api_key": str(val.get("doubao_api_key", "")).strip(),
            "updated_at": str(val.get("updated_at", "")).strip(),
        }
    return out


def _normalized_provider_keys(
    *,
    chatgpt_api_key: str,
    claude_api_key: str,
    deepseek_api_key: str,
    doubao_api_key: str,
) -> dict[str, str]:
    return {
        "chatgpt_api_key": (chatgpt_api_key or "").strip(),
        "claude_api_key": (claude_api_key or "").strip(),
        "deepseek_api_key": (deepseek_api_key or "").strip(),
        "doubao_api_key": (doubao_api_key or "").strip(),
    }


def _has_any_provider_key(row: dict[str, str]) -> bool:
    return bool(
        row.get("chatgpt_api_key", "").strip()
        or row.get("claude_api_key", "").strip()
        or row.get("deepseek_api_key", "").strip()
        or row.get("doubao_api_key", "").strip()
    )


def _write_all(data: dict[str, dict[str, str]]) -> None:
    PERSONA_PATH.parent.mkdir(parents=True, exist_ok=True)
    PERSONA_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def get_user_persona(username: str) -> UserPersona | None:
    name = username.strip()
    if not name:
        return None
    row = _read_all().get(name)
    if not row:
        return None
    display_name = row.get("display_name", "").strip()
    style_prompt = row.get("style_prompt", "").strip()
    if not display_name or not style_prompt or not _has_any_provider_key(row):
        return None
    return UserPersona(
        username=name,
        display_name=display_name,
        style_prompt=style_prompt,
        chatgpt_api_key=row.get("chatgpt_api_key", "").strip(),
        claude_api_key=row.get("claude_api_key", "").strip(),
        deepseek_api_key=row.get("deepseek_api_key", "").strip(),
        doubao_api_key=row.get("doubao_api_key", "").strip(),
        updated_at=row.get("updated_at", "") or "",
    )


def upsert_user_persona(
    username: str,
    *,
    display_name: str,
    style_prompt: str,
    chatgpt_api_key: str = "",
    claude_api_key: str = "",
    deepseek_api_key: str = "",
    doubao_api_key: str = "",
) -> UserPersona:
    name = username.strip()
    disp = display_name.strip()
    prompt = style_prompt.strip()
    provider_keys = _normalized_provider_keys(
        chatgpt_api_key=chatgpt_api_key,
        claude_api_key=claude_api_key,
        deepseek_api_key=deepseek_api_key,
        doubao_api_key=doubao_api_key,
    )
    if not name:
        raise ValueError("username is empty")
    if not disp:
        raise ValueError("角色名字不能为空")
    if not prompt:
        raise ValueError("回复风格 prompt 不能为空")
    if not _has_any_provider_key(provider_keys):
        raise ValueError("请至少填写一个模型 API Key（ChatGPT / Claude / DeepSeek / 豆包）")
    if len(disp) > 40:
        raise ValueError("角色名字不能超过 40 字")
    if len(prompt) > 4000:
        raise ValueError("回复风格 prompt 不能超过 4000 字")

    data = _read_all()
    updated_at = _now_iso()
    data[name] = {
        "display_name": disp,
        "style_prompt": prompt,
        "chatgpt_api_key": provider_keys["chatgpt_api_key"],
        "claude_api_key": provider_keys["claude_api_key"],
        "deepseek_api_key": provider_keys["deepseek_api_key"],
        "doubao_api_key": provider_keys["doubao_api_key"],
        "updated_at": updated_at,
    }
    _write_all(data)
    return UserPersona(
        username=name,
        display_name=disp,
        style_prompt=prompt,
        chatgpt_api_key=provider_keys["chatgpt_api_key"],
        claude_api_key=provider_keys["claude_api_key"],
        deepseek_api_key=provider_keys["deepseek_api_key"],
        doubao_api_key=provider_keys["doubao_api_key"],
        updated_at=updated_at,
    )

