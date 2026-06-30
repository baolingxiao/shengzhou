# -*- coding: utf-8 -*-
"""按 AI 角色解析独立记忆宫殿目录（沈昼等）。"""

from __future__ import annotations

from pathlib import Path

from neuralpal.characters.constants import DEFAULT_CHARACTER_NAME
from neuralpal.memory.palace_layout import ensure_palace_layout

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def character_data_root(character_name: str) -> Path:
    name = (character_name or DEFAULT_CHARACTER_NAME).strip()
    return (_PROJECT_ROOT / "data" / "characters" / name).resolve()


def get_character_palace_root(character_name: str) -> Path:
    """角色专属 knowledge_palace：`data/characters/{name}/knowledge_palace/`"""
    root = character_data_root(character_name) / "knowledge_palace"
    ensure_palace_layout(root)
    return root


def get_character_chroma_path(character_name: str) -> Path:
    return character_data_root(character_name) / "chroma_db"


def ensure_character_palace(character_name: str) -> Path:
    root = get_character_palace_root(character_name)
    root.mkdir(parents=True, exist_ok=True)
    return root


def palace_paths_for_character_id(character_id: str | None = None) -> tuple[Path, Path, str]:
    """解析角色记忆宫殿根目录与 Chroma 路径（聊天与后台共用）。"""
    from neuralpal.characters.constants import DEFAULT_CHARACTER_NAME
    from neuralpal.characters.store import get_character_store

    name = DEFAULT_CHARACTER_NAME
    if character_id:
        char = get_character_store().get_character(character_id.strip())
        if char and char.name.strip():
            name = char.name.strip()
    root = ensure_character_palace(name)
    chroma = get_character_chroma_path(name)
    chroma.mkdir(parents=True, exist_ok=True)
    return root, chroma, name
