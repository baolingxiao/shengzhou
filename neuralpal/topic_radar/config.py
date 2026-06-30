# -*- coding: utf-8 -*-
"""话题雷达配置与 CPC Profile 加载。"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from neuralpal.config import get_settings
from neuralpal.topic_radar.models import CPCTopicProfile

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parent / "config"
_CPC_PROFILES_PATH = _CONFIG_DIR / "cpc_topic_profiles.json"


def cpc_profile_key(cpc_code: str, user_mbti: str) -> str:
    return f"{cpc_code.strip().upper()}_{user_mbti.strip().upper()}"


@lru_cache(maxsize=1)
def load_cpc_profiles() -> dict[str, CPCTopicProfile]:
    if not _CPC_PROFILES_PATH.is_file():
        logger.error("CPC topic profiles missing: %s", _CPC_PROFILES_PATH)
        return {}
    raw = json.loads(_CPC_PROFILES_PATH.read_text(encoding="utf-8"))
    out: dict[str, CPCTopicProfile] = {}
    for key, row in raw.items():
        if not isinstance(row, dict):
            continue
        profile = CPCTopicProfile.model_validate(row)
        out[key.upper()] = profile
        out[key] = profile
    return out


def get_cpc_profile(user_mbti: str, partner_code: str = "") -> CPCTopicProfile | None:
    from neuralpal.characters.mbti_profiles import get_mbti_profile

    mbti = (user_mbti or "INFP").strip().upper()[:4]
    code = (partner_code or get_mbti_profile(mbti).partner_code).strip().upper()
    key = cpc_profile_key(code, mbti)
    profiles = load_cpc_profiles()
    if key in profiles:
        return profiles[key]
    # 回退：仅 CPC 前缀匹配
    for k, p in profiles.items():
        if p.matched_user_mbti == mbti and p.cpc_code == code:
            return p
    logger.warning("No CPC profile for key=%s mbti=%s code=%s", key, mbti, code)
    return None


def topic_radar_db_path() -> Path:
    s = get_settings()
    p = Path(s.topic_radar_db_path)
    if not p.is_absolute():
        from neuralpal.config.settings import _project_root

        p = _project_root() / p
    return p


def proactive_limits() -> dict[str, Any]:
    s = get_settings()
    return {
        "max_proactive_seed_per_conversation": s.topic_radar_max_proactive_seeds_per_conversation,
        "minimum_hours_between_proactive_seeds": s.topic_radar_proactive_cooldown_hours,
        "avoid_same_category_days": 3,
    }


def is_topic_radar_enabled() -> bool:
    return bool(get_settings().topic_radar_enabled)
