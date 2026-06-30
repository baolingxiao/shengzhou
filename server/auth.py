# -*- coding: utf-8 -*-
"""登录校验：管理者账户与普通账户。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH_USERS_PATH = ROOT / "data" / "auth_users.json"


@dataclass(frozen=True)
class AuthUser:
    username: str
    role: str = "user"

    @property
    def is_admin(self) -> bool:
        return self.role in {"admin", "developer"}


def _admin_credentials() -> tuple[str, str]:
    return (
        os.getenv("JARVIS_AUTH_USER", "admin").strip(),
        os.getenv("JARVIS_AUTH_PASSWORD", "jarvis"),
    )


def _normalize_role(raw: object) -> str:
    token = str(raw or "").strip().lower()
    if token in {"admin", "developer"}:
        return "developer"
    return "user"


@lru_cache(maxsize=1)
def _admin_usernames() -> frozenset[str]:
    names: set[str] = set()
    primary, _ = _admin_credentials()
    if primary:
        names.add(primary)
    extra = os.getenv("JARVIS_ADMIN_USERS", "")
    for part in extra.split(","):
        token = part.strip()
        if token:
            names.add(token)
    for row in _load_auth_user_rows():
        role = _normalize_role(row.get("role"))
        if role == "developer" or row.get("is_admin") is True:
            username = str(row.get("username", "")).strip()
            if username:
                names.add(username)
    return frozenset(names)


def _load_auth_user_rows() -> list[dict]:
    if not AUTH_USERS_PATH.is_file():
        return []
    try:
        payload = json.loads(AUTH_USERS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    users = payload.get("users") if isinstance(payload, dict) else payload
    if not isinstance(users, list):
        return []
    return [row for row in users if isinstance(row, dict)]


def _load_extra_users() -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for row in _load_auth_user_rows():
        username = str(row.get("username", "")).strip()
        password = str(row.get("password", ""))
        if not username or not password:
            continue
        role = "developer" if row.get("is_admin") is True else _normalize_role(row.get("role"))
        out.append((username, password, role))
    return out


def authenticate(username: str, password: str) -> AuthUser | None:
    name = username.strip()
    if not name or not password:
        return None

    admin_user, admin_pass = _admin_credentials()
    if name == admin_user and password == admin_pass:
        return AuthUser(username=name, role="developer")

    for extra_user, extra_pass, extra_role in _load_extra_users():
        if name == extra_user and password == extra_pass:
            return AuthUser(username=name, role=extra_role)

    return None


def is_admin_username(username: str | None) -> bool:
    if not username:
        return False
    return username.strip() in _admin_usernames()


def role_for_username(username: str | None) -> str:
    if not username:
        return "user"
    return "developer" if is_admin_username(username) else "user"
