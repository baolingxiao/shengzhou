from functools import lru_cache
import os
import re
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_developer_username() -> str:
    raw = os.getenv("JARVIS_AUTH_USER", "戴金鑫").strip()
    token = raw or "戴金鑫"
    return "戴金鑫" if token == "admin" else token


def _default_shenzhou_session_id() -> str:
    safe = re.sub(r"[^\w\-.]", "_", _default_developer_username())[:80]
    return f"user-{safe}" if safe else "default"


# 始终指向仓库根目录的 .env，避免「在别的 cwd 下启动 CLI / IDE Run」时读不到密钥。
_DOTENV_PATH = _project_root() / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_DOTENV_PATH),
        env_file_encoding="utf-8",
        # 若环境变量里存在 ANTHROPIC_API_KEY=（空串），默认会盖住 .env；忽略空串以回落到文件
        env_ignore_empty=True,
        extra="ignore",
    )

    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_realtime_model: str = Field(
        default="gpt-realtime",
        validation_alias="OPENAI_REALTIME_MODEL",
    )
    openai_realtime_voice: str = Field(
        default="alloy",
        validation_alias="OPENAI_REALTIME_VOICE",
    )
    openai_realtime_speed: float = Field(
        default=1.1,
        ge=0.25,
        le=1.5,
        validation_alias="OPENAI_REALTIME_SPEED",
    )

    # Claude 模型 ID（仅杂志热点话题 & YouTube视频模块使用）
    anthropic_model_sonnet: str = Field(
        default="claude-sonnet-4-6",
        validation_alias="ANTHROPIC_MODEL_SONNET",
    )
    anthropic_model_haiku: str = Field(
        default="claude-haiku-4-5",
        validation_alias="ANTHROPIC_MODEL_HAIKU",
    )
    anthropic_model_opus: str = Field(
        default="claude-opus-4-6",
        validation_alias="ANTHROPIC_MODEL_OPUS",
    )
    anthropic_max_tokens: int = Field(
        default=4096,
        ge=256,
        le=8192,
        validation_alias="ANTHROPIC_MAX_TOKENS",
    )

    # --- 主对话 LLM 提供商切换（doubao / claude）---
    active_llm_provider: str = Field(
        default="claude",
        validation_alias="NEURALPAL_LLM_PROVIDER",
    )

    # --- 豆包 Doubao ---
    doubao_api_key: str = Field(default="", validation_alias="DOUBAO_API_KEY")
    doubao_base_url: str = Field(
        default="https://ark.cn-beijing.volces.com/api/v3",
        validation_alias="DOUBAO_BASE_URL",
    )
    doubao_model_pro: str = Field(
        default="doubao-seed-2-0-pro-260215",
        validation_alias="DOUBAO_MODEL_PRO",
    )
    doubao_model_lite: str = Field(
        default="doubao-seed-2-0-lite-260215",
        validation_alias="DOUBAO_MODEL_LITE",
    )
    doubao_model_deep: str = Field(
        default="doubao-seed-2-0-pro-260215",
        validation_alias="DOUBAO_MODEL_DEEP",
    )
    doubao_model_code: str = Field(
        default="doubao-seed-2-0-code-preview-260215",
        validation_alias="DOUBAO_MODEL_CODE",
    )
    doubao_max_tokens: int = Field(
        default=4096,
        ge=256,
        le=16384,
        validation_alias="DOUBAO_MAX_TOKENS",
    )

    rules_pdf_path: Path = Field(
        default=Path("/Users/dai/Downloads/Neural Pal特助.pdf"),
        validation_alias="NEURALPAL_RULES_PDF",
    )

    append_pdf_appendix: bool = Field(
        default=False,
        validation_alias="NEURALPAL_APPEND_PDF_APPENDIX",
    )

    @field_validator("append_pdf_appendix", mode="before")
    @classmethod
    def _coerce_append_pdf_flag(cls, v: Any) -> bool:
        if v is None or v == "":
            return False
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    chroma_persist_path: Path = Field(
        default_factory=lambda: _project_root() / "data" / "chroma_db",
        validation_alias="NEURALPAL_CHROMA_PATH",
    )

    working_memory_max_rounds: int = Field(
        default=5,
        ge=1,
        validation_alias="NEURALPAL_WORKING_MEMORY_MAX_ROUNDS",
    )

    # 混合短期记忆：仅最近 N 轮以完整 Human/AI 注入主模型；更旧轮次用摘要块替代（见 memory_system）
    working_memory_full_rounds: int = Field(
        default=2,
        ge=1,
        validation_alias="NEURALPAL_WORKING_MEMORY_FULL_ROUNDS",
    )

    memory_mixed_short_term_enabled: bool = Field(
        default=True,
        validation_alias="NEURALPAL_MEMORY_MIXED_SHORT_TERM",
    )

    @field_validator("memory_mixed_short_term_enabled", mode="before")
    @classmethod
    def _coerce_mixed_short_term(cls, v: Any) -> bool:
        if v is None or v == "":
            return True
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    # 动态召回：预检索 top1 相似度低于阈值则跳过正式召回（省 token）；可用 NEURALPAL_DYNAMIC_RETRIEVAL=false 关闭
    dynamic_retrieval_enabled: bool = Field(
        default=True,
        validation_alias="NEURALPAL_DYNAMIC_RETRIEVAL",
    )

    @field_validator("dynamic_retrieval_enabled", mode="before")
    @classmethod
    def _coerce_dynamic_retrieval(cls, v: Any) -> bool:
        if v is None or v == "":
            return True
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    retrieval_similarity_threshold: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        validation_alias="NEURALPAL_RETRIEVAL_SIMILARITY_THRESHOLD",
    )

    # 合规审查总开关：测试阶段可临时关闭（false=直接返回主模型草稿，不做审查与重写）
    compliance_review_enabled: bool = Field(
        default=True,
        validation_alias="NEURALPAL_COMPLIANCE_REVIEW_ENABLED",
    )

    @field_validator("compliance_review_enabled", mode="before")
    @classmethod
    def _coerce_compliance_review_enabled(cls, v: Any) -> bool:
        if v is None or v == "":
            return True
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    # --- Telegram Bot ---
    telegram_bot_token: str = Field(default="", validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_use_memory_orchestrator: bool = Field(
        default=True,
        validation_alias="NEURALPAL_TELEGRAM_USE_MEMORY_ORCH",
    )

    @field_validator("telegram_use_memory_orchestrator", mode="before")
    @classmethod
    def _coerce_telegram_use_memory_orch(cls, v: Any) -> bool:
        if v is None or v == "":
            return True
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    # --- Local Web Chat ---
    local_web_use_memory_orchestrator: bool = Field(
        default=True,
        validation_alias="NEURALPAL_LOCAL_USE_MEMORY_ORCH",
    )
    local_web_host: str = Field(
        default="127.0.0.1",
        validation_alias="NEURALPAL_LOCAL_WEB_HOST",
    )
    local_web_port: int = Field(
        default=8765,
        ge=1,
        le=65535,
        validation_alias="NEURALPAL_LOCAL_WEB_PORT",
    )
    obsidian_vault_path: Path | None = Field(
        default=None,
        validation_alias="NEURALPAL_OBSIDIAN_VAULT_PATH",
    )
    obsidian_memory_subdir: str = Field(
        default="NeuralPal/knowledge_palace",
        validation_alias="NEURALPAL_OBSIDIAN_MEMORY_SUBDIR",
    )
    memory_unify_obsidian: bool = Field(
        default=True,
        validation_alias="NEURALPAL_MEMORY_UNIFY_OBSIDIAN",
    )
    memory_maintenance_enabled: bool = Field(
        default=True,
        validation_alias="NEURALPAL_MEMORY_MAINTENANCE_ENABLED",
    )
    memory_maintenance_dry_run: bool = Field(
        default=False,
        validation_alias="NEURALPAL_MEMORY_MAINTENANCE_DRY_RUN",
    )
    memory_maintenance_interval_seconds: int = Field(
        default=600,
        ge=60,
        le=86400,
        validation_alias="NEURALPAL_MEMORY_MAINTENANCE_INTERVAL_SECONDS",
    )
    memory_tiered_pipeline_only: bool = Field(
        default=True,
        validation_alias="NEURALPAL_MEMORY_TIERED_PIPELINE",
    )

    @field_validator("memory_tiered_pipeline_only", mode="before")
    @classmethod
    def _coerce_memory_tiered_pipeline(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if v is None:
            return True
        return str(v).strip().lower() in ("1", "true", "yes", "on")
    @classmethod
    def _coerce_memory_unify_obsidian(cls, v: Any) -> bool:
        if v is None or v == "":
            return True
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    @field_validator("memory_maintenance_enabled", mode="before")
    @classmethod
    def _coerce_memory_maintenance_enabled(cls, v: Any) -> bool:
        if v is None or v == "":
            return True
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    @field_validator("memory_maintenance_dry_run", mode="before")
    @classmethod
    def _coerce_memory_maintenance_dry_run(cls, v: Any) -> bool:
        if v is None or v == "":
            return False
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    @field_validator("local_web_use_memory_orchestrator", mode="before")
    @classmethod
    def _coerce_local_use_memory_orch(cls, v: Any) -> bool:
        if v is None or v == "":
            return True
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    @field_validator("obsidian_vault_path", mode="before")
    @classmethod
    def _resolve_obsidian_vault_path(cls, v: Any) -> Path | None:
        if v is None or v == "":
            return None
        p = Path(v).expanduser() if not isinstance(v, Path) else v.expanduser()
        if not p.is_absolute():
            p = _project_root() / p
        return p

    @field_validator("obsidian_memory_subdir", mode="before")
    @classmethod
    def _normalize_obsidian_subdir(cls, v: Any) -> str:
        if v is None:
            return "NeuralPal/knowledge_palace"
        return str(v).strip().strip("/")

    # --- Desktop App Chat ---
    desktop_use_memory_orchestrator: bool = Field(
        default=True,
        validation_alias="NEURALPAL_DESKTOP_USE_MEMORY_ORCH",
    )

    @field_validator("desktop_use_memory_orchestrator", mode="before")
    @classmethod
    def _coerce_desktop_use_memory_orch(cls, v: Any) -> bool:
        if v is None or v == "":
            return True
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    # --- Desktop update reminder ---
    desktop_update_check_enabled: bool = Field(
        default=True,
        validation_alias="NEURALPAL_DESKTOP_UPDATE_CHECK_ENABLED",
    )
    desktop_update_check_interval_seconds: int = Field(
        default=3600,
        ge=300,
        le=86400,
        validation_alias="NEURALPAL_DESKTOP_UPDATE_CHECK_INTERVAL_SECONDS",
    )
    desktop_update_git_remote: str = Field(
        default="origin",
        validation_alias="NEURALPAL_UPDATE_GIT_REMOTE",
    )
    desktop_update_git_branch: str = Field(
        default="",
        validation_alias="NEURALPAL_UPDATE_GIT_BRANCH",
    )
    desktop_update_script: Path = Field(
        default_factory=lambda: _project_root() / "scripts" / "restart_desktop_app.sh",
        validation_alias="NEURALPAL_DESKTOP_UPDATE_SCRIPT",
    )
    desktop_update_state_path: Path = Field(
        default_factory=lambda: _project_root() / "data" / "desktop_update_state.json",
        validation_alias="NEURALPAL_DESKTOP_UPDATE_STATE_PATH",
    )

    @field_validator("desktop_update_check_enabled", mode="before")
    @classmethod
    def _coerce_desktop_update_check_enabled(cls, v: Any) -> bool:
        if v is None or v == "":
            return True
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    @field_validator("desktop_update_script", mode="before")
    @classmethod
    def _resolve_desktop_update_script(cls, v: Any) -> Path:
        if v is None or v == "":
            return _project_root() / "scripts" / "restart_desktop_app.sh"
        p = Path(v).expanduser() if not isinstance(v, Path) else v.expanduser()
        if not p.is_absolute():
            p = _project_root() / p
        return p

    @field_validator("desktop_update_state_path", mode="before")
    @classmethod
    def _resolve_desktop_update_state_path(cls, v: Any) -> Path:
        if v is None or v == "":
            return _project_root() / "data" / "desktop_update_state.json"
        p = Path(v).expanduser() if not isinstance(v, Path) else v.expanduser()
        if not p.is_absolute():
            p = _project_root() / p
        return p

    # --- Desktop chat background ---
    chat_background_enabled: bool = Field(
        default=False,
        validation_alias="NEURALPAL_CHAT_BACKGROUND_ENABLED",
    )
    chat_background_provider: str = Field(
        default="pexels",
        validation_alias="NEURALPAL_CHAT_BACKGROUND_PROVIDER",
    )
    chat_background_rotate_hours: int = Field(
        default=12,
        ge=1,
        le=168,
        validation_alias="NEURALPAL_CHAT_BACKGROUND_ROTATE_HOURS",
    )
    chat_background_min_width: int = Field(
        default=1600,
        ge=640,
        validation_alias="NEURALPAL_CHAT_BACKGROUND_MIN_WIDTH",
    )
    chat_background_min_height: int = Field(
        default=900,
        ge=360,
        validation_alias="NEURALPAL_CHAT_BACKGROUND_MIN_HEIGHT",
    )
    chat_background_min_candidates: int = Field(
        default=20,
        ge=1,
        le=200,
        validation_alias="NEURALPAL_CHAT_BACKGROUND_MIN_CANDIDATES",
    )
    chat_background_refill_threshold: int = Field(
        default=10,
        ge=1,
        le=200,
        validation_alias="NEURALPAL_CHAT_BACKGROUND_REFILL_THRESHOLD",
    )
    chat_background_overlay_opacity: float = Field(
        default=0.45,
        ge=0.0,
        le=1.0,
        validation_alias="NEURALPAL_CHAT_BACKGROUND_OVERLAY_OPACITY",
    )
    chat_background_cache_images: bool = Field(
        default=False,
        validation_alias="NEURALPAL_CHAT_BACKGROUND_CACHE_IMAGES",
    )
    pexels_api_key: str = Field(default="", validation_alias="PEXELS_API_KEY")

    @field_validator("chat_background_enabled", "chat_background_cache_images", mode="before")
    @classmethod
    def _coerce_chat_background_flags(cls, v: Any) -> bool:
        if v is None or v == "":
            return False
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    # --- 可选提醒插件（默认关闭：不加载工具、不启调度器）---
    reminder_enabled: bool = Field(default=False, validation_alias="NEURALPAL_REMINDER_ENABLED")

    @field_validator("reminder_enabled", mode="before")
    @classmethod
    def _coerce_reminder_enabled(cls, v: Any) -> bool:
        if v is None or v == "":
            return False
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    reminder_json_path: Path = Field(
        default_factory=lambda: _project_root() / "data" / "neuralpal_reminders.json",
        validation_alias="NEURALPAL_REMINDER_JSON_PATH",
    )

    reminder_scheduler_interval_seconds: int = Field(
        default=60,
        ge=10,
        le=3600,
        validation_alias="NEURALPAL_REMINDER_SCHEDULER_INTERVAL_SECONDS",
    )
    desktop_reminder_sound_lead_seconds: float = Field(
        default=5.0,
        ge=1.0,
        le=120.0,
        validation_alias="NEURALPAL_DESKTOP_REMINDER_SOUND_LEAD_SECONDS",
    )

    # --- 沈昼 · 本机/网页代办（Computer Use）---
    agent_enabled: bool = Field(default=True, validation_alias="NEURALPAL_AGENT_ENABLED")
    agent_mock_mode: bool = Field(default=False, validation_alias="NEURALPAL_AGENT_MOCK_MODE")
    agent_max_steps: int = Field(default=20, ge=1, le=50, validation_alias="NEURALPAL_AGENT_MAX_STEPS")
    agent_claude_model: str = Field(default="", validation_alias="NEURALPAL_AGENT_CLAUDE_MODEL")
    agent_claude_max_tokens: int = Field(
        default=4096,
        ge=256,
        le=8192,
        validation_alias="NEURALPAL_AGENT_CLAUDE_MAX_TOKENS",
    )
    agent_openai_model: str = Field(
        default="computer-use-preview",
        validation_alias="NEURALPAL_AGENT_OPENAI_MODEL",
    )
    agent_state_dir: Path = Field(
        default_factory=lambda: _project_root() / "data" / "agent_sessions",
        validation_alias="NEURALPAL_AGENT_STATE_DIR",
    )
    agent_allow_terminal: bool = Field(
        default=False,
        validation_alias="NEURALPAL_ALLOW_TERMINAL_AGENT",
    )

    @field_validator("agent_enabled", mode="before")
    @classmethod
    def _coerce_agent_enabled(cls, v: Any) -> bool:
        if v is None or v == "":
            return True
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    @field_validator("agent_mock_mode", mode="before")
    @classmethod
    def _coerce_agent_mock_mode(cls, v: Any) -> bool:
        if v is None or v == "":
            return False
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    @field_validator("agent_state_dir", mode="before")
    @classmethod
    def _resolve_agent_state_dir(cls, v: Any) -> Path:
        if v is None or v == "":
            return _project_root() / "data" / "agent_sessions"
        return Path(v).expanduser()

    @field_validator("agent_allow_terminal", mode="before")
    @classmethod
    def _coerce_agent_allow_terminal(cls, v: Any) -> bool:
        if v is None or v == "":
            return False
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    schedule_validator_enabled: bool = Field(
        default=True,
        validation_alias="NEURALPAL_SCHEDULE_VALIDATOR_ENABLED",
    )
    schedule_auto_repair_enabled: bool = Field(
        default=True,
        validation_alias="NEURALPAL_SCHEDULE_AUTO_REPAIR_ENABLED",
    )
    schedule_personalized_energy_enabled: bool = Field(
        default=True,
        validation_alias="NEURALPAL_SCHEDULE_PERSONALIZED_ENERGY_ENABLED",
    )
    schedule_review_enabled: bool = Field(
        default=True,
        validation_alias="NEURALPAL_SCHEDULE_REVIEW_ENABLED",
    )
    schedule_habit_suggestions_enabled: bool = Field(
        default=False,
        validation_alias="NEURALPAL_SCHEDULE_HABIT_SUGGESTIONS_ENABLED",
    )

    # Telegram 用户时区（用于午夜短期记忆按本地日历日重置；与提醒插件解耦）
    telegram_timezone_store_path: Path = Field(
        default_factory=lambda: _project_root() / "data" / "telegram_chat_timezones.json",
        validation_alias="NEURALPAL_TELEGRAM_TZ_STORE_PATH",
    )

    @field_validator("reminder_json_path", mode="before")
    @classmethod
    def _resolve_reminder_json(cls, v: Any) -> Path:
        if v is None or v == "":
            return _project_root() / "data" / "neuralpal_reminders.json"
        p = Path(v).expanduser() if not isinstance(v, Path) else v.expanduser()
        if not p.is_absolute():
            p = _project_root() / p
        return p

    @field_validator("telegram_timezone_store_path", mode="before")
    @classmethod
    def _resolve_telegram_tz_store(cls, v: Any) -> Path:
        if v is None or v == "":
            return _project_root() / "data" / "telegram_chat_timezones.json"
        p = Path(v).expanduser() if not isinstance(v, Path) else v.expanduser()
        if not p.is_absolute():
            p = _project_root() / p
        return p

    # 为 false 时：不进行「第 N+1 轮触发、先归档最旧一轮」的滚动裁剪（短期记忆列表会持续增长至进程结束）
    memory_auto_archive_enabled: bool = Field(
        default=True,
        validation_alias="NEURALPAL_MEMORY_AUTO_ARCHIVE",
    )

    @field_validator("memory_auto_archive_enabled", mode="before")
    @classmethod
    def _coerce_memory_auto_archive(cls, v: Any) -> bool:
        if v is None or v == "":
            return True
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    # knowledge_palace：长期文本记忆根目录（与 Chroma 向量一一对应）
    knowledge_palace_root: Path = Field(
        default_factory=lambda: _project_root() / "knowledge_palace",
        validation_alias="NEURALPAL_KNOWLEDGE_PALACE",
    )

    # 长期记忆专用 Chroma 持久化目录（海马体向量索引，与 data/chroma_db 分离）
    long_term_memory_chroma_path: Path = Field(
        default_factory=lambda: _project_root() / "neuralpal_memory_db",
        validation_alias="NEURALPAL_LONG_TERM_CHROMA_PATH",
    )

    @field_validator("knowledge_palace_root", mode="before")
    @classmethod
    def _resolve_knowledge_palace(cls, v: Any) -> Path:
        if v is None or v == "":
            return _project_root() / "knowledge_palace"
        p = Path(v).expanduser() if not isinstance(v, Path) else v.expanduser()
        if not p.is_absolute():
            p = _project_root() / p
        return p

    @field_validator("long_term_memory_chroma_path", mode="before")
    @classmethod
    def _resolve_long_term_chroma(cls, v: Any) -> Path:
        if v is None or v == "":
            return _project_root() / "neuralpal_memory_db"
        p = Path(v).expanduser() if not isinstance(v, Path) else v.expanduser()
        if not p.is_absolute():
            p = _project_root() / p
        return p

    @field_validator("chroma_persist_path", mode="before")
    @classmethod
    def _resolve_chroma_path(cls, v: Any) -> Path:
        if v is None or v == "":
            return _project_root() / "data" / "chroma_db"
        p = Path(v).expanduser()
        if not p.is_absolute():
            p = _project_root() / p
        return p

    # --- 杂志情报主动聊天系统（Magazine Intelligence Proactive Chat）---
    magazine_intel_enabled: bool = Field(
        default=False, validation_alias="NEURALPAL_MAGAZINE_INTEL_ENABLED"
    )

    @field_validator("magazine_intel_enabled", mode="before")
    @classmethod
    def _coerce_magazine_intel_enabled(cls, v: Any) -> bool:
        if v is None or v == "":
            return False
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    magazine_intel_timezone: str = Field(
        default="America/New_York",
        validation_alias="NEURALPAL_MAGAZINE_INTEL_TIMEZONE",
    )

    magazine_intel_chat_id: str = Field(
        default="", validation_alias="NEURALPAL_MAGAZINE_INTEL_CHAT_ID"
    )

    magazine_intel_reserve_dir: str = Field(
        default="",
        validation_alias="NEURALPAL_MAGAZINE_INTEL_RESERVE_DIR",
    )

    magazine_intel_dnd_start: str = Field(
        default="18:00", validation_alias="NEURALPAL_MAGAZINE_INTEL_DND_START"
    )

    magazine_intel_dnd_end: str = Field(
        default="07:00", validation_alias="NEURALPAL_MAGAZINE_INTEL_DND_END"
    )

    magazine_intel_daily_max: int = Field(
        default=1, ge=1, le=5, validation_alias="NEURALPAL_MAGAZINE_INTEL_DAILY_MAX"
    )
    magazine_intel_source_groups: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "magazine",
            "fintech",
            "venture",
            "policy",
            "investment",
            "payments",
        ],
        validation_alias="NEURALPAL_MAGAZINE_INTEL_SOURCE_GROUPS",
    )
    magazine_intel_region_focus: str = Field(
        default="US",
        validation_alias="NEURALPAL_MAGAZINE_INTEL_REGION_FOCUS",
    )
    magazine_intel_min_score: float = Field(
        default=70.0,
        ge=0.0,
        le=100.0,
        validation_alias="NEURALPAL_MAGAZINE_INTEL_MIN_SCORE",
    )
    magazine_intel_include_official: bool = Field(
        default=True,
        validation_alias="NEURALPAL_MAGAZINE_INTEL_INCLUDE_OFFICIAL",
    )
    magazine_intel_include_startup_funding: bool = Field(
        default=True,
        validation_alias="NEURALPAL_MAGAZINE_INTEL_INCLUDE_STARTUP_FUNDING",
    )

    # --- Magazine TTS（ElevenLabs）---
    magazine_tts_enabled: bool = Field(
        default=False,
        validation_alias="NEURALPAL_MAGAZINE_TTS_ENABLED",
    )
    magazine_tts_chunk_chars: int = Field(
        default=160,
        ge=40,
        le=500,
        validation_alias="NEURALPAL_MAGAZINE_TTS_CHUNK_CHARS",
    )
    magazine_tts_cache_dir: Path = Field(
        default_factory=lambda: _project_root() / "data" / "magazine_tts_cache",
        validation_alias="NEURALPAL_MAGAZINE_TTS_CACHE_DIR",
    )

    elevenlabs_api_key: str = Field(default="", validation_alias="ELEVENLABS_API_KEY")
    elevenlabs_voice_id: str = Field(default="", validation_alias="ELEVENLABS_VOICE_ID")
    elevenlabs_model_id: str = Field(
        default="eleven_multilingual_v2",
        validation_alias="ELEVENLABS_MODEL_ID",
    )
    elevenlabs_api_url: str = Field(
        default="https://api.elevenlabs.io/v1/text-to-speech",
        validation_alias="ELEVENLABS_API_URL",
    )
    elevenlabs_output_format: str = Field(
        default="mp3_44100_128",
        validation_alias="ELEVENLABS_OUTPUT_FORMAT",
    )
    elevenlabs_stability: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        validation_alias="ELEVENLABS_STABILITY",
    )
    elevenlabs_similarity_boost: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        validation_alias="ELEVENLABS_SIMILARITY_BOOST",
    )
    elevenlabs_style: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        validation_alias="ELEVENLABS_STYLE",
    )
    elevenlabs_use_speaker_boost: bool = Field(
        default=True,
        validation_alias="ELEVENLABS_USE_SPEAKER_BOOST",
    )
    elevenlabs_speed: float = Field(
        default=1.15,
        ge=0.7,
        le=1.2,
        validation_alias="ELEVENLABS_SPEED",
    )
    elevenlabs_timeout_seconds: int = Field(
        default=35,
        ge=5,
        le=120,
        validation_alias="ELEVENLABS_TIMEOUT_SECONDS",
    )

    # --- Desktop reply auto TTS ---
    reply_tts_enabled: bool = Field(
        default=True,
        validation_alias="NEURALPAL_REPLY_TTS_ENABLED",
    )
    reply_tts_chunk_chars: int = Field(
        default=180,
        ge=40,
        le=500,
        validation_alias="NEURALPAL_REPLY_TTS_CHUNK_CHARS",
    )
    reply_tts_cache_dir: Path = Field(
        default_factory=lambda: _project_root() / "data" / "reply_tts_cache",
        validation_alias="NEURALPAL_REPLY_TTS_CACHE_DIR",
    )

    # --- Desktop voice dialog (wake word + VAD + STT) ---
    voice_dialog_enabled: bool = Field(
        default=False,
        validation_alias="NEURALPAL_VOICE_DIALOG_ENABLED",
    )
    voice_wake_phrases: str = Field(
        default="在不,再不,仔不",
        validation_alias="NEURALPAL_VOICE_WAKE_PHRASES",
    )
    voice_silence_seconds: float = Field(
        default=1.2,
        ge=0.5,
        le=6.0,
        validation_alias="NEURALPAL_VOICE_SILENCE_SECONDS",
    )
    voice_min_speech_seconds: float = Field(
        default=0.4,
        ge=0.1,
        le=3.0,
        validation_alias="NEURALPAL_VOICE_MIN_SPEECH_SECONDS",
    )
    voice_wake_timeout_seconds: float = Field(
        default=8.0,
        ge=2.0,
        le=30.0,
        validation_alias="NEURALPAL_VOICE_WAKE_TIMEOUT_SECONDS",
    )
    voice_followup_seconds: float = Field(
        default=30.0,
        ge=5.0,
        le=180.0,
        validation_alias="NEURALPAL_VOICE_FOLLOWUP_SECONDS",
    )
    voice_wake_max_seconds: float = Field(
        default=2.5,
        ge=0.8,
        le=6.0,
        validation_alias="NEURALPAL_VOICE_WAKE_MAX_SECONDS",
    )
    voice_wake_stt_max_seconds: float = Field(
        default=4.0,
        ge=2.0,
        le=20.0,
        validation_alias="NEURALPAL_VOICE_WAKE_STT_MAX_SECONDS",
    )
    voice_wake_silence_seconds: float = Field(
        default=0.7,
        ge=0.3,
        le=2.0,
        validation_alias="NEURALPAL_VOICE_WAKE_SILENCE_SECONDS",
    )
    voice_stt_api_key: str = Field(default="", validation_alias="NEURALPAL_VOICE_STT_API_KEY")
    voice_stt_provider: str = Field(
        default="local",
        validation_alias="NEURALPAL_VOICE_STT_PROVIDER",
    )
    voice_stt_model: str = Field(default="base", validation_alias="NEURALPAL_VOICE_STT_MODEL")
    voice_stt_local_model: str = Field(default="base", validation_alias="NEURALPAL_VOICE_STT_LOCAL_MODEL")
    voice_stt_language: str = Field(default="zh", validation_alias="NEURALPAL_VOICE_STT_LANGUAGE")
    voice_stt_timeout_seconds: int = Field(
        default=45,
        ge=10,
        le=120,
        validation_alias="NEURALPAL_VOICE_STT_TIMEOUT_SECONDS",
    )
    voice_stt_elevenlabs_api_url: str = Field(
        default="https://api.elevenlabs.io/v1/speech-to-text",
        validation_alias="NEURALPAL_VOICE_STT_ELEVENLABS_API_URL",
    )

    @field_validator("voice_dialog_enabled", mode="before")
    @classmethod
    def _coerce_voice_dialog_enabled(cls, v: Any) -> bool:
        if v is None or v == "":
            return False
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    @field_validator("magazine_tts_enabled", mode="before")
    @classmethod
    def _coerce_magazine_tts_enabled(cls, v: Any) -> bool:
        if v is None or v == "":
            return False
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    @field_validator("magazine_intel_source_groups", mode="before")
    @classmethod
    def _coerce_magazine_source_groups(cls, v: Any) -> list[str]:
        default = ["magazine", "fintech", "venture", "policy", "investment", "payments"]
        if v is None or v == "":
            return default
        if isinstance(v, str):
            raw = [p.strip().lower() for p in v.split(",")]
        elif isinstance(v, (list, tuple, set)):
            raw = [str(p).strip().lower() for p in v]
        else:
            return default
        out: list[str] = []
        for g in raw:
            if not g:
                continue
            if g not in out:
                out.append(g)
        return out or default

    @field_validator(
        "magazine_intel_include_official",
        "magazine_intel_include_startup_funding",
        mode="before",
    )
    @classmethod
    def _coerce_magazine_bool_flags(cls, v: Any) -> bool:
        if v is None or v == "":
            return True
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    @field_validator("magazine_tts_cache_dir", mode="before")
    @classmethod
    def _resolve_magazine_tts_cache_dir(cls, v: Any) -> Path:
        if v is None or v == "":
            return _project_root() / "data" / "magazine_tts_cache"
        p = Path(v).expanduser() if not isinstance(v, Path) else v.expanduser()
        if not p.is_absolute():
            p = _project_root() / p
        return p

    @field_validator("reply_tts_enabled", mode="before")
    @classmethod
    def _coerce_reply_tts_enabled(cls, v: Any) -> bool:
        if v is None or v == "":
            return True
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    @field_validator("elevenlabs_use_speaker_boost", mode="before")
    @classmethod
    def _coerce_elevenlabs_use_speaker_boost(cls, v: Any) -> bool:
        if v is None or v == "":
            return True
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    @field_validator("reply_tts_cache_dir", mode="before")
    @classmethod
    def _resolve_reply_tts_cache_dir(cls, v: Any) -> Path:
        if v is None or v == "":
            return _project_root() / "data" / "reply_tts_cache"
        p = Path(v).expanduser() if not isinstance(v, Path) else v.expanduser()
        if not p.is_absolute():
            p = _project_root() / p
        return p

    # --- AI 伴侣话题雷达 Topic Radar ---
    topic_radar_enabled: bool = Field(
        default=False,
        validation_alias="TOPIC_RADAR_ENABLED",
    )

    @field_validator("topic_radar_enabled", mode="before")
    @classmethod
    def _coerce_topic_radar_enabled(cls, v: Any) -> bool:
        if v is None or v == "":
            return False
        if isinstance(v, bool):
            return v
        return str(v).strip().lower() in ("1", "true", "yes", "on")

    topic_radar_ark_api_key: str = Field(default="", validation_alias="ARK_API_KEY")
    topic_radar_ark_base_url: str = Field(
        default="",
        validation_alias="ARK_BASE_URL",
    )
    topic_radar_doubao_model_id: str = Field(default="", validation_alias="DOUBAO_MODEL_ID")
    topic_radar_claude_model_id: str = Field(default="", validation_alias="CLAUDE_MODEL_ID")
    topic_radar_claude_web_search_tool_version: str = Field(
        default="web_search_20250305",
        validation_alias="CLAUDE_WEB_SEARCH_TOOL_VERSION",
    )
    topic_radar_claude_web_search_max_uses: int = Field(
        default=3,
        ge=1,
        le=10,
        validation_alias="CLAUDE_WEB_SEARCH_MAX_USES",
    )
    topic_radar_db_path: Path = Field(
        default_factory=lambda: _project_root() / "data" / "topic_radar.db",
        validation_alias="TOPIC_RADAR_DB_PATH",
    )
    topic_radar_daily_max_categories: int = Field(
        default=3,
        ge=1,
        le=5,
        validation_alias="TOPIC_RADAR_DAILY_MAX_CATEGORIES",
    )
    topic_radar_max_targets_per_category: int = Field(
        default=3,
        ge=1,
        le=5,
        validation_alias="TOPIC_RADAR_MAX_TARGETS_PER_CATEGORY",
    )
    topic_radar_max_saved_seeds_per_run: int = Field(
        default=3,
        ge=1,
        le=10,
        validation_alias="TOPIC_RADAR_MAX_SAVED_SEEDS_PER_RUN",
    )
    topic_radar_min_score: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        validation_alias="TOPIC_RADAR_MIN_SCORE",
    )
    topic_radar_skip_if_available_seeds_gte: int = Field(
        default=6,
        ge=1,
        validation_alias="TOPIC_RADAR_SKIP_IF_AVAILABLE_SEEDS_GTE",
    )
    topic_radar_proactive_cooldown_hours: int = Field(
        default=12,
        ge=1,
        validation_alias="TOPIC_RADAR_PROACTIVE_COOLDOWN_HOURS",
    )
    topic_radar_max_proactive_seeds_per_conversation: int = Field(
        default=1,
        ge=1,
        validation_alias="TOPIC_RADAR_MAX_PROACTIVE_SEEDS_PER_CONVERSATION",
    )
    topic_radar_default_timezone: str = Field(
        default="America/New_York",
        validation_alias="TOPIC_RADAR_DEFAULT_TIMEZONE",
    )
    topic_radar_api_timeout_seconds: float = Field(
        default=120.0,
        ge=10.0,
        validation_alias="TOPIC_RADAR_API_TIMEOUT_SECONDS",
    )

    @field_validator("topic_radar_db_path", mode="before")
    @classmethod
    def _resolve_topic_radar_db(cls, v: Any) -> Path:
        if v is None or v == "":
            return _project_root() / "data" / "topic_radar.db"
        p = Path(v).expanduser() if not isinstance(v, Path) else v.expanduser()
        if not p.is_absolute():
            p = _project_root() / p
        return p

    # --- Companion Life Engine ---
    companion_life_enabled: bool = Field(
        default=True,
        validation_alias="COMPANION_LIFE_ENABLED",
    )

    @field_validator("companion_life_enabled", mode="before")
    @classmethod
    def _coerce_companion_life_enabled(cls, v: Any) -> bool:
        if v is None or v == "":
            return True
        if isinstance(v, bool):
            return v
        return str(v).strip().lower() in ("1", "true", "yes", "on")

    companion_life_intent_llm_enabled: bool = Field(
        default=True,
        validation_alias="COMPANION_LIFE_INTENT_LLM_ENABLED",
    )

    @field_validator("companion_life_intent_llm_enabled", mode="before")
    @classmethod
    def _coerce_companion_life_intent_llm_enabled(cls, v: Any) -> bool:
        if v is None or v == "":
            return True
        if isinstance(v, bool):
            return v
        return str(v).strip().lower() in ("1", "true", "yes", "on")

    companion_life_intent_doubao_model_id: str = Field(
        default="",
        validation_alias="COMPANION_LIFE_INTENT_DOUBAO_MODEL_ID",
    )
    companion_life_intent_api_timeout_seconds: float = Field(
        default=20.0,
        ge=5.0,
        le=120.0,
        validation_alias="COMPANION_LIFE_INTENT_API_TIMEOUT_SECONDS",
    )

    neuralpal_dev_context_status_enabled: bool = Field(
        default=False,
        validation_alias="NEURALPAL_DEV_CONTEXT_STATUS_ENABLED",
    )

    @field_validator("neuralpal_dev_context_status_enabled", mode="before")
    @classmethod
    def _coerce_dev_context_status_enabled(cls, v: Any) -> bool:
        if v is None or v == "":
            return False
        if isinstance(v, bool):
            return v
        return str(v).strip().lower() in ("1", "true", "yes", "on")

    companion_life_obsidian_mirror_enabled: bool = Field(
        default=True,
        validation_alias="COMPANION_LIFE_OBSIDIAN_MIRROR_ENABLED",
    )
    companion_life_obsidian_vault_path: Path | None = Field(
        default=None,
        validation_alias="COMPANION_LIFE_OBSIDIAN_VAULT_PATH",
    )
    companion_life_obsidian_subdir: str = Field(
        default="数字生命日记库",
        validation_alias="COMPANION_LIFE_OBSIDIAN_SUBDIR",
    )
    companion_life_default_timezone: str = Field(
        default="America/New_York",
        validation_alias="COMPANION_LIFE_DEFAULT_TIMEZONE",
    )  # TODO: wire into scheduled daily run when APScheduler hook is added
    companion_life_db_path: Path = Field(
        default_factory=lambda: _project_root() / "data" / "companion_life.db",
        validation_alias="COMPANION_LIFE_DB_PATH",
    )
    companion_life_chroma_path: Path = Field(
        default_factory=lambda: _project_root() / "data" / "companion_life_chroma",
        validation_alias="COMPANION_LIFE_CHROMA_PATH",
    )
    companion_life_active_day_min_events: int = Field(
        default=1,
        ge=0,
        le=8,
        validation_alias="COMPANION_LIFE_ACTIVE_DAY_MIN_EVENTS",
    )
    companion_life_active_day_max_events: int = Field(
        default=4,
        ge=1,
        le=8,
        validation_alias="COMPANION_LIFE_ACTIVE_DAY_MAX_EVENTS",
    )
    companion_life_quiet_day_event_probability: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        validation_alias="COMPANION_LIFE_QUIET_DAY_EVENT_PROBABILITY",
    )
    companion_life_quiet_day_max_events: int = Field(
        default=1,
        ge=0,
        le=4,
        validation_alias="COMPANION_LIFE_QUIET_DAY_MAX_EVENTS",
    )
    companion_life_min_event_score: float = Field(
        default=0.62,
        ge=0.0,
        le=1.0,
        validation_alias="COMPANION_LIFE_MIN_EVENT_SCORE",
    )
    companion_life_max_chat_snippets_per_day: int = Field(
        default=2,
        ge=0,
        le=5,
        validation_alias="COMPANION_LIFE_MAX_CHAT_SNIPPETS_PER_DAY",
    )
    companion_life_max_proactive_snippets_per_conversation: int = Field(
        default=1,
        ge=0,
        le=3,
        validation_alias="COMPANION_LIFE_MAX_PROACTIVE_SNIPPETS_PER_CONVERSATION",
    )  # TODO: wire into life_context_builder proactive gating
    companion_life_proactive_cooldown_hours: int = Field(
        default=12,
        ge=1,
        validation_alias="COMPANION_LIFE_PROACTIVE_COOLDOWN_HOURS",
    )  # TODO: wire into life_context_builder proactive gating
    companion_life_avoid_same_category_days: int = Field(
        default=3,
        ge=1,
        validation_alias="COMPANION_LIFE_AVOID_SAME_CATEGORY_DAYS",
    )  # TODO: wire into life_event_ranker dedup window
    companion_life_daily_run_hour: int = Field(
        default=0,
        ge=0,
        le=23,
        validation_alias="COMPANION_LIFE_DAILY_RUN_HOUR",
    )  # TODO: wire into scheduled daily run when APScheduler hook is added
    companion_life_daily_run_minute: int = Field(
        default=15,
        ge=0,
        le=59,
        validation_alias="COMPANION_LIFE_DAILY_RUN_MINUTE",
    )  # TODO: wire into scheduled daily run when APScheduler hook is added
    companion_life_vector_index_enabled: bool = Field(default=True)
    companion_life_vector_min_importance: float = Field(default=0.70, ge=0.0, le=1.0)
    companion_life_vector_min_chat_value: float = Field(default=0.75, ge=0.0, le=1.0)
    companion_life_topic_radar_enabled: bool = Field(default=True)
    companion_life_topic_radar_external_source_max: int = Field(default=3, ge=0, le=10)
    companion_life_log_level: str = Field(
        default="INFO",
        validation_alias="COMPANION_LIFE_LOG_LEVEL",
    )  # TODO: configure companion_life module logging

    @field_validator("companion_life_default_timezone", mode="before")
    @classmethod
    def _validate_companion_life_timezone(cls, v: Any) -> str:
        tz = str(v or "America/New_York").strip() or "America/New_York"
        try:
            from zoneinfo import ZoneInfo

            ZoneInfo(tz)
            return tz
        except Exception:
            return "America/New_York"

    @model_validator(mode="after")
    def _validate_companion_life_bounds(self) -> "Settings":
        if self.companion_life_active_day_min_events > self.companion_life_active_day_max_events:
            raise ValueError(
                "COMPANION_LIFE_ACTIVE_DAY_MIN_EVENTS must be <= "
                "COMPANION_LIFE_ACTIVE_DAY_MAX_EVENTS"
            )
        return self

    @field_validator("companion_life_db_path", mode="before")
    @classmethod
    def _resolve_companion_life_db(cls, v: Any) -> Path:
        if v is None or v == "":
            return _project_root() / "data" / "companion_life.db"
        p = Path(v).expanduser() if not isinstance(v, Path) else v.expanduser()
        if not p.is_absolute():
            p = _project_root() / p
        return p

    @field_validator("companion_life_chroma_path", mode="before")
    @classmethod
    def _resolve_companion_life_chroma(cls, v: Any) -> Path:
        if v is None or v == "":
            return _project_root() / "data" / "companion_life_chroma"
        p = Path(v).expanduser() if not isinstance(v, Path) else v.expanduser()
        if not p.is_absolute():
            p = _project_root() / p
        return p

    @field_validator("companion_life_obsidian_vault_path", mode="before")
    @classmethod
    def _resolve_companion_life_obsidian_vault(cls, v: Any) -> Path | None:
        if v is None or v == "":
            return None
        p = Path(v).expanduser() if not isinstance(v, Path) else v.expanduser()
        if not p.is_absolute():
            p = _project_root() / p
        return p

    # --- 沈昼世界引擎集成（shenzhou-world）---
    shenzhou_integration_enabled: bool = Field(
        default=True,
        validation_alias="SHENZHOU_INTEGRATION_ENABLED",
    )
    shenzhou_scheduler_enabled: bool = Field(
        default=True,
        validation_alias="SHENZHOU_SCHEDULER_ENABLED",
    )
    shenzhou_world_api_url: str = Field(
        default="http://127.0.0.1:3000",
        validation_alias="SHENZHOU_WORLD_API_URL",
    )
    shenzhou_internal_token: str = Field(
        default="",
        validation_alias="SHENZHOU_INTERNAL_TOKEN",
    )
    shenzhou_user_entity_slug: str = Field(
        default="dai-jinxin",
        validation_alias="SHENZHOU_USER_ENTITY_SLUG",
    )
    shenzhou_user_display_name: str = Field(
        default="戴金鑫",
        validation_alias="SHENZHOU_USER_DISPLAY_NAME",
    )
    shenzhou_default_session_id: str = Field(
        default_factory=_default_shenzhou_session_id,
        validation_alias="SHENZHOU_DEFAULT_SESSION_ID",
    )
    shenzhou_timezone: str = Field(
        default="Asia/Shanghai",
        validation_alias="SHENZHOU_TIMEZONE",
    )
    shenzhou_sync_hour: int = Field(default=23, ge=0, le=23, validation_alias="SHENZHOU_SYNC_HOUR")
    shenzhou_sync_minute: int = Field(default=59, ge=0, le=59, validation_alias="SHENZHOU_SYNC_MINUTE")
    shenzhou_pipeline_hour: int = Field(default=0, ge=0, le=23, validation_alias="SHENZHOU_PIPELINE_HOUR")
    shenzhou_pipeline_minute: int = Field(default=5, ge=0, le=59, validation_alias="SHENZHOU_PIPELINE_MINUTE")
    shenzhou_pull_hour: int = Field(default=0, ge=0, le=23, validation_alias="SHENZHOU_PULL_HOUR")
    shenzhou_pull_minute: int = Field(default=15, ge=0, le=59, validation_alias="SHENZHOU_PULL_MINUTE")
    shenzhou_api_timeout_seconds: float = Field(
        default=60.0,
        ge=5.0,
        le=600.0,
        validation_alias="SHENZHOU_API_TIMEOUT_SECONDS",
    )
    shenzhou_proactive_life_context: bool = Field(
        default=False,
        validation_alias="SHENZHOU_PROACTIVE_LIFE_CONTEXT",
    )
    shenzhou_proactive_message_enabled: bool = Field(
        default=True,
        validation_alias="SHENZHOU_PROACTIVE_MESSAGE_ENABLED",
    )
    shenzhou_proactive_check_interval_minutes: int = Field(
        default=5,
        ge=1,
        le=120,
        validation_alias="SHENZHOU_PROACTIVE_CHECK_INTERVAL_MINUTES",
    )
    shenzhou_proactive_daily_max: int = Field(
        default=3,
        ge=0,
        le=20,
        validation_alias="SHENZHOU_PROACTIVE_DAILY_MAX",
    )
    shenzhou_proactive_event_cooldown_minutes: int = Field(
        default=360,
        ge=10,
        le=10080,
        validation_alias="SHENZHOU_PROACTIVE_EVENT_COOLDOWN_MINUTES",
    )
    shenzhou_proactive_lead_minutes: int = Field(
        default=60,
        ge=0,
        le=720,
        validation_alias="SHENZHOU_PROACTIVE_LEAD_MINUTES",
    )
    shenzhou_proactive_lag_minutes: int = Field(
        default=120,
        ge=0,
        le=1440,
        validation_alias="SHENZHOU_PROACTIVE_LAG_MINUTES",
    )
    shenzhou_proactive_quiet_start_hour: int = Field(
        default=23,
        ge=0,
        le=23,
        validation_alias="SHENZHOU_PROACTIVE_QUIET_START_HOUR",
    )
    shenzhou_proactive_quiet_end_hour: int = Field(
        default=8,
        ge=0,
        le=23,
        validation_alias="SHENZHOU_PROACTIVE_QUIET_END_HOUR",
    )
    shenzhou_proactive_channels: str = Field(
        default="in_app",
        validation_alias="SHENZHOU_PROACTIVE_CHANNELS",
    )
    shenzhou_proactive_session_id: str = Field(
        default="",
        validation_alias="SHENZHOU_PROACTIVE_SESSION_ID",
    )
    shenzhou_proactive_telegram_chat_id: str = Field(
        default="",
        validation_alias="SHENZHOU_PROACTIVE_TELEGRAM_CHAT_ID",
    )
    shenzhou_proactive_webhook_url: str = Field(
        default="",
        validation_alias="SHENZHOU_PROACTIVE_WEBHOOK_URL",
    )
    shenzhou_context_archive_enabled: bool = Field(
        default=True,
        validation_alias="SHENZHOU_CONTEXT_ARCHIVE_ENABLED",
    )
    shenzhou_context_keep_raw_days: int = Field(
        default=14,
        ge=1,
        le=3650,
        validation_alias="SHENZHOU_CONTEXT_KEEP_RAW_DAYS",
    )
    shenzhou_cache_dir: Path = Field(
        default_factory=lambda: _project_root() / "data" / "shenzhou",
        validation_alias="SHENZHOU_CACHE_DIR",
    )

    @field_validator("shenzhou_integration_enabled", mode="before")
    @classmethod
    def _coerce_shenzhou_integration(cls, v: Any) -> bool:
        if v is None or v == "":
            return True
        if isinstance(v, bool):
            return v
        return str(v).strip().lower() in ("1", "true", "yes", "on")

    @field_validator("shenzhou_scheduler_enabled", mode="before")
    @classmethod
    def _coerce_shenzhou_scheduler(cls, v: Any) -> bool:
        if v is None or v == "":
            return True
        if isinstance(v, bool):
            return v
        return str(v).strip().lower() in ("1", "true", "yes", "on")

    @field_validator(
        "shenzhou_proactive_life_context",
        "shenzhou_proactive_message_enabled",
        "shenzhou_context_archive_enabled",
        mode="before",
    )
    @classmethod
    def _coerce_shenzhou_proactive(cls, v: Any) -> bool:
        if v is None or v == "":
            return False
        if isinstance(v, bool):
            return v
        return str(v).strip().lower() in ("1", "true", "yes", "on")

    @field_validator("shenzhou_default_session_id", mode="before")
    @classmethod
    def _normalize_shenzhou_default_session_id(cls, v: Any) -> str:
        token = str(v or "").strip()
        if not token:
            return _default_shenzhou_session_id()
        # 兼容历史默认值 user-admin，自动迁移到 user-<开发者用户名>
        if token == "user-admin":
            return _default_shenzhou_session_id()
        return token

    @field_validator("shenzhou_cache_dir", mode="before")
    @classmethod
    def _resolve_shenzhou_cache(cls, v: Any) -> Path:
        if v is None or v == "":
            return _project_root() / "data" / "shenzhou"
        p = Path(v).expanduser() if not isinstance(v, Path) else v.expanduser()
        if not p.is_absolute():
            p = _project_root() / p
        return p


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
