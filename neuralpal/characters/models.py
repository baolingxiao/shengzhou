# -*- coding: utf-8 -*-
"""AI 伴侣角色数据模型。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CharacterTuning(BaseModel):
    intimacy: int = Field(default=3, ge=1, le=5)
    initiative: int = Field(default=3, ge=1, le=5)
    emotion_expression: int = Field(default=3, ge=1, le=5)
    rationality: int = Field(default=3, ge=1, le=5)
    humor: int = Field(default=3, ge=1, le=5)
    independent_world: int = Field(default=3, ge=1, le=5)
    quiet_companion: int = Field(default=3, ge=1, le=5)


class AICharacter(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    name: str = "我的 AI 伴侣"
    user_mbti: str = "INFP"
    ai_type: str = "温柔陪伴型"
    personality_description: str = ""
    intimacy: int = Field(default=3, ge=1, le=5)
    initiative: int = Field(default=3, ge=1, le=5)
    emotion_expression: int = Field(default=3, ge=1, le=5)
    rationality: int = Field(default=3, ge=1, le=5)
    humor: int = Field(default=3, ge=1, le=5)
    independent_world: int = Field(default=3, ge=1, le=5)
    quiet_companion: int = Field(default=3, ge=1, le=5)
    ending_signature: str | None = None
    first_intro_paragraphs: list[str] = Field(default_factory=list)
    intro_delivered: bool = False
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)

    @field_validator("user_mbti", mode="before")
    @classmethod
    def _normalize_mbti(cls, v: object) -> str:
        return str(v or "INFP").strip().upper()[:4]

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_tuning(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        level_map = {"低": 2, "中": 3, "高": 4}
        initiative_map = {"被动回应": 2, "适度主动": 3, "非常主动": 4}
        emotion_map = {"克制": 2, "自然": 3, "强烈": 4}
        style_rationality = {"理性": 4, "温柔": 2, "治愈": 2, "幽默": 3, "活泼": 2, "暧昧": 3}
        style_humor = {"幽默": 4, "活泼": 4, "理性": 2, "温柔": 2, "治愈": 2, "暧昧": 3}
        world_map = {"朋友型": 3, "恋人型": 3, "导师型": 4, "树洞型": 4, "搭子型": 4}
        quiet_map = {"朋友型": 3, "恋人型": 2, "导师型": 3, "树洞型": 4, "搭子型": 2}

        if isinstance(out.get("intimacy"), str):
            out["intimacy"] = level_map.get(out["intimacy"], 3)
        if isinstance(out.get("initiative"), str):
            out["initiative"] = initiative_map.get(out["initiative"], 3)
        if isinstance(out.get("emotion_expression"), str):
            out["emotion_expression"] = emotion_map.get(out["emotion_expression"], 3)
        if "rationality" not in out and isinstance(out.get("chat_style"), str):
            out["rationality"] = style_rationality.get(out["chat_style"], 3)
        if "humor" not in out and isinstance(out.get("chat_style"), str):
            out["humor"] = style_humor.get(out["chat_style"], 3)
        if "independent_world" not in out and isinstance(out.get("companion_mode"), str):
            out["independent_world"] = world_map.get(out["companion_mode"], 3)
        if "quiet_companion" not in out and isinstance(out.get("companion_mode"), str):
            out["quiet_companion"] = quiet_map.get(out["companion_mode"], 3)
        for key in (
            "chat_style",
            "companion_mode",
        ):
            out.pop(key, None)
        # 旧角色无 intro 字段：视为已投递，避免老数据重复自我介绍
        if "intro_delivered" not in out and "first_intro_paragraphs" not in out:
            out["intro_delivered"] = True
        return out


class CharacterCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    user_mbti: str
    ai_type: str
    personality_description: str = Field(max_length=12000)
    intimacy: int = Field(ge=1, le=5)
    initiative: int = Field(ge=1, le=5)
    emotion_expression: int = Field(ge=1, le=5)
    rationality: int = Field(ge=1, le=5)
    humor: int = Field(ge=1, le=5)
    independent_world: int = Field(ge=1, le=5)
    quiet_companion: int = Field(ge=1, le=5)


class CharacterUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=40)
    ending_signature: str | None = Field(default=None, max_length=80)
    personality_description: str | None = Field(default=None, max_length=12000)
    intimacy: int | None = Field(default=None, ge=1, le=5)
    initiative: int | None = Field(default=None, ge=1, le=5)
    emotion_expression: int | None = Field(default=None, ge=1, le=5)
    rationality: int | None = Field(default=None, ge=1, le=5)
    humor: int | None = Field(default=None, ge=1, le=5)
    independent_world: int | None = Field(default=None, ge=1, le=5)
    quiet_companion: int | None = Field(default=None, ge=1, le=5)


class PersonalityRecommendation(BaseModel):
    user_mbti: str
    user_type_name: str = ""
    partner_code: str = ""
    partner_code_decode: dict[str, Any] = Field(default_factory=dict)
    cpc_legend: list[dict[str, Any]] = Field(default_factory=list)
    ai_type: str
    companion_keywords: list[str] = Field(default_factory=list)
    summary: str = ""
    personality_description: str
    defaults: CharacterTuning
    tuning_dimensions: list[dict[str, str]] = Field(default_factory=list)
