# -*- coding: utf-8 -*-
"""代办任务数据结构。"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Literal

ActionSurface = Literal["local", "web", "chain"]
RiskLevel = Literal["L1", "L2", "L3"]
ActionStatus = Literal[
    "awaiting_confirm",
    "confirmed",
    "running",
    "completed",
    "failed",
    "cancelled",
]


class Surface(str, Enum):
    LOCAL = "local"
    WEB = "web"
    CHAIN = "chain"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def new_task_id() -> str:
    stamp = _utc_now().strftime("%Y%m%d_%H%M%S")
    return f"act_{stamp}_{uuid.uuid4().hex[:8]}"


@dataclass
class ActionProposal:
    task_id: str
    goal: str
    surface: ActionSurface
    steps: list[str]
    risk_level: RiskLevel
    reason: str
    status: ActionStatus = "awaiting_confirm"
    session_id: str = "default"
    character_id: str | None = None
    created_at: str = field(default_factory=lambda: _iso(_utc_now()))
    expires_at: str = field(
        default_factory=lambda: _iso(_utc_now() + timedelta(hours=2))
    )
    execution_summary: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActionProposal:
        return cls(
            task_id=str(data.get("task_id") or new_task_id()),
            goal=str(data.get("goal") or ""),
            surface=data.get("surface") or "local",  # type: ignore[arg-type]
            steps=[str(x) for x in (data.get("steps") or [])],
            risk_level=data.get("risk_level") or "L2",  # type: ignore[arg-type]
            reason=str(data.get("reason") or ""),
            status=data.get("status") or "awaiting_confirm",  # type: ignore[arg-type]
            session_id=str(data.get("session_id") or "default"),
            character_id=data.get("character_id"),
            created_at=str(data.get("created_at") or _iso(_utc_now())),
            expires_at=str(data.get("expires_at") or _iso(_utc_now() + timedelta(hours=2))),
            execution_summary=str(data.get("execution_summary") or ""),
            error=str(data.get("error") or ""),
        )

    def is_expired(self) -> bool:
        try:
            exp = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            return _utc_now() > exp
        except ValueError:
            return False

    def summary_for_user(self) -> str:
        lines = [f"任务编号：{self.task_id}", f"目标：{self.goal}", "步骤："]
        for i, step in enumerate(self.steps, 1):
            lines.append(f"  {i}. {step}")
        lines.append(f"执行面：{self.surface} · 风险：{self.risk_level}")
        return "\n".join(lines)
