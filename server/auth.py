# -*- coding: utf-8 -*-
"""登录校验：管理者账户与普通账户。"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH_USERS_PATH = ROOT / "data" / "auth_users.json"
DEFAULT_DEVELOPER_USERNAME = "戴金鑫"


@dataclass(frozen=True)
class AuthUser:
    username: str
    role: str = "user"

    @property
    def is_admin(self) -> bool:
        return self.role in {"admin", "developer"}


def _admin_credentials() -> tuple[str, str]:
    raw_user = os.getenv("JARVIS_AUTH_USER", DEFAULT_DEVELOPER_USERNAME).strip()
    admin_user = raw_user or DEFAULT_DEVELOPER_USERNAME
    # 兼容历史默认 admin，统一映射为开发者实体「戴金鑫」
    if admin_user == "admin":
        admin_user = DEFAULT_DEVELOPER_USERNAME
    return (
        admin_user,
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


def _write_auth_user_rows(rows: list[dict[str, object]]) -> None:
    AUTH_USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUTH_USERS_PATH.write_text(
        json.dumps({"users": rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _username_exists(username: str) -> bool:
    name = (username or "").strip()
    if not name:
        return False
    primary, _ = _admin_credentials()
    if name == primary:
        return True
    if name == "admin" and primary == DEFAULT_DEVELOPER_USERNAME:
        return True
    extra = os.getenv("JARVIS_ADMIN_USERS", "")
    if any(name == token.strip() for token in extra.split(",") if token.strip()):
        return True
    for row in _load_auth_user_rows():
        if str(row.get("username", "")).strip() == name:
            return True
    return False


def authenticate(username: str, password: str) -> AuthUser | None:
    name = username.strip()
    if not name or not password:
        return None

    admin_user, admin_pass = _admin_credentials()
    if password == admin_pass and name in {admin_user, "admin", DEFAULT_DEVELOPER_USERNAME}:
        return AuthUser(username=admin_user, role="developer")

    for extra_user, extra_pass, extra_role in _load_extra_users():
        if name == extra_user and password == extra_pass:
            return AuthUser(username=name, role=extra_role)

    return None


def register_user(username: str, password: str) -> AuthUser:
    name = (username or "").strip()
    pwd = str(password or "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,40}", name):
        raise ValueError("用户名需为 3-40 位字母/数字/._-")
    if len(pwd) < 8:
        raise ValueError("密码至少 8 位")
    if len(pwd) > 128:
        raise ValueError("密码不能超过 128 位")
    if _username_exists(name):
        raise ValueError("用户名已存在")

    rows = _load_auth_user_rows()
    rows.append(
        {
            "username": name,
            "password": pwd,
            "role": "user",
        }
    )
    _write_auth_user_rows(rows)
    _admin_usernames.cache_clear()
    return AuthUser(username=name, role="user")


def is_admin_username(username: str | None) -> bool:
    if not username:
        return False
    return username.strip() in _admin_usernames()


def role_for_username(username: str | None) -> str:
    if not username:
        return "user"
    return "developer" if is_admin_username(username) else "user"
