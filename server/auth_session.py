# -*- coding: utf-8 -*-
"""轻量本地登录会话令牌（Bearer）。"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from dataclasses import dataclass

try:
    from fastapi import Depends, Header, HTTPException
except Exception:  # pragma: no cover - 允许在无 fastapi 的精简测试环境导入
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str) -> None:
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    def Header(default=None, alias: str | None = None):  # type: ignore[override]
        del alias
        return default

    def Depends(dep):  # type: ignore[override]
        return dep

from server.auth import AuthUser

_DEFAULT_TTL_SECONDS = 7 * 24 * 3600


@dataclass(frozen=True)
class AuthSession:
    username: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role in {"admin", "developer"}


def session_id_for_username(username: str) -> str:
    token = (username or "").strip()
    if not token:
        return "default"
    safe = re.sub(r"[^\w\-.]", "_", token)[:80]
    return f"user-{safe}" if safe else "default"


def _secret() -> bytes:
    token = os.getenv("JARVIS_AUTH_SECRET", "jarvis-local-secret").strip()
    return token.encode("utf-8")


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(token: str) -> bytes:
    padding = "=" * (-len(token) % 4)
    return base64.urlsafe_b64decode((token + padding).encode("ascii"))


def _sign(body: str) -> str:
    digest = hmac.new(_secret(), body.encode("utf-8"), hashlib.sha256).digest()
    return _b64url_encode(digest)


def issue_access_token(user: AuthUser, *, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> str:
    now = int(time.time())
    payload = {
        "u": user.username,
        "r": "developer" if user.is_admin else "user",
        "iat": now,
        "exp": now + max(60, int(ttl_seconds)),
    }
    body = _b64url_encode(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    return f"{body}.{_sign(body)}"


def parse_access_token(token: str) -> AuthSession | None:
    raw = (token or "").strip()
    if "." not in raw:
        return None
    body, sig = raw.split(".", 1)
    if not body or not sig:
        return None
    if not hmac.compare_digest(_sign(body), sig):
        return None
    try:
        payload = json.loads(_b64url_decode(body).decode("utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    username = str(payload.get("u", "")).strip()
    role = str(payload.get("r", "user")).strip().lower()
    exp = int(payload.get("exp", 0))
    if not username or exp <= int(time.time()):
        return None
    if role not in {"user", "developer", "admin"}:
        role = "user"
    if role == "admin":
        role = "developer"
    return AuthSession(username=username, role=role)


def require_auth_session(authorization: str | None = Header(None, alias="Authorization")) -> AuthSession:
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录或会话已失效")
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="鉴权头格式错误")
    session = parse_access_token(authorization[len(prefix) :])
    if session is None:
        raise HTTPException(status_code=401, detail="登录会话无效，请重新登录")
    return session


def require_developer_session(session: AuthSession = Depends(require_auth_session)) -> AuthSession:
    if not session.is_admin:
        raise HTTPException(status_code=403, detail="仅开发者账户可访问")
    return session

