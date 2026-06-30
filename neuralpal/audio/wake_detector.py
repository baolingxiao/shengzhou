# -*- coding: utf-8 -*-
"""唤醒词匹配与 transcript 清洗。"""

from __future__ import annotations

import re
from typing import Iterable

# 常见同音/误识别字：在/再/仔 + 不/补
_ZWAKE_FIRST = frozenset("在再仔载宰")
_ZWAKE_BU_LIKE = frozenset("不补補布步簿")

_TRAD_TO_SIMP = str.maketrans(
    {
        "補": "补",
        "臺": "台",
        "瞭": "了",
        "麼": "么",
    }
)


def normalize_wake_text(text: str) -> str:
    t = (text or "").strip().lower().translate(_TRAD_TO_SIMP)
    t = re.sub(r"[\s，,。.!！?？、；;：:\"'“”‘’（）()\[\]【】\-—…·]+", "", t)
    return t


def parse_wake_phrases(raw: str | Iterable[str]) -> list[str]:
    if isinstance(raw, str):
        parts = re.split(r"[,，;；\n]+", raw)
    else:
        parts = list(raw)
    out: list[str] = []
    seen: set[str] = set()
    for part in parts:
        phrase = normalize_wake_text(str(part))
        if phrase and phrase not in seen:
            seen.add(phrase)
            out.append(phrase)
    return out


def build_wake_stt_prompt(phrases: Iterable[str]) -> str:
    cleaned = parse_wake_phrases(phrases)
    if not cleaned:
        cleaned = ["在不", "再不", "仔不"]
    return "。".join(cleaned) + "。"


def _exact_wake_match(normalized: str, phrases: Iterable[str]) -> str | None:
    for phrase in phrases:
        p = normalize_wake_text(phrase)
        if not p:
            continue
        if p in normalized or normalized in p:
            return p
    return None


def _fuzzy_wake_match(normalized: str, phrases: list[str]) -> str | None:
    if not normalized or len(normalized) > 12:
        return None

    if normalized[0] in _ZWAKE_FIRST:
        for idx, ch in enumerate(normalized[1:4], start=1):
            if ch in _ZWAKE_BU_LIKE:
                return _pick_phrase_for_match(phrases, normalized[: idx + 1])

    if normalized.startswith("再") and any(ch in _ZWAKE_BU_LIKE for ch in normalized):
        return _pick_phrase_for_match(phrases, normalized[:4], prefer_prefix="再")

    return None


def _pick_phrase_for_match(
    phrases: list[str],
    fragment: str,
    *,
    prefer_prefix: str = "",
) -> str:
    if prefer_prefix:
        for phrase in phrases:
            if phrase.startswith(prefer_prefix):
                return phrase
    for phrase in phrases:
        if phrase and phrase[0] == fragment[0]:
            return phrase
    return phrases[0] if phrases else fragment


def match_wake_phrase(text: str, phrases: Iterable[str]) -> str | None:
    normalized = normalize_wake_text(text)
    if not normalized:
        return None
    phrase_list = parse_wake_phrases(phrases)
    exact = _exact_wake_match(normalized, phrase_list)
    if exact is not None:
        return exact
    return _fuzzy_wake_match(normalized, phrase_list)


def strip_wake_prefix(text: str, wake_phrase: str | None, phrases: Iterable[str] | None = None) -> str:
    raw = (text or "").strip()
    if not raw:
        return raw
    cleaned = raw
    phrase_list = parse_wake_phrases(phrases) if phrases is not None else []
    # 连续剥离唤醒词（如「再不。仔不。」→ 空）
    for _ in range(3):
        prev = cleaned
        if wake_phrase:
            pattern = re.compile(re.escape(wake_phrase), re.IGNORECASE)
            cleaned = pattern.sub("", cleaned, count=1)
        for phrase in phrase_list:
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            cleaned = pattern.sub("", cleaned, count=1)
        fuzzy = re.compile(
            rf"^[{''.join(_ZWAKE_FIRST)}][{''.join(_ZWAKE_BU_LIKE)}]?",
            re.IGNORECASE,
        )
        cleaned = fuzzy.sub("", cleaned, count=1)
        cleaned = re.sub(r"^[\s，,。.!！?？、]+", "", cleaned).strip()
        if cleaned == prev:
            break
    return cleaned


def is_wake_only_text(text: str, phrases: Iterable[str]) -> bool:
    """判断文本是否仅为唤醒词（不应作为用户问题提交）。"""
    normalized = normalize_wake_text(text)
    if not normalized:
        return True
    phrase_list = parse_wake_phrases(phrases)
    if normalized in phrase_list:
        return True
    return match_wake_phrase(text, phrase_list) is not None and len(normalized) <= 4
