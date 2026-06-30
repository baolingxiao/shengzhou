# -*- coding: utf-8 -*-
"""话题雷达数据模型。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


SeedStatus = Literal["candidate", "available", "used", "expired", "rejected"]


class CPCTopicProfile(BaseModel):
    cpc_code: str
    companion_name: str
    matched_user_mbti: str
    style: str
    base_topics: list[str] = Field(default_factory=list)
    preferred_seed_types: list[str] = Field(default_factory=list)
    opening_style: str = ""


class SearchTarget(BaseModel):
    topic: str
    why_relevant: str = ""
    broad_queries: list[str] = Field(default_factory=list)
    focused_queries: list[str] = Field(default_factory=list)
    personalized_queries: list[str] = Field(default_factory=list)
    queries_cn: list[str] = Field(default_factory=list)
    freshness_days: int = 30
    wanted_content: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


class SelectedCategory(BaseModel):
    category: str
    reason: str = ""
    search_targets: list[SearchTarget] = Field(default_factory=list)


class SearchPlan(BaseModel):
    generated_at: str = Field(default_factory=_now_iso)
    user_id: str = ""
    cpc_profile_key: str = ""
    selected_categories: list[SelectedCategory] = Field(default_factory=list)


class SourceReference(BaseModel):
    source_title: str = ""
    source_url: str = ""
    source_date: str = "unknown"
    cited_text: str = ""


class SearchUsage(BaseModel):
    web_search_requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class ConversationSeed(BaseModel):
    seed_id: str = Field(default_factory=lambda: uuid4().hex)
    user_id: str = ""
    cpc_profile_key: str = ""
    category: str = ""
    topic: str = ""
    seed_type: str = ""
    title: str = ""
    core_idea: str = ""
    why_relevant_to_user: str = ""
    why_fit_cpc: str = ""
    best_context: list[str] = Field(default_factory=list)
    natural_opening: str = ""
    follow_up_question: str = ""
    source_title: str = ""
    source_url: str = ""
    source_date: str = "unknown"
    cited_text: str = ""
    actual_search_queries: list[str] = Field(default_factory=list)
    relevance_score: float = 0.0
    cpc_fit_score: float = 0.0
    conversation_value_score: float = 0.0
    novelty_score: float = 0.0
    timeliness_score: float = 0.0
    final_score: float = 0.0
    status: SeedStatus = "available"
    created_at: str = Field(default_factory=_now_iso)
    expires_at: str = ""
    used_at: str = ""
    feedback_score: float = 0.0

    @field_validator("final_score", mode="before")
    @classmethod
    def _compute_final_if_missing(cls, v: float, info: Any) -> float:
        if v and float(v) > 0:
            return float(v)
        data = info.data if hasattr(info, "data") else {}
        if not data:
            return float(v or 0)
        return round(
            float(data.get("relevance_score", 0)) * 0.35
            + float(data.get("cpc_fit_score", 0)) * 0.20
            + float(data.get("conversation_value_score", 0)) * 0.25
            + float(data.get("novelty_score", 0)) * 0.10
            + float(data.get("timeliness_score", 0)) * 0.10,
            4,
        )


class SearchResearchResult(BaseModel):
    generated_at: str = Field(default_factory=_now_iso)
    user_id: str = ""
    search_plan_id: str = ""
    selected_seeds: list[ConversationSeed] = Field(default_factory=list)
    discarded_count: int = 0
    search_usage: SearchUsage = Field(default_factory=SearchUsage)
    actual_search_queries: list[str] = Field(default_factory=list)


class TopicFeedback(BaseModel):
    feedback_id: str = Field(default_factory=lambda: uuid4().hex)
    seed_id: str
    user_id: str
    event_type: str
    score_delta: float
    created_at: str = Field(default_factory=_now_iso)


class UserTopicPreference(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    user_id: str
    category: str
    topic: str
    weight: float = 0.5
    positive_count: int = 0
    negative_count: int = 0
    last_updated_at: str = Field(default_factory=_now_iso)


class RadarRunRecord(BaseModel):
    run_id: str = Field(default_factory=lambda: uuid4().hex)
    user_id: str
    cpc_profile_key: str
    started_at: str = Field(default_factory=_now_iso)
    finished_at: str = ""
    status: str = "running"
    selected_categories_json: str = ""
    actual_search_queries_json: str = ""
    doubao_input_tokens: int = 0
    doubao_output_tokens: int = 0
    claude_input_tokens: int = 0
    claude_output_tokens: int = 0
    claude_web_search_requests: int = 0
    error_message: str = ""
