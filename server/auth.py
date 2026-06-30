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
    is_admin: bool


def _admin_credentials() -> tuple[str, str]:
    return (
        os.getenv("JARVIS_AUTH_USER", "admin").strip(),
        os.getenv("JARVIS_AUTH_PASSWORD", "jarvis"),
    )


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
        if row.get("role") == "admin" or row.get("is_admin") is True:
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


def _load_extra_users() -> list[tuple[str, str, bool]]:
    out: list[tuple[str, str, bool]] = []
    for row in _load_auth_user_rows():
        username = str(row.get("username", "")).strip()
        password = str(row.get("password", ""))
        if not username or not password:
            continue
        is_admin = row.get("role") == "admin" or row.get("is_admin") is True
        out.append((username, password, is_admin))
    return out


def authenticate(username: str, password: str) -> AuthUser | None:
    name = username.strip()
    if not name or not password:
        return None

    admin_user, admin_pass = _admin_credentials()
    if name == admin_user and password == admin_pass:
        return AuthUser(username=name, is_admin=True)

    for extra_user, extra_pass, extra_admin in _load_extra_users():
        if name == extra_user and password == extra_pass:
            return AuthUser(username=name, is_admin=extra_admin)

    return None


def is_admin_username(username: str | None) -> bool:
    if not username:
        return False
    return username.strip() in _admin_usernames()
