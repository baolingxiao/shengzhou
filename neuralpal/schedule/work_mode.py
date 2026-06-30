# -*- coding: utf-8 -*-
"""沈昼上下班时间判定与 system 注入块。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

from neuralpal.characters.models import AICharacter
from neuralpal.characters.character_rules import character_rules_dir
from neuralpal.schedule.overtime_state import load_overtime_state, save_overtime_state

WorkModeKind = Literal["work", "companion", "overtime"]

_WORK_MODE_MARKER = "[[NEURALPAL_WORK_SCHEDULE_V1]]"

_DEFAULT_SCHEDULE: dict[str, Any] = {
    "timezone": "local",
    "work_weekdays": [0, 1, 2, 3, 4],
    "work_start": "10:00",
    "work_end": "17:00",
    "overtime_tp_cost": 5,
    "overtime_active_minutes": 120,
    "refusal_template": (
        "我下班啦，老板。现在是私人时间，电脑操控和网页搜索都关着——"
        "除非你让我加班，否则只能陪你聊天哦。"
    ),
    "overtime_prompt_template": (
        "要说加班也行。不过非工作时间代劳要算你欠我一次，亲密度会扣 {cost} 点。"
        "回复「麻烦你加个班」之类我就继续办你刚才那件事。"
    ),
}


@dataclass(frozen=True)
class WorkModeSnapshot:
    mode: WorkModeKind
    agent_tools_allowed: bool
    is_workday: bool
    clock_label: str
    work_window: str
    awaiting_overtime_consent: bool
    has_deferred_task: bool
    overtime_active: bool
    overtime_tp_cost: int
    timezone: str


def _characters_root() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "characters"


@lru_cache(maxsize=4)
def _load_schedule_config(character_name: str) -> dict[str, Any]:
    path = _characters_root() / character_name / "rules" / "work_schedule.json"
    if not path.is_file():
        return dict(_DEFAULT_SCHEDULE)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        merged = dict(_DEFAULT_SCHEDULE)
        merged.update(data if isinstance(data, dict) else {})
        return merged
    except (OSError, json.JSONDecodeError):
        return dict(_DEFAULT_SCHEDULE)


def _parse_hhmm(value: str) -> time:
    parts = (value or "10:00").strip().split(":")
    h = int(parts[0]) if parts else 10
    m = int(parts[1]) if len(parts) > 1 else 0
    return time(hour=max(0, min(23, h)), minute=max(0, min(59, m)))


def _now_for_schedule(tz_name: str) -> tuple[datetime, str]:
    """
    解析排班用时区并返回当前时刻。

    ``local`` / ``system``：跟随运行环境本机时钟（与菜单栏时间一致）。
    其它值：IANA 时区名，如 ``Asia/Shanghai``。
    """
    raw = (tz_name or "local").strip()
    if raw.lower() in ("local", "system", "host"):
        now = datetime.now().astimezone()
        tzinfo = now.tzinfo
        key = getattr(tzinfo, "key", None) if tzinfo is not None else None
        label = f"本地 ({key})" if key else "本地"
        return now, label
    try:
        tz = ZoneInfo(raw)
        return datetime.now(tz), raw
    except Exception:
        tz = ZoneInfo("Asia/Shanghai")
        return datetime.now(tz), "Asia/Shanghai"


def _now_in_tz(tz_name: str) -> datetime:
    return _now_for_schedule(tz_name)[0]


def is_within_work_hours(
    *,
    character_name: str = "沈昼",
    now: datetime | None = None,
) -> bool:
    cfg = _load_schedule_config(character_name)
    tz_name = str(cfg.get("timezone") or "local")
    if now is not None:
        local = now.astimezone() if now.tzinfo is not None else now
    else:
        local = _now_in_tz(tz_name)
    weekdays = cfg.get("work_weekdays") or [0, 1, 2, 3, 4]
    if local.weekday() not in weekdays:
        return False
    start = _parse_hhmm(str(cfg.get("work_start") or "10:00"))
    end = _parse_hhmm(str(cfg.get("work_end") or "17:00"))
    t = local.time()
    return start <= t < end


def _overtime_still_active(state, cfg: dict[str, Any], now: datetime) -> bool:
    if not state.overtime_active:
        return False
    expires_raw = (state.overtime_expires_at or "").strip()
    if not expires_raw:
        return True
    try:
        expires = datetime.fromisoformat(expires_raw.replace("Z", "+00:00"))
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc) < expires.astimezone(timezone.utc)
    except ValueError:
        return True


def resolve_work_mode(
    session_id: str,
    *,
    character: AICharacter | None = None,
    now: datetime | None = None,
) -> WorkModeSnapshot:
    name = (character.name if character else "沈昼") or "沈昼"
    cfg = _load_schedule_config(name)
    tz_name = str(cfg.get("timezone") or "local")
    if now is not None:
        local = now.astimezone() if now.tzinfo is not None else now
        tz_label = tz_name
    else:
        local, tz_label = _now_for_schedule(tz_name)

    state = load_overtime_state(session_id)
    overtime_active = _overtime_still_active(state, cfg, local)
    if state.overtime_active and not overtime_active:
        state.overtime_active = False
        save_overtime_state(state)

    start = str(cfg.get("work_start") or "10:00")
    end = str(cfg.get("work_end") or "17:00")
    work_window = f"工作日 {start}–{end}"
    clock_label = local.strftime("%H:%M")
    is_workday = local.weekday() in (cfg.get("work_weekdays") or [0, 1, 2, 3, 4])

    in_work = is_within_work_hours(character_name=name, now=local)
    if in_work:
        mode: WorkModeKind = "work"
        agent_allowed = True
        if state.awaiting_overtime_consent or (state.deferred_task_text or "").strip():
            state.awaiting_overtime_consent = False
            state.deferred_task_text = ""
            save_overtime_state(state)
    elif overtime_active:
        mode = "overtime"
        agent_allowed = True
    else:
        mode = "companion"
        agent_allowed = False

    return WorkModeSnapshot(
        mode=mode,
        agent_tools_allowed=agent_allowed,
        is_workday=is_workday,
        clock_label=clock_label,
        work_window=work_window,
        awaiting_overtime_consent=bool(state.awaiting_overtime_consent),
        has_deferred_task=bool((state.deferred_task_text or "").strip()),
        overtime_active=overtime_active,
        overtime_tp_cost=int(cfg.get("overtime_tp_cost") or 5),
        timezone=tz_label,
    )


def get_work_mode_snapshot(
    session_id: str,
    *,
    character_id: str | None = None,
) -> dict[str, Any]:
    from neuralpal.characters.prompt_bridge import resolve_character_for_session

    character = resolve_character_for_session(session_id, character_id=character_id)
    snap = resolve_work_mode(session_id, character=character)
    cfg = _load_schedule_config((character.name if character else "沈昼") or "沈昼")
    return {
        "mode": snap.mode,
        "mode_label": {"work": "上班中", "companion": "陪伴中", "overtime": "加班中"}[snap.mode],
        "agent_tools_allowed": snap.agent_tools_allowed,
        "is_workday": snap.is_workday,
        "clock": snap.clock_label,
        "work_window": snap.work_window,
        "timezone": snap.timezone,
        "awaiting_overtime_consent": snap.awaiting_overtime_consent,
        "has_deferred_task": snap.has_deferred_task,
        "overtime_active": snap.overtime_active,
        "overtime_tp_cost": snap.overtime_tp_cost,
        "work_start": cfg.get("work_start"),
        "work_end": cfg.get("work_end"),
    }


def build_off_hours_refusal(character: AICharacter | None, *, tp_cost: int = 5) -> str:
    name = (character.name if character else "沈昼") or "沈昼"
    cfg = _load_schedule_config(name)
    refusal = str(cfg.get("refusal_template") or _DEFAULT_SCHEDULE["refusal_template"])
    hint = str(cfg.get("overtime_prompt_template") or _DEFAULT_SCHEDULE["overtime_prompt_template"])
    hint = hint.format(cost=tp_cost)
    return f"{refusal}\n\n{hint}"


def format_work_mode_block(
    snap: WorkModeSnapshot,
    *,
    character: AICharacter | None = None,
) -> str:
    name = (character.name if character else "沈昼") or "沈昼"
    mode_desc = {
        "work": "当前为**上班时间**：可调用电脑操控与网页搜索代办；语气公事公办。",
        "companion": (
            "当前为**下班/陪伴时间**：禁止调用 propose_action 及一切电脑操控、网页搜索代办；"
            "仅陪伴闲聊。用户若提出任务，须先拒绝并提示加班；用户明确同意加班后才可执行，且会扣亲密度。"
        ),
        "overtime": (
            "当前为**用户已授权的加班时段**：可恢复电脑操控与网页搜索，完成待办后仍保持沈昼口吻。"
        ),
    }[snap.mode]

    deferred_note = ""
    if snap.has_deferred_task and snap.awaiting_overtime_consent:
        deferred_note = (
            "\n- 上一条用户任务已暂存，正在等待用户是否同意加班；"
            "在用户明确同意前不得执行该任务。"
        )

    return f"""{_WORK_MODE_MARKER}
### 【沈昼 · 上下班调度 · 必须遵守】
- 角色：**{name}**
- 当前模式：**{snap.mode}**（本地 {snap.clock_label} · {snap.timezone}）
- 常规办公时段：**{snap.work_window}**
- {mode_desc}
- 非办公时段任务须走「拒绝 → 用户同意加班（扣 {snap.overtime_tp_cost} TP）→ 再执行」流程。{deferred_note}
- 陪伴模式下仍须遵守信任等级与 reply_style；不要向用户复述 TP 或「系统模式」等内部词，用自然口吻表达下班/加班。
"""


def schedule_config_for_character(character: AICharacter | None) -> dict[str, Any]:
    name = (character.name if character else "沈昼") or "沈昼"
    return _load_schedule_config(name)


def grant_overtime_window(
    session_id: str,
    *,
    character_name: str = "沈昼",
    now: datetime | None = None,
) -> None:
    """标记会话进入加班窗口。"""
    cfg = _load_schedule_config(character_name)
    minutes = int(cfg.get("overtime_active_minutes") or 120)
    tz_name = str(cfg.get("timezone") or "local")
    local = now if now is not None else _now_in_tz(tz_name)
    if local.tzinfo is None:
        local = _now_in_tz(tz_name)
    expires = local + timedelta(minutes=minutes)

    state = load_overtime_state(session_id)
    state.overtime_active = True
    state.awaiting_overtime_consent = False
    state.overtime_granted_at = local.astimezone(timezone.utc).isoformat()
    state.overtime_expires_at = expires.astimezone(timezone.utc).isoformat()
    save_overtime_state(state)


__all__ = [
    "WorkModeSnapshot",
    "build_off_hours_refusal",
    "format_work_mode_block",
    "get_work_mode_snapshot",
    "grant_overtime_window",
    "is_within_work_hours",
    "resolve_work_mode",
    "schedule_config_for_character",
]
