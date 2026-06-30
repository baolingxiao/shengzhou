# -*- coding: utf-8 -*-
"""信任度 + 风险级门控。"""

from __future__ import annotations

from dataclasses import dataclass

from neuralpal.characters.models import AICharacter
from neuralpal.characters.character_rules import _load_trust_config, character_rules_dir, load_trust_state
from neuralpal.tools.agent.models import ActionProposal, RiskLevel


@dataclass
class GateResult:
    allowed: bool
    message: str
    requires_confirm: bool = True


def _trust_points(character: AICharacter | None) -> int:
    if character is None:
        return 10
    rules_dir = character_rules_dir(character)
    if rules_dir is None:
        return 10
    config = _load_trust_config(str(rules_dir))
    state = load_trust_state(character)
    if not config or not state:
        return int((config or {}).get("range", {}).get("initial", 10) if config else 10)
    rng = config.get("range") or {}
    lo = int(rng.get("min", 0))
    hi = int(rng.get("max", 100))
    tp = int(state.get("trust_points", rng.get("initial", 10)))
    return max(lo, min(hi, tp))


def min_tp_for_risk(risk: RiskLevel) -> int:
    if risk == "L3":
        return 10
    if risk == "L2":
        return 31
    return 51


def is_blocked_risk(risk: RiskLevel, goal: str) -> bool:
    g = (goal or "").lower()
    blocked_keywords = (
        "付款", "支付", "转账", "删除全部", "格式化", "rm -rf",
        "破解", "入侵", "钓鱼",
    )
    if risk == "L1":
        pay_words = ("付款", "支付", "转账", "下单购买", "确认支付")
        if any(w in goal for w in pay_words):
            return True
    return any(w in g for w in blocked_keywords)


def check_proposal(proposal: ActionProposal, character: AICharacter | None) -> GateResult:
    if is_blocked_risk(proposal.risk_level, proposal.goal):
        return GateResult(
            allowed=False,
            message="该操作触及安全红线（付款/破坏性/未授权操作），无法代劳。请你本人手动完成关键步骤。",
            requires_confirm=True,
        )

    tp = _trust_points(character)
    need = min_tp_for_risk(proposal.risk_level)
    if tp < need:
        return GateResult(
            allowed=False,
            message=(
                f"当前亲密度（TP={tp}）不足以执行此风险级别（{proposal.risk_level}，需 TP≥{need}）。"
                "可先完成更多事务协作以提升信任，或由你本人在本机操作。"
            ),
            requires_confirm=True,
        )

    requires_confirm = True
    if proposal.risk_level == "L3" and tp >= 71:
        requires_confirm = False
    if proposal.risk_level in ("L1", "L2"):
        requires_confirm = True

    return GateResult(allowed=True, message="ok", requires_confirm=requires_confirm)


def check_execute(proposal: ActionProposal, character: AICharacter | None) -> GateResult:
    base = check_proposal(proposal, character)
    if not base.allowed:
        return base
    if proposal.status != "confirmed" and proposal.status != "running":
        return GateResult(
            allowed=False,
            message="任务尚未确认。请用户明确回复「确认」后再执行。",
            requires_confirm=True,
        )
    return base
