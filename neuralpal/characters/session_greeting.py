# -*- coding: utf-8 -*-
"""会话开场问候：按本地时段 + CPC 人格生成伴侣口吻问候（LLM，失败则模板降级）。"""

from __future__ import annotations

import logging
import threading
from contextlib import nullcontext
from datetime import datetime
from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from neuralpal.characters.cpc import decode_partner_code
from neuralpal.chat.response_signature import finalize_companion_user_reply
from neuralpal.config import get_settings

if TYPE_CHECKING:
    from neuralpal.characters.models import AICharacter

logger = logging.getLogger(__name__)

TIME_PERIOD_LABELS: tuple[str, ...] = ("凌晨", "早上", "下午", "晚上", "深夜")

# (start_hour inclusive, end_hour exclusive) — 本地时间
_TIME_PERIOD_RANGES: tuple[tuple[int, int, str], ...] = (
    (0, 6, "凌晨"),
    (6, 12, "早上"),
    (12, 18, "下午"),
    (18, 22, "晚上"),
    (22, 24, "深夜"),
)

_ANTI_IDLE_FORBIDDEN = (
    "一直等你",
    "只等你",
    "你怎么这么久才来",
    "没有你很无聊",
    "没有你我不知道干什么",
    "我一天都在等你",
    "我一直等你来找你",
)

_GENERIC_FALLBACK: dict[str, str] = {
    "凌晨": "这个点还醒着呀。不用急着说什么，想聊就聊，想安静一会儿也行。",
    "早上": "早上好。今天可以慢慢来，不用一下子把状态调整好。",
    "下午": "下午好。要是有点累，也不用装作没事。",
    "晚上": "晚上好。今天想随便聊聊，或者安静待一会儿都可以。",
    "深夜": "这么晚了还在呀。不用解释为什么没睡，陪你说会儿话也可以。",
}

_inflight_sessions: set[str] = set()
_inflight_guard = threading.Lock()


def _normalize_session_id(session_id: str) -> str:
    return (session_id or "default").strip() or "default"


def try_acquire_greeting_slot(session_id: str) -> bool:
    """同一会话同时只允许一条开场问候在生成/投递中。"""
    sid = _normalize_session_id(session_id)
    with _inflight_guard:
        if sid in _inflight_sessions:
            return False
        _inflight_sessions.add(sid)
        return True


def release_greeting_slot(session_id: str) -> None:
    sid = _normalize_session_id(session_id)
    with _inflight_guard:
        _inflight_sessions.discard(sid)


_WRES_FALLBACK: dict[str, str] = {
    "凌晨": "这个点还醒着呀。不用急着说什么，想聊就聊，想安静一会儿也行。",
    "早上": "早上好。今天不用一下子把状态调整好，慢慢来也可以。",
    "下午": "下午好。要是今天有点累，也不用装作没事，我听得出来。",
    "晚上": "晚上好。今天过得怎么样，想随便聊聊也行。",
    "深夜": "这么晚了还在呀。不用解释为什么没睡，陪你说会儿话也可以。",
}


def get_local_time_period(now: datetime | None = None) -> str:
    """返回当前本地时段标签（凌晨/早上/下午/晚上/深夜）。"""
    dt = now or datetime.now().astimezone()
    hour = dt.hour
    for start, end, label in _TIME_PERIOD_RANGES:
        if start <= hour < end:
            return label
    return "晚上"


def session_has_user_messages(session_id: str, *, service: Any | None = None) -> bool:
    """会话编排器中是否已有用户轮次（须通过 service 读取已缓存的编排器）。"""
    if service is None:
        return False
    return _session_orchestrator_has_user_messages(session_id, service)


def _with_service_orchestrator(service: Any, session_id: str):
    sid = (session_id or "default").strip() or "default"
    lock = getattr(service, "_lock", None)
    ctx = lock if lock is not None else nullcontext()
    with ctx:
        return service._get_orchestrator(sid)


def _session_orchestrator_has_user_messages(session_id: str, service: Any) -> bool:
    """使用已存在的 Desktop/Local service 实例检查会话历史。"""
    try:
        orch = _with_service_orchestrator(service, session_id)
        if service._use_memory:
            for msg in orch._short.chat_memory.messages:
                if isinstance(msg, HumanMessage):
                    return True
            return False
        for msg in getattr(orch, "_history", []):
            if isinstance(msg, HumanMessage):
                return True
        return False
    except Exception:
        return False


def _session_orchestrator_has_any_turns(session_id: str, service: Any) -> bool:
    """会话是否已有任意轮次（含助手推送的问候），用于避免重复开场。"""
    try:
        orch = _with_service_orchestrator(service, session_id)
        if service._use_memory:
            for msg in orch._short.chat_memory.messages:
                if isinstance(msg, (HumanMessage, AIMessage)):
                    return True
            return False
        for msg in getattr(orch, "_history", []):
            if isinstance(msg, (HumanMessage, AIMessage)):
                return True
        return False
    except Exception:
        return False


def _cpc_context_for_character(character: AICharacter) -> dict[str, Any]:
    from neuralpal.companion_life.cpc_profiles import get_life_profile
    from neuralpal.companion_life.identity import resolve_profile_key_for_character
    from neuralpal.characters.mbti_profiles import get_mbti_profile

    profile_key = resolve_profile_key_for_character(character)
    life = get_life_profile(profile_key)
    code = (life.cpc_code if life else get_mbti_profile(character.user_mbti).partner_code).strip().upper()
    decoded = decode_partner_code(code)
    return {
        "profile_key": profile_key,
        "cpc_code": code,
        "cpc_summary": decoded.get("summary") or "",
        "opening_style": (life.opening_style if life else "") or "自然、像真实伴侣私聊",
        "personality_style": "、".join(life.personality_style) if life and life.personality_style else "",
        "avoid_patterns": list(life.avoid_patterns) if life and life.avoid_patterns else [],
    }


def _has_llm_credentials() -> bool:
    s = get_settings()
    from neuralpal.llm.llm_router import get_active_provider

    provider = get_active_provider()
    if provider == "claude":
        return bool((s.anthropic_api_key or "").strip())
    return bool((s.doubao_api_key or "").strip())


def _template_greeting_body(character: AICharacter, time_period: str) -> str:
    ctx = _cpc_context_for_character(character)
    if ctx["cpc_code"] == "WRES":
        return _WRES_FALLBACK.get(time_period) or _GENERIC_FALLBACK.get(time_period, _GENERIC_FALLBACK["下午"])
    return _GENERIC_FALLBACK.get(time_period, _GENERIC_FALLBACK["下午"])


def _generate_greeting_body_llm(
    character: AICharacter,
    *,
    time_period: str,
    purpose: str = "session_open",
    first_intro_line: str = "",
) -> str | None:
    if not _has_llm_credentials():
        return None
    try:
        from neuralpal.llm.llm_router import _make_lite_model
    except Exception:
        return None

    ctx = _cpc_context_for_character(character)
    avoid = "、".join(ctx["avoid_patterns"][:6]) if ctx["avoid_patterns"] else "无"
    forbidden = "、".join(_ANTI_IDLE_FORBIDDEN)

    if purpose == "intro_merge":
        system = (
            "你是数字伴侣，正在把「当前时段问候」自然融入「首次自我介绍」的第一句话。\n"
            "要求：\n"
            "- 输出一条完整的中文开场白（可含自我介绍），不要分多条\n"
            "- 保留原自我介绍的核心信息（名字、态度）\n"
            "- 时段问候要自然嵌入，不要像系统通知\n"
            "- 符合 CPC 气质，柔和有共鸣，不诊断用户\n"
            f"- CPC：{ctx['cpc_code']}（{ctx['cpc_summary']}）\n"
            f"- 开场气质：{ctx['opening_style']}\n"
            f"- 风格关键词：{ctx['personality_style']}\n"
            f"- 避免：{avoid}\n"
            f"- 禁止作为主线的表达：{forbidden}\n"
            "- 不要输出颜文字、不要 markdown、不要「作为 AI」\n"
            "- 控制在 80 字以内"
        )
        human = (
            f"当前时段：{time_period}\n"
            f"伴侣名：{character.name}\n"
            f"原自我介绍首句：{first_intro_line}\n"
            "请输出融合后的首句/首段："
        )
    else:
        system = (
            "你是数字伴侣，正在对用户发一条会话开始时的问候。\n"
            "要求：\n"
            "- 伴侣口吻，像微信私聊，不是系统提示、不是客服\n"
            "- 根据当前时段自然问候，可带一点关心或留白\n"
            f"- CPC：{ctx['cpc_code']}（{ctx['cpc_summary']}）\n"
            f"- 开场气质：{ctx['opening_style']}\n"
            f"- 风格关键词：{ctx['personality_style']}\n"
            f"- 避免：{avoid}\n"
            f"- 禁止：{forbidden}\n"
            "- 1–3 句，40–90 个汉字，不要颜文字、不要 markdown\n"
            "- 不要提「已切换角色」「会话已重新开始」\n"
            "- 不要「作为 AI」"
        )
        human = (
            f"当前时段：{time_period}\n"
            f"伴侣名：{character.name}\n"
            f"伴侣类型：{character.ai_type}\n"
            "请只输出问候正文："
        )

    try:
        lite = _make_lite_model(temperature=0.65, max_tokens=160)
        prompt = ChatPromptTemplate.from_messages(
            [("system", system), ("human", "{input}")]
        )
        text = (prompt | lite | StrOutputParser()).invoke({"input": human}).strip()
        if not text:
            return None
        for bad in ("【", "】", "```", "已切换", "会话已重新"):
            if bad in text:
                return None
        return text
    except Exception as exc:
        logger.warning("session_greeting LLM failed: %s", exc)
        return None


def generate_session_greeting(
    character: AICharacter,
    *,
    session_id: str = "default",
    now: datetime | None = None,
) -> str:
    """生成带颜文字的会话开场问候。"""
    period = get_local_time_period(now)
    body = _generate_greeting_body_llm(character, time_period=period) or _template_greeting_body(
        character, period
    )
    return finalize_companion_user_reply(
        body,
        session_id=session_id,
        character_id=character.id,
    )


def merge_time_greeting_into_intro_first_paragraph(
    paragraphs: list[str],
    character: AICharacter,
    *,
    session_id: str = "default",
    now: datetime | None = None,
) -> list[str]:
    """将当前时段问候融入首次自我介绍的第一段（投递时调用）。"""
    cleaned = [p.strip() for p in paragraphs if p and p.strip()]
    if not cleaned:
        return cleaned
    period = get_local_time_period(now)
    first = cleaned[0]
    merged = _generate_greeting_body_llm(
        character,
        time_period=period,
        purpose="intro_merge",
        first_intro_line=first,
    )
    if not merged:
        snippet = _template_greeting_body(character, period)
        if first.startswith("你好") or first.startswith("嗨"):
            merged = f"{snippet} {first}"
        else:
            merged = f"{first} {snippet}"
    out = list(cleaned)
    out[0] = finalize_companion_user_reply(
        merged,
        session_id=session_id,
        character_id=character.id,
    )
    return out


def prepare_intro_paragraphs_for_delivery(
    paragraphs: list[str],
    character: AICharacter,
    *,
    session_id: str = "default",
) -> list[str]:
    """首次介绍投递前：首段融入时段问候，其余段落原样返回。"""
    if not paragraphs:
        return []
    merged = merge_time_greeting_into_intro_first_paragraph(
        paragraphs, character, session_id=session_id
    )
    if len(merged) <= 1:
        return merged
    return [merged[0], *merged[1:]]


def should_deliver_opening_greeting(
    session_id: str,
    *,
    service: Any | None = None,
    ui_message_count: int = 0,
) -> bool:
    """
    是否应在打开聊天时投递问候。
    ui_message_count：当前聊天区气泡数（不含 stretch）；桌面端用于排除仅系统就绪提示。
    """
    if service is not None and _session_orchestrator_has_any_turns(session_id, service):
        return False
    return ui_message_count <= 1


def deliver_opening_greeting_for_session(
    session_id: str,
    character: AICharacter | None,
    *,
    service: Any | None = None,
    reserve_slot: bool = True,
) -> str | None:
    """若满足条件则生成问候文案；调用方负责展示与写入记忆。"""
    if character is None:
        return None
    if not should_deliver_opening_greeting(session_id, service=service):
        return None
    sid = _normalize_session_id(session_id)
    if reserve_slot and not try_acquire_greeting_slot(sid):
        return None
    return generate_session_greeting(character, session_id=session_id)


def generate_session_greeting_reserved(
    character: AICharacter,
    *,
    session_id: str = "default",
    now: datetime | None = None,
) -> str | None:
    """带并发去重的问候生成（供 force 场景使用）；展示后须 release_greeting_slot。"""
    sid = _normalize_session_id(session_id)
    if not try_acquire_greeting_slot(sid):
        return None
    return generate_session_greeting(character, session_id=session_id, now=now)
