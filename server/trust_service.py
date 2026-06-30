# -*- coding: utf-8 -*-
"""亲密度（TP）读写。"""

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
from neuralpal.characters.trust_points import apply_trust_delta
from neuralpal.characters.store import get_character_store


def _clamp_tp(value: int, config: dict[str, Any]) -> int:
    rng = config.get("range") or {}
    lo = int(rng.get("min", 0))
    hi = int(rng.get("max", 100))
    return max(lo, min(hi, int(value)))


def get_trust_snapshot(character_id: str) -> dict[str, Any]:
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

    rng = config.get("range") or {}
    tp = _clamp_tp(
        int(state.get("trust_points", rng.get("initial", 10))),
        config,
    )
    level_info = trust_level_for_points(tp, config)

    return {
        "character_id": char.id,
        "character": char.name,
        "display_name": "亲密度",
        "trust_points": tp,
        "min": int(rng.get("min", 0)),
        "max": int(rng.get("max", 100)),
        "level": int(level_info.get("level", state.get("level", 1))),
        "level_name": str(level_info.get("name", state.get("level_name", ""))),
    }


def set_trust_points(character_id: str, trust_points: int, *, actor: str) -> dict[str, Any]:
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

    tp = _clamp_tp(trust_points, config)
    level_info = trust_level_for_points(tp, config)
    prev_tp = int(state.get("trust_points", tp))

    state["trust_points"] = tp
    state["level"] = int(level_info.get("level", 1))
    state["level_name"] = str(level_info.get("name", ""))
    state["updated_at"] = datetime.now(timezone.utc).isoformat()

    score_log = state.get("score_log")
    if not isinstance(score_log, list):
        score_log = []
    if tp != prev_tp:
        score_log.append(
            {
                "delta": tp - prev_tp,
                "reason": f"管理者 {actor} 手动调整",
                "tp_after": tp,
                "at": state["updated_at"],
            }
        )
    state["score_log"] = score_log[-200:]

    if not save_trust_state(char, state):
        raise RuntimeError("保存信任度失败")

    return get_trust_snapshot(character_id)


def apply_trust_delta_for_character(
    character_id: str,
    delta: int,
    *,
    reason: str,
) -> dict[str, Any]:
    return apply_trust_delta(character_id, delta, reason=reason)
