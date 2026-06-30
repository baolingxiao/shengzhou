# -*- coding: utf-8 -*-
"""Companion Life 数据模型。"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


def _instance_id_field(*, default: str = "") -> Any:
    return Field(
        default=default,
        validation_alias=AliasChoices("companion_instance_id", "companion_id"),
        serialization_alias="companion_instance_id",
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


class CompanionLifeProfile(BaseModel):
    profile_key: str
    cpc_code: str
    companion_name: str
    matched_user_mbti: str
    personality_style: list[str] = Field(default_factory=list)
    base_topics: list[str] = Field(default_factory=list)
    preferred_activities: list[str] = Field(default_factory=list)
    preferred_event_types: list[str] = Field(default_factory=list)
    preferred_content_types: list[str] = Field(default_factory=list)
    daily_event_min: int = 1
    daily_event_max: int = 4
    external_exploration_ratio: float = 0.30
    internal_continuation_ratio: float = 0.30
    user_related_ratio: float = 0.25
    quiet_daily_ratio: float = 0.15
    normal_day_ratio: float = 0.60
    exploration_day_ratio: float = 0.25
    reflection_day_ratio: float = 0.10
    special_day_ratio: float = 0.05
    opening_style: str = ""
    diary_style: str = ""
    avoid_patterns: list[str] = Field(default_factory=list)
    forbidden_patterns: list[str] = Field(default_factory=list)
    default_ending_signature: str = ""


class CompanionState(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    companion_instance_id: str = _instance_id_field(default="")
    user_id: str
    profile_key: str
    updated_at: datetime = Field(default_factory=_now)
    mood: str = "平静"
    energy: float = 0.6
    curiosity: float = 0.5
    social_need: float = 0.4
    emotional_openness: float = 0.5
    focus_level: float = 0.5
    focus_topic: str | None = None
    recent_interests: list[str] = Field(default_factory=list)
    unfinished_thread_ids: list[str] = Field(default_factory=list)
    active_life_arc_ids: list[str] = Field(default_factory=list)
    last_diary_date: date | None = None
    last_event_date: date | None = None
    last_proactive_share_at: datetime | None = None
    available_chat_snippet_count: int = 0

    @field_validator(
        "energy",
        "curiosity",
        "social_need",
        "emotional_openness",
        "focus_level",
        mode="before",
    )
    @classmethod
    def _clamp_metrics(cls, v: Any) -> float:
        return _clamp01(v)

    @property
    def companion_id(self) -> str:
        """Deprecated compatibility alias. Remove after migration stabilizes."""
        return self.companion_instance_id


class LifeEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:12]}")
    user_id: str = ""
    companion_instance_id: str = _instance_id_field(default="")
    profile_key: str = ""
    event_date: date = Field(default_factory=lambda: _now().date())
    created_at: datetime = Field(default_factory=_now)
    event_type: str = ""
    event_category: str = ""
    activity_type: str = ""
    title: str = ""
    summary: str = ""
    narrative: str = ""
    reality_level: str = "internal_reflection"
    source_type: str = "internal_reflection"
    source_title: str | None = None
    source_url: str | None = None
    source_date: str | None = None
    source_excerpt: str | None = None
    related_user_topics: list[str] = Field(default_factory=list)
    related_project_ids: list[str] = Field(default_factory=list)
    related_thread_ids: list[str] = Field(default_factory=list)
    related_arc_ids: list[str] = Field(default_factory=list)
    mood_before: str | None = None
    mood_after: str | None = None
    energy_cost: float = 0.0
    curiosity_gain: float = 0.0
    social_need_delta: float = 0.0
    importance: float = 0.5
    future_chat_value: float = 0.5
    novelty_score: float = 0.5
    continuity_score: float = 0.5
    grounding_score: float = 0.5
    cpc_fit_score: float = 0.5
    final_score: float = 0.0
    status: str = "candidate"
    expires_at: datetime | None = None
    obsidian_path: str | None = None

    @property
    def companion_id(self) -> str:
        """Deprecated compatibility alias. Remove after migration stabilizes."""
        return self.companion_instance_id


class OpenThread(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    thread_id: str = Field(default_factory=lambda: f"thread_{uuid4().hex[:10]}")
    user_id: str = ""
    companion_instance_id: str = _instance_id_field(default="")
    profile_key: str = ""
    title: str = ""
    topic: str = ""
    summary: str = ""
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    importance: float = 0.5
    status: str = "open"
    origin_event_id: str | None = None
    related_event_ids: list[str] = Field(default_factory=list)
    next_possible_actions: list[str] = Field(default_factory=list)
    close_conditions: list[str] = Field(default_factory=list)
    obsidian_path: str | None = None

    @property
    def companion_id(self) -> str:
        """Deprecated compatibility alias. Remove after migration stabilizes."""
        return self.companion_instance_id


class LifeArc(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    arc_id: str = Field(default_factory=lambda: f"arc_{uuid4().hex[:10]}")
    user_id: str = ""
    companion_instance_id: str = _instance_id_field(default="")
    profile_key: str = ""
    title: str = ""
    theme: str = ""
    description: str = ""
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    progress: float = 0.0
    status: str = "active"
    preferred_actions: list[str] = Field(default_factory=list)
    related_thread_ids: list[str] = Field(default_factory=list)
    related_event_ids: list[str] = Field(default_factory=list)
    obsidian_path: str | None = None

    @field_validator("progress", mode="before")
    @classmethod
    def _clamp_progress(cls, v: Any) -> float:
        return _clamp01(v)

    @property
    def companion_id(self) -> str:
        """Deprecated compatibility alias. Remove after migration stabilizes."""
        return self.companion_instance_id


class ChatSnippet(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    snippet_id: str = Field(default_factory=lambda: f"snip_{uuid4().hex[:10]}")
    user_id: str = ""
    companion_instance_id: str = _instance_id_field(default="")
    profile_key: str = ""
    event_id: str | None = None
    thread_id: str | None = None
    arc_id: str | None = None
    created_at: datetime = Field(default_factory=_now)
    expires_at: datetime | None = None
    snippet_type: str = "recent_thought"
    best_contexts: list[str] = Field(default_factory=list)
    opening: str = ""
    follow_up_question: str | None = None
    tone: str = ""
    importance: float = 0.5
    freshness: float = 0.8
    chat_value: float = 0.5
    status: str = "available"
    used_at: datetime | None = None

    @property
    def companion_id(self) -> str:
        """Deprecated compatibility alias. Remove after migration stabilizes."""
        return self.companion_instance_id


class DailyLifePlan(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    plan_id: str = Field(default_factory=lambda: f"plan_{uuid4().hex[:10]}")
    user_id: str = ""
    companion_instance_id: str = _instance_id_field(default="")
    profile_key: str = ""
    plan_date: date = Field(default_factory=lambda: _now().date())
    day_type: str = "normal_day"
    state_snapshot: CompanionState | None = None
    selected_focus_topics: list[str] = Field(default_factory=list)
    planned_activity_types: list[str] = Field(default_factory=list)
    open_threads_to_continue: list[str] = Field(default_factory=list)
    life_arcs_to_advance: list[str] = Field(default_factory=list)
    external_sources_to_use: list[str] = Field(default_factory=list)
    user_topics_to_consider: list[str] = Field(default_factory=list)
    target_event_count: int = 2
    run_mode: str = "active_day"


class DailyDiary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    diary_id: str = Field(default_factory=lambda: f"diary_{uuid4().hex[:10]}")
    user_id: str = ""
    companion_instance_id: str = _instance_id_field(default="")
    profile_key: str = ""
    diary_date: date = Field(default_factory=lambda: _now().date())
    mood: str = ""
    energy: float = 0.6
    curiosity: float = 0.5
    social_need: float = 0.4
    main_theme: str | None = None
    event_ids: list[str] = Field(default_factory=list)
    thread_ids: list[str] = Field(default_factory=list)
    arc_ids: list[str] = Field(default_factory=list)
    markdown_content: str = ""
    obsidian_path: str | None = None

    @property
    def companion_id(self) -> str:
        """Deprecated compatibility alias. Remove after migration stabilizes."""
        return self.companion_instance_id


class SharedMemory(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    memory_id: str = Field(default_factory=lambda: f"shared_{uuid4().hex[:10]}")
    user_id: str = ""
    companion_instance_id: str = _instance_id_field(default="")
    profile_key: str = ""
    memory_type: str = "shared_topic"
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    title: str = ""
    summary: str = ""
    importance: float = 0.5
    related_conversation_ids: list[str] = Field(default_factory=list)
    related_event_ids: list[str] = Field(default_factory=list)
    related_thread_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    obsidian_path: str | None = None

    @property
    def companion_id(self) -> str:
        """Deprecated compatibility alias. Remove after migration stabilizes."""
        return self.companion_instance_id


class CompanionLifeRunRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    run_id: str = Field(default_factory=lambda: f"run_{uuid4().hex[:10]}")
    user_id: str = ""
    companion_instance_id: str = _instance_id_field(default="")
    profile_key: str = ""
    run_date: date = Field(default_factory=lambda: _now().date())
    started_at: datetime = Field(default_factory=_now)
    finished_at: datetime | None = None
    run_mode: str = "active_day"
    status: str = "running"
    generated_event_count: int = 0
    approved_event_count: int = 0
    rejected_event_count: int = 0
    generated_snippet_count: int = 0
    external_source_count: int = 0
    api_calls: dict[str, Any] = Field(default_factory=dict)
    token_usage: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None

    @property
    def companion_id(self) -> str:
        """Deprecated compatibility alias. Remove after migration stabilizes."""
        return self.companion_instance_id


class GroundedSource(BaseModel):
    source_id: str = Field(default_factory=lambda: f"src_{uuid4().hex[:8]}")
    title: str = ""
    url: str = ""
    date: str = ""
    excerpt: str = ""
    topic: str = ""


class CompanionLifeChatContext(BaseModel):
    intent: str = "casual_chat"
    state_text: str = ""
    diary_excerpt: str = ""
    events_text: str = ""
    snippets_text: str = ""
    threads_text: str = ""
    arcs_text: str = ""
    shared_text: str = ""
    should_inject: bool = False
    should_proactive: bool = False
    chosen_snippet_id: str | None = None


class LifeEventValidationResult(BaseModel):
    ok: bool = True
    reality_level: str = "internal_reflection"
    rewritten: bool = False
    narrative: str = ""
    summary: str = ""
    rejection_reason: str = ""
