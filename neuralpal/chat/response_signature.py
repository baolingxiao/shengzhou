# -*- coding: utf-8 -*-
"""伴侣回复末尾颜文字：解析与输出后处理（不交给 LLM）。"""

from __future__ import annotations

import re
from functools import lru_cache

from neuralpal.characters.models import AICharacter

SYSTEM_DEFAULT_ENDING_SIGNATURE = "( ´ ▽ ` )ﾉ"

_CPC_DEFAULT_SIGNATURES: dict[str, str] = {
    "WRES_INTJ": "(｡•̀ᴗ-)✧",
    "WRES_INFJ": "( ´ ▽ ` )ﾉ",
    "WREP_INTP": "(￣▽￣)ノ",
    "WREP_ISFP": "(˶ᵔ ᵕ ᵔ˶)",
    "CALS_ENTJ": "( •̀ᴗ•́ )و",
    "CALS_ESTJ": "( •̀ ω •́ )✧",
    "CARP_ENTP": "(¬‿¬ )",
    "WAES_INFP": "(｡･ω･｡)ﾉ♡",
    "WAES_ENFJ": "(づ｡◕‿‿◕｡)づ",
    "WAES_ISFJ": "( ˘͈ ᵕ ˘͈♡)",
    "WASP_ENFP": "ヽ(•̀ω•́ )ゝ",
    "WASP_ESFP": "ヾ(≧▽≦*)o",
    "CRES_ISTJ": "( • ̀ω•́ )",
    "WASS_ESFJ": "(๑˘︶˘๑)",
    "CRLP_ISTP": "( •_•)>⌐■-■",
    "CALP_ESTP": "(ง •̀_•́)ง",
}


def _normalize_signature(sig: str) -> str:
    return (sig or "").strip()


@lru_cache(maxsize=1)
def _collect_known_signatures() -> tuple[str, ...]:
    known: set[str] = {SYSTEM_DEFAULT_ENDING_SIGNATURE}
    known.update(_CPC_DEFAULT_SIGNATURES.values())
    try:
        from neuralpal.companion_life.cpc_profiles import load_life_profiles

        for prof in load_life_profiles().values():
            ds = _normalize_signature(getattr(prof, "default_ending_signature", "") or "")
            if ds:
                known.add(ds)
    except Exception:
        pass
    try:
        from neuralpal.characters.store import get_character_store

        for char in get_character_store().list_characters():
            cs = _normalize_signature(char.ending_signature or "")
            if cs:
                known.add(cs)
    except Exception:
        pass
    return tuple(sorted(known, key=len, reverse=True))


def resolve_profile_default_signature(profile_key: str) -> str | None:
    pk = (profile_key or "").strip().upper()
    if not pk:
        return None
    try:
        from neuralpal.companion_life.cpc_profiles import get_life_profile

        prof = get_life_profile(pk)
        if prof is not None:
            ds = _normalize_signature(getattr(prof, "default_ending_signature", "") or "")
            if ds:
                return ds
    except Exception:
        pass
    return _CPC_DEFAULT_SIGNATURES.get(pk)


def resolve_ending_signature(character: AICharacter | None) -> str:
    """character 实例 → CPC 默认 → 系统默认。"""
    if character is not None:
        inst = _normalize_signature(character.ending_signature or "")
        if inst:
            return inst
        from neuralpal.companion_life.identity import resolve_profile_key_for_character

        pk = resolve_profile_key_for_character(character)
        prof_sig = resolve_profile_default_signature(pk)
        if prof_sig:
            return prof_sig
    return SYSTEM_DEFAULT_ENDING_SIGNATURE


def _strip_trailing_known_signature(text: str) -> str:
    t = (text or "").rstrip()
    if not t:
        return t
    for sig in _collect_known_signatures():
        if not sig:
            continue
        for suffix in (f" {sig}", sig):
            if t.endswith(suffix):
                t = t[: -len(suffix)].rstrip()
                break
    return t


def append_companion_signature(text: str, ending_signature: str) -> str:
    """
    在最终用户可见回复末尾追加颜文字。
    不修改 Markdown 结构；仅处理全文末尾。
    """
    sig = _normalize_signature(ending_signature) or SYSTEM_DEFAULT_ENDING_SIGNATURE
    if not sig:
        return text or ""

    raw = text or ""
    if not raw.strip():
        return sig

    body = _strip_trailing_known_signature(raw)
    if body.endswith(sig) or body.endswith(f" {sig}"):
        return body
    return f"{body} {sig}"


def should_append_companion_signature(text: str) -> bool:
    """是否应对该文本追加颜文字（排除工具 JSON、系统错误条等）。"""
    stripped = (text or "").strip()
    if not stripped:
        return True
    if stripped.startswith("【") and "】" in stripped[:24]:
        return False
    if re.match(r"^\{[\s\S]*\}$", stripped):
        return False
    if stripped.startswith("<") and stripped.endswith(">"):
        return False
    return True


def finalize_companion_user_reply(
    text: str,
    *,
    session_id: str = "default",
    character_id: str | None = None,
) -> str:
    """在返回用户前追加当前伴侣实例颜文字（无角色则不追加）。"""
    from neuralpal.characters.prompt_bridge import resolve_character_for_session

    if not should_append_companion_signature(text):
        return text

    character = resolve_character_for_session(session_id, character_id=character_id)
    if character is None:
        return text

    sig = resolve_ending_signature(character)
    return append_companion_signature(text, sig)
