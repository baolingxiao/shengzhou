# -*- coding: utf-8 -*-
"""Companion Personality Code (CPC) 伴侣人格码 — 四维字母释义与解码。"""

from __future__ import annotations

from typing import Any

CPC_DIMENSIONS: tuple[dict[str, Any], ...] = (
    {
        "key": "emotion",
        "name": "情感表达",
        "hint": "表达更偏热情，还是安静陪伴",
        "options": {
            "W": {"en": "Warm", "label": "温暖"},
            "C": {"en": "Calm", "label": "克制"},
        },
    },
    {
        "key": "interaction",
        "name": "互动方式",
        "hint": "更主动推动关系，还是尊重用户空间",
        "options": {
            "A": {"en": "Active", "label": "主动"},
            "R": {"en": "Reserved", "label": "留白"},
        },
    },
    {
        "key": "thinking",
        "name": "思维风格",
        "hint": "更偏分析解决问题，还是理解情绪",
        "options": {
            "L": {"en": "Logical", "label": "理性"},
            "E": {"en": "Empathic", "label": "共情"},
        },
    },
    {
        "key": "temperament",
        "name": "关系气质",
        "hint": "更可靠稳定，还是轻松有趣",
        "options": {
            "S": {"en": "Stable", "label": "稳定"},
            "P": {"en": "Playful", "label": "灵动"},
        },
    },
)


def cpc_legend() -> list[dict[str, Any]]:
    """返回四维字母对照表（供前端展示）。"""
    rows: list[dict[str, Any]] = []
    for dim in CPC_DIMENSIONS:
        opts = []
        for letter, meta in dim["options"].items():
            opts.append(
                {
                    "letter": letter,
                    "en": meta["en"],
                    "label": meta["label"],
                }
            )
        rows.append(
            {
                "key": dim["key"],
                "name": dim["name"],
                "hint": dim["hint"],
                "options": opts,
            }
        )
    return rows


def decode_partner_code(code: str) -> dict[str, Any]:
    """将 4 位伴侣代号解码为各维度释义。"""
    raw = (code or "").strip().upper()
    if len(raw) != 4:
        return {
            "code": raw,
            "valid": False,
            "summary": "",
            "letters": [],
        }

    letters: list[dict[str, str]] = []
    for idx, dim in enumerate(CPC_DIMENSIONS):
        letter = raw[idx]
        meta = dim["options"].get(letter)
        if not meta:
            return {
                "code": raw,
                "valid": False,
                "summary": "",
                "letters": [],
            }
        letters.append(
            {
                "letter": letter,
                "dimension": dim["name"],
                "dimension_key": dim["key"],
                "en": meta["en"],
                "label": meta["label"],
            }
        )

    return {
        "code": raw,
        "valid": True,
        "summary": "、".join(item["label"] for item in letters),
        "letters": letters,
    }
