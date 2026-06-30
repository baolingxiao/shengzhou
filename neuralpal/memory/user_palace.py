# -*- coding: utf-8 -*-
"""普通用户本地私有记忆宫殿路径。"""

from __future__ import annotations

import re
from pathlib import Path

from neuralpal.memory.palace_layout import ensure_palace_layout

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _safe_user_slug(username: str) -> str:
    raw = (username or "").strip()
    slug = re.sub(r"[^\w\-.]", "_", raw)[:80]
    return slug or "anonymous"


def user_palace_paths(username: str) -> tuple[Path, Path]:
    slug = _safe_user_slug(username)
    base = (_PROJECT_ROOT / "data" / "users" / slug).resolve()
    palace_root = base / "knowledge_palace"
    chroma_path = base / "chroma_db"
    ensure_palace_layout(palace_root)
    chroma_path.mkdir(parents=True, exist_ok=True)
    return palace_root, chroma_path

