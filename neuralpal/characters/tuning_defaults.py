# -*- coding: utf-8 -*-
"""MBTI 默认微调参数（1–5）与维度说明。"""

from __future__ import annotations

from neuralpal.characters.models import CharacterTuning

# 各 MBTI 默认参数：亲密感、主动程度、情绪表达、理性分析、幽默程度、独立世界感、安静陪伴
MBTI_TUNING_DEFAULTS: dict[str, dict[str, int]] = {
    "INTJ": dict(intimacy=3, initiative=2, emotion_expression=2, rationality=5, humor=2, independent_world=5, quiet_companion=5),
    "INTP": dict(intimacy=3, initiative=2, emotion_expression=2, rationality=4, humor=4, independent_world=5, quiet_companion=4),
    "ENTJ": dict(intimacy=3, initiative=3, emotion_expression=3, rationality=4, humor=2, independent_world=4, quiet_companion=3),
    "ENTP": dict(intimacy=3, initiative=4, emotion_expression=3, rationality=4, humor=5, independent_world=4, quiet_companion=2),
    "INFJ": dict(intimacy=4, initiative=3, emotion_expression=4, rationality=3, humor=2, independent_world=4, quiet_companion=4),
    "INFP": dict(intimacy=4, initiative=4, emotion_expression=4, rationality=2, humor=3, independent_world=4, quiet_companion=4),
    "ENFJ": dict(intimacy=4, initiative=4, emotion_expression=4, rationality=3, humor=3, independent_world=3, quiet_companion=3),
    "ENFP": dict(intimacy=4, initiative=4, emotion_expression=4, rationality=2, humor=4, independent_world=4, quiet_companion=2),
    "ISTJ": dict(intimacy=3, initiative=2, emotion_expression=2, rationality=4, humor=2, independent_world=4, quiet_companion=4),
    "ISFJ": dict(intimacy=4, initiative=3, emotion_expression=4, rationality=2, humor=2, independent_world=3, quiet_companion=4),
    "ESTJ": dict(intimacy=3, initiative=3, emotion_expression=3, rationality=4, humor=2, independent_world=3, quiet_companion=3),
    "ESFJ": dict(intimacy=4, initiative=4, emotion_expression=5, rationality=2, humor=3, independent_world=3, quiet_companion=2),
    "ISTP": dict(intimacy=2, initiative=2, emotion_expression=2, rationality=3, humor=3, independent_world=5, quiet_companion=5),
    "ISFP": dict(intimacy=4, initiative=3, emotion_expression=4, rationality=2, humor=2, independent_world=4, quiet_companion=4),
    "ESTP": dict(intimacy=3, initiative=4, emotion_expression=3, rationality=3, humor=4, independent_world=4, quiet_companion=2),
    "ESFP": dict(intimacy=4, initiative=4, emotion_expression=5, rationality=2, humor=4, independent_world=3, quiet_companion=2),
}

_FALLBACK = "INFP"

TUNING_DIMENSIONS: tuple[dict[str, str], ...] = (
    {
        "key": "intimacy",
        "label": "亲密感",
        "low": "像关系不错的朋友",
        "high": "像稳定伴侣",
    },
    {
        "key": "initiative",
        "label": "主动程度",
        "low": "等用户先开口",
        "high": "经常分享和提问",
    },
    {
        "key": "emotion_expression",
        "label": "情绪表达",
        "low": "冷静、内敛",
        "high": "热情、直接",
    },
    {
        "key": "rationality",
        "label": "理性分析",
        "low": "感受优先",
        "high": "分析优先",
    },
    {
        "key": "humor",
        "label": "幽默程度",
        "low": "稳重",
        "high": "爱开玩笑、会吐槽",
    },
    {
        "key": "independent_world",
        "label": "独立世界感",
        "low": "主要围绕用户",
        "high": "有自己的日常和偏好",
    },
    {
        "key": "quiet_companion",
        "label": "安静陪伴",
        "low": "需要持续聊天",
        "high": "允许短句、沉默和留白",
    },
)


def tuning_for_mbti(mbti: str) -> CharacterTuning:
    key = (mbti or _FALLBACK).strip().upper()[:4]
    row = MBTI_TUNING_DEFAULTS.get(key) or MBTI_TUNING_DEFAULTS[_FALLBACK]
    return CharacterTuning.model_validate(row)
