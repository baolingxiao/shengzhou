# -*- coding: utf-8 -*-
"""Trace 数据脱敏：不记录 API Key、密码等敏感字段。"""

from __future__ import annotations

import re
from typing import Any

_REDACTED = "[REDACTED]"

_EXACT_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "secret",
        "password",
        "passwd",
        "authorization",
        "access_token",
        "refresh_token",
        "bearer",
        "credential",
        "private_key",
    }
)


def _is_sensitive_key(key: str) -> bool:
    k = str(key).lower().replace("-", "_")
    if k in _EXACT_SENSITIVE_KEYS:
        return True
    if k.endswith("_api_key") or k.endswith("_secret") or k.endswith("_password"):
        return True
    return False

# 常见密钥形态（仅用于值脱敏，不用于存储原始值）
_KEY_VALUE_PATTERNS = (
    re.compile(r"(sk-[A-Za-z0-9_-]{8,})", re.IGNORECASE),
    re.compile(r"(Bearer\s+[A-Za-z0-9._-]+)", re.IGNORECASE),
)


def _redact_string(value: str) -> str:
    if not value:
        return value
    out = value
    for pat in _KEY_VALUE_PATTERNS:
        out = pat.sub(_REDACTED, out)
    return out


def sanitize_value(key: str, value: Any) -> Any:
    """按字段名与内容对单值脱敏。"""
    if _is_sensitive_key(key):
        return _REDACTED
    if isinstance(value, str):
        return _redact_string(value)
    if isinstance(value, dict):
        return sanitize_dict(value)
    if isinstance(value, list):
        return [sanitize_value(str(i), v) for i, v in enumerate(value)]
    return value


def sanitize_dict(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    return {k: sanitize_value(k, v) for k, v in data.items()}


def sanitize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [sanitize_dict(m) for m in messages]
