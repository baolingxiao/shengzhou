# -*- coding: utf-8 -*-
"""伴侣实例身份：companion_instance_id、profile_key 与路径安全。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neuralpal.characters.models import AICharacter

LEGACY_UNRESOLVED_PREFIX = "legacy_unresolved_"
PROFILE_KEY_RE = re.compile(r"^[A-Z]{2,8}_[A-Z]{4}$")


@dataclass(frozen=True)
class CompanionInstanceContext:
    user_id: str
    companion_instance_id: str
    profile_key: str
    companion_name: str
    is_legacy: bool = False


def is_legacy_instance_id(instance_id: str) -> bool:
    return (instance_id or "").strip().startswith(LEGACY_UNRESOLVED_PREFIX)


def is_profile_key_shape(value: str) -> bool:
    return bool(PROFILE_KEY_RE.match((value or "").strip().upper()))


def legacy_unresolved_id(user_id: str, profile_key: str) -> str:
    uid = safe_path_segment(user_id)
    pk = safe_path_segment(profile_key.upper())
    return f"{LEGACY_UNRESOLVED_PREFIX}{uid}_{pk}"


def safe_path_segment(text: str, *, max_len: int = 120) -> str:
    t = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", (text or "").strip())
    t = t.replace("..", "_").strip("._ ")
    return (t[:max_len] or "unknown").strip("._")


def resolve_profile_key_for_character(character: AICharacter) -> str:
    from neuralpal.companion_life.cpc_profiles import resolve_profile_key
    from neuralpal.characters.mbti_profiles import get_mbti_profile

    code = get_mbti_profile(character.user_mbti).partner_code
    return resolve_profile_key(character.user_mbti, code)


def list_characters_by_profile_key(profile_key: str) -> list[AICharacter]:
    from neuralpal.companion_life.cpc_profiles import get_life_profile
    from neuralpal.characters.store import get_character_store

    pk = (profile_key or "").strip().upper()
    if not get_life_profile(pk):
        return []
    out: list[AICharacter] = []
    for char in get_character_store().list_characters():
        try:
            if resolve_profile_key_for_character(char).upper() == pk:
                out.append(char)
        except Exception:
            continue
    return out


def map_legacy_companion_key(user_id: str, old_companion_id: str) -> tuple[str, str, str, list[str]]:
    """将旧 companion_id（实为 profile_key）映射为实例 ID。

    返回: (companion_instance_id, profile_key, migration_status, candidate_character_ids)
    """
    pk = (old_companion_id or "").strip().upper()
    if not pk:
        return legacy_unresolved_id(user_id, "UNKNOWN"), "UNKNOWN", "legacy_unresolved", []
    if not is_profile_key_shape(pk):
        # 已是 character.id 形态
        if is_legacy_instance_id(pk):
            return pk, "", "legacy_unresolved", []
        return pk, pk, "active", []

    candidates = list_characters_by_profile_key(pk)
    ids = [c.id for c in candidates]
    if len(candidates) == 1:
        return candidates[0].id, pk, "active", ids
    reason = "no_matching_character" if not candidates else "multiple_characters_same_cpc"
    return legacy_unresolved_id(user_id, pk), pk, "legacy_unresolved", ids


def load_instance_context(
    user_id: str,
    companion_instance_id: str,
    *,
    companion_name: str = "",
) -> CompanionInstanceContext | None:
    from neuralpal.characters.store import get_character_store

    iid = (companion_instance_id or "").strip()
    if not iid:
        return None
    if is_legacy_instance_id(iid):
        parts = iid[len(LEGACY_UNRESOLVED_PREFIX) :].rsplit("_", 1)
        pk = parts[-1] if len(parts) > 1 else ""
        return CompanionInstanceContext(
            user_id=user_id,
            companion_instance_id=iid,
            profile_key=pk,
            companion_name=companion_name or iid,
            is_legacy=True,
        )
    char = get_character_store().get_character(iid)
    if char:
        pk = resolve_profile_key_for_character(char)
        return CompanionInstanceContext(
            user_id=user_id,
            companion_instance_id=char.id,
            profile_key=pk,
            companion_name=char.name,
            is_legacy=False,
        )
    if is_profile_key_shape(iid):
        return None
    return CompanionInstanceContext(
        user_id=user_id,
        companion_instance_id=iid,
        profile_key="",
        companion_name=companion_name or iid,
        is_legacy=False,
    )
