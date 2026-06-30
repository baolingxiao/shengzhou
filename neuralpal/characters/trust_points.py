# -*- coding: utf-8 -*-
"""信任度（TP）运行时读写与加减分。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from neuralpal.characters.character_rules import (
    _load_trust_config,
    character_rules_dir,
    load_trust_state,
    save_trust_state,
    trust_level_for_points,
)
from neuralpal.characters.store import get_character_store


def _clamp_tp(value: int, config: dict[str, Any]) -> int:
    rng = config.get("range") or {}
    lo = int(rng.get("min", 0))
    hi = int(rng.get("max", 100))
    return max(lo, min(hi, int(value)))


def apply_trust_delta(
    character_id: str,
    delta: int,
    *,
    reason: str,
) -> dict[str, Any]:
    """对角色 TP 加减分并持久化，返回快照含 trust_delta。"""
    char = get_character_store().get_character(character_id.strip())
    if not char:
        raise ValueError("角色不存在")

    rules_dir = character_rules_dir(char)
    if rules_dir is None:
        raise ValueError("角色未配置信任度规则")

    config = _load_trust_config(str(rules_dir))
    state = load_trust_state(char)
    if not config or not state:
        raise ValueError("信任度配置不可用")

    prev_tp = _clamp_tp(int(state.get("trust_points", 10)), config)
    next_tp = _clamp_tp(prev_tp + int(delta), config)
    actual_delta = next_tp - prev_tp
    level_info = trust_level_for_points(next_tp, config)

    state["trust_points"] = next_tp
    state["level"] = int(level_info.get("level", 1))
    state["level_name"] = str(level_info.get("name", ""))
    state["updated_at"] = datetime.now(timezone.utc).isoformat()

    score_log = state.get("score_log")
    if not isinstance(score_log, list):
        score_log = []
    if actual_delta != 0:
        score_log.append(
            {
                "delta": actual_delta,
                "reason": (reason or "系统调整").strip(),
                "tp_after": next_tp,
                "at": state["updated_at"],
            }
        )
    state["score_log"] = score_log[-200:]

    if not save_trust_state(char, state):
        raise RuntimeError("保存信任度失败")

    rng = config.get("range") or {}
    return {
        "character_id": char.id,
        "character": char.name,
        "display_name": "亲密度",
        "trust_points": next_tp,
        "trust_delta": actual_delta,
        "min": int(rng.get("min", 0)),
        "max": int(rng.get("max", 100)),
        "level": int(level_info.get("level", 1)),
        "level_name": str(level_info.get("name", "")),
    }


__all__ = ["apply_trust_delta"]
