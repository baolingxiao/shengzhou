# -*- coding: utf-8 -*-
"""CPC 生活画像加载。"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from neuralpal.companion_life.models import CompanionLifeProfile
from neuralpal.topic_radar.config import cpc_profile_key

logger = logging.getLogger(__name__)

_PROFILES_PATH = Path(__file__).resolve().parent / "config" / "cpc_life_profiles.json"


@lru_cache(maxsize=1)
def load_life_profiles() -> dict[str, CompanionLifeProfile]:
    if not _PROFILES_PATH.is_file():
        logger.error("CPC life profiles missing: %s", _PROFILES_PATH)
        return {}
    raw = json.loads(_PROFILES_PATH.read_text(encoding="utf-8"))
    out: dict[str, CompanionLifeProfile] = {}
    for key, row in raw.items():
        if not isinstance(row, dict):
            continue
        profile = CompanionLifeProfile.model_validate(row)
        out[key.upper()] = profile
        out[key] = profile
    return out


def get_life_profile(profile_key: str) -> CompanionLifeProfile | None:
    key = (profile_key or "").strip().upper()
    return load_life_profiles().get(key)


def resolve_profile_key(user_mbti: str, partner_code: str = "") -> str:
    from neuralpal.characters.mbti_profiles import get_mbti_profile

    mbti = (user_mbti or "INFP").strip().upper()[:4]
    code = (partner_code or get_mbti_profile(mbti).partner_code).strip().upper()
    return cpc_profile_key(code, mbti)


def profile_for_character(user_mbti: str, partner_code: str = "") -> CompanionLifeProfile | None:
    return get_life_profile(resolve_profile_key(user_mbti, partner_code))
