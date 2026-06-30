# -*- coding: utf-8 -*-
"""根据用户 MBTI 生成推荐 AI 伴侣性格。"""

from __future__ import annotations

import re

from neuralpal.characters.mbti_profiles import (
    _FALLBACK_MBTI,
    format_companion_guide,
    format_companion_summary,
    get_mbti_profile,
)
from neuralpal.characters.cpc import cpc_legend, decode_partner_code
from neuralpal.characters.models import PersonalityRecommendation
from neuralpal.characters.tuning_defaults import TUNING_DIMENSIONS, tuning_for_mbti

_VALID_MBTI = re.compile(r"^[EI][NS][FT][JP]$", re.IGNORECASE)


def normalize_mbti(raw: str, *, default: str = _FALLBACK_MBTI) -> str:
    mbti = (raw or default).strip().upper()[:4]
    if _VALID_MBTI.match(mbti):
        return mbti
    return default.upper()


def recommend_for_mbti(raw_mbti: str) -> PersonalityRecommendation:
    mbti = normalize_mbti(raw_mbti)
    profile = get_mbti_profile(mbti)
    return PersonalityRecommendation(
        user_mbti=profile.mbti,
        user_type_name=profile.type_name,
        partner_code=profile.partner_code,
        partner_code_decode=decode_partner_code(profile.partner_code),
        cpc_legend=cpc_legend(),
        ai_type=profile.ai_type,
        companion_keywords=list(profile.keywords),
        summary=format_companion_summary(profile),
        personality_description=format_companion_guide(profile),
        defaults=tuning_for_mbti(profile.mbti),
        tuning_dimensions=[dict(d) for d in TUNING_DIMENSIONS],
    )


def default_character_name(mbti: str, ai_type: str) -> str:
    return f"{ai_type} · {normalize_mbti(mbti)}"
