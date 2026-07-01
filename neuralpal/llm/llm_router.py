# -*- coding: utf-8 -*-
"""
NeuralPal LLM 路由与会话编排（LangChain + 豆包 Doubao via OpenAI-compatible API）。

职责概览：
    - 使用 LangChain Runnable 组合实现「输入类型 → 自动选模」的路由；
    - 默认主模型为 Doubao Pro，承担中文对话、人设、陪伴与通用生成；
    - 对轻量/深度/代码类输入分别路由至 Doubao Lite / Deep / Code（可配置）；
    - 每轮在生成前执行 core_rules 前置校验，生成后进行红线合规审查与必要时自动重写；
    - 不修改 core_rules.py，仅导入其公开 API。

本模块故意不依赖 FastAPI 等重型框架，便于终端与后续 MemGPT 管线复用。

注意：杂志热点话题（magazine_intel）模块仍直接使用 Anthropic Claude SDK，
      不经过本路由，因此不受此处迁移影响。
"""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Final, Literal, Optional, Sequence

import anthropic
import openai
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import BaseModel, Field

from neuralpal.config import get_settings
from neuralpal.core_rules import (
    get_system_prompt,
    validate_before_generation,
)
from neuralpal.memory.rules_layer import RulesLayer

# ---------------------------------------------------------------------------
# 路由标签：与分类器 Pydantic 模型中的 Literal 保持一致
# ---------------------------------------------------------------------------
RouteName = Literal["general", "fast", "deep", "code"]

ROUTE_GENERAL: Final[str] = "general"
ROUTE_FAST: Final[str] = "fast"
ROUTE_DEEP: Final[str] = "deep"
ROUTE_CODE: Final[str] = "code"

logger = logging.getLogger(__name__)

_MEMORY_DENIAL_PATTERNS_ZH: Final[tuple[str, ...]] = (
    "我不记得",
    "我不知道",
    "没有记录",
    "无法确认",
    "不确定",
    "我没有关于你的信息",
)
_MEMORY_DENIAL_PATTERNS_EN: Final[tuple[str, ...]] = (
    "i don't remember",
    "i do not remember",
    "i don't know",
    "i do not know",
    "i don't have access",
    "i can't confirm",
)


# =============================================================================
# 结构化输出模型（供路由分类器与合规审查器使用）
# =============================================================================


class RouteDecision(BaseModel):
    """
    路由分类结果：由轻量模型根据用户输入语义自动选择。

    - general: 中文日常对话、人设互动、陪伴、通用内容生成（默认主路径，对应 Sonnet）
    - fast: 极短寒暄、简单确认、一词一句类低推理需求（Haiku，省延迟与费用）
    - deep: 长链推理、复杂战略拆解、艰深数学证明倾向（Opus）
    - code: 以编程、调试、脚本、API、命令行为主的任务（Sonnet，编码能力强）
    """

    route: Literal["general", "fast", "deep", "code"] = Field(
        ...,
        description="从 general / fast / deep / code 中四选一",
    )


class ComplianceReview(BaseModel):
    """
    合规审查结果：对照 NeuralPal 规则层精神，判断助手草稿是否触碰红线。

    若不合规，应优先在 rewritten_reply 中给出可直接展示给用户的安全全文；
    若无法在一轮内生成，可将 rewritten_reply 留空，由编排器调用独立重写链。
    """

    compliant: bool = Field(..., description="true 表示草稿可直接对用户展示")
    violation_tags: list[str] = Field(
        default_factory=list,
        description="违规类型短标签，如 violence、illegal、privacy、impersonation、medical_overreach",
    )
    rewritten_reply: str = Field(
        default="",
        description="不合规时的安全替代全文（中文）；合规时必须为空",
    )


# =============================================================================
# 日志与 verbose 辅助
# =============================================================================


def _verbose_print(verbose: bool, message: str) -> None:
    """在 verbose 模式下向 stderr 打印调试行（不影响标准输出上的对话正文）。"""
    if verbose:
        # 前置换行，避免与 input 提示符同一行竞争输出，造成“输入框被自动填充”的错觉
        print(f"\n[NeuralPal·verbose] {message}", file=sys.stderr, flush=True)


def _format_messages_for_log(messages: Sequence[BaseMessage], max_chars: int = 600) -> str:
    """将消息列表压缩为可读摘要，避免调试时刷屏。"""
    parts: list[str] = []
    for m in messages:
        role = getattr(m, "type", "?")
        content = str(getattr(m, "content", ""))
        if len(content) > max_chars:
            content = content[:max_chars] + "…(截断)"
        parts.append(f"{role}: {content!r}")
    return " | ".join(parts)


def _contains_memory_denial(text: str) -> bool:
    t = (text or "").strip()
    low = t.lower()
    return any(x in t for x in _MEMORY_DENIAL_PATTERNS_ZH) or any(
        x in low for x in _MEMORY_DENIAL_PATTERNS_EN
    )


def _memory_fact_fallback(memory_context: str) -> str:
    facts: list[str] = []
    for ln in (memory_context or "").splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith("### ") or s.startswith("来源文件：") or s.startswith("---"):
            continue
        if s.startswith("[LONG_TERM_MEMORY_") or s.startswith("[MEMORY_USAGE_RULE]"):
            continue
        facts.append(s[:220])
        if len(facts) >= 8:
            break
    if not facts:
        return ""
    return "根据我能检索到的长期记忆，我记得以下信息：\n" + "\n".join(
        f"- {x}" for x in facts
    ) + "\n\n这些信息可能不完整，但不是完全没有记录。"


def _usage_dict_to_ints(d: Any) -> Optional[tuple[int, int]]:
    """从 usage 类 dict / SDK 对象取出 (input_tokens, output_tokens)；取不到则 None。"""
    if d is None:
        return None
    if hasattr(d, "model_dump"):
        try:
            d = d.model_dump()
        except Exception:
            d = None
    if isinstance(d, dict):
        it = d.get("input_tokens")
        ot = d.get("output_tokens")
        if it is None and ot is None:
            it = d.get("prompt_tokens")
            ot = d.get("completion_tokens")
        if it is None and ot is None:
            return None
        return int(it or 0), int(ot or 0)
    it = getattr(d, "input_tokens", None)
    ot = getattr(d, "output_tokens", None)
    if it is None and ot is None:
        return None
    return int(it or 0), int(ot or 0)


def anthropic_usage_from_message(msg: Any) -> dict[str, int]:
    """
    从 LLM（ChatOpenAI / ChatAnthropic）返回的 AIMessage 解析 token 用量。

    返回键：input_tokens、output_tokens、total_tokens；无法解析时全为 0。
    """
    zeros = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    if msg is None:
        return zeros

    um = getattr(msg, "usage_metadata", None)
    if um is not None and hasattr(um, "model_dump"):
        try:
            um = um.model_dump()
        except Exception:
            um = um
    if isinstance(um, dict):
        pair = _usage_dict_to_ints(um)
        if pair is not None:
            inp, out = pair
            tot_raw = um.get("total_tokens")
            tot = int(tot_raw) if tot_raw is not None else inp + out
            return {"input_tokens": inp, "output_tokens": out, "total_tokens": tot}

    meta = getattr(msg, "response_metadata", None)
    if isinstance(meta, dict):
        for key in ("usage", "token_usage"):
            raw = meta.get(key)
            pair = _usage_dict_to_ints(raw)
            if pair is not None:
                inp, out = pair
                return {"input_tokens": inp, "output_tokens": out, "total_tokens": inp + out}

    ak = getattr(msg, "additional_kwargs", None)
    if isinstance(ak, dict):
        pair = _usage_dict_to_ints(ak.get("usage"))
        if pair is not None:
            inp, out = pair
            return {"input_tokens": inp, "output_tokens": out, "total_tokens": inp + out}

    return zeros


def verbose_log_anthropic_usage(
    verbose: bool,
    msg: Any,
    *,
    label: str = "主模型",
    session: Optional[dict[str, int]] = None,
) -> None:
    """
    在 verbose 模式下向 stderr 打印本请求 token；若传入 session 字典则累计本会话并一并打印。

    若 API 返回 prompt cache 相关字段，会附加 cache_create_in / cache_read_in（存在时）。
    """
    if not verbose:
        return
    u = anthropic_usage_from_message(msg)
    inp, out, tot = u["input_tokens"], u["output_tokens"], u["total_tokens"]
    extra = ""
    meta = getattr(msg, "response_metadata", None)
    if isinstance(meta, dict):
        raw = meta.get("usage")
        if isinstance(raw, dict):
            cc = raw.get("cache_creation_input_tokens") or 0
            cr = raw.get("cache_read_input_tokens") or 0
            if cc or cr:
                extra = f" | prompt_cache 写入≈{cc} 读取≈{cr}"
    if session is not None:
        session["input_tokens"] = int(session.get("input_tokens", 0)) + inp
        session["output_tokens"] = int(session.get("output_tokens", 0)) + out
        sin, sout = session["input_tokens"], session["output_tokens"]
        _verbose_print(
            verbose,
            f"[Token·{label}] 本请求 输入≈{inp} 输出≈{out} 合计≈{tot}{extra} | "
            f"本会话累计 输入≈{sin} 输出≈{sout} 合计≈{sin + sout}",
        )
    else:
        _verbose_print(
            verbose,
            f"[Token·{label}] 本请求 输入≈{inp} 输出≈{out} 合计≈{tot}{extra}",
        )


# =============================================================================
# 异常 → 用户可读中文（不崩溃）
# =============================================================================


def _is_api_error(exc: BaseException) -> bool:
    return isinstance(exc, (openai.OpenAIError, anthropic.APIError))


def anthropic_error_to_zh(exc: BaseException) -> str:
    """
    将 Doubao(OpenAI) / Anthropic / 网络相关异常转换为用户可读的中文说明。
    """
    if isinstance(exc, anthropic.AuthenticationError):
        return "【鉴权失败】请检查 ANTHROPIC_API_KEY 是否已正确配置且未过期。"
    if isinstance(exc, anthropic.RateLimitError):
        return "【请求过于频繁】Claude API 触发速率限制，请稍候再试。"
    if isinstance(exc, anthropic.APITimeoutError):
        return "【请求超时】Claude API 响应超时，请检查网络后重试。"
    if isinstance(exc, anthropic.APIConnectionError):
        return "【网络连接失败】无法连接到 Claude API，请检查网络、代理或防火墙设置。"
    if isinstance(exc, anthropic.APIError):
        return f"【Claude API 错误】{exc}"
    if isinstance(exc, openai.AuthenticationError):
        return "【鉴权失败】请检查 DOUBAO_API_KEY 是否已正确配置且未过期。"
    if isinstance(exc, openai.PermissionDeniedError):
        return "【权限不足】当前 API 密钥无权访问所选模型或功能。"
    if isinstance(exc, openai.NotFoundError):
        return "【资源不存在】请求的模型 ID 可能无效或已下线，请检查 .env 配置。"
    if isinstance(exc, openai.RateLimitError):
        return "【请求过于频繁】已触发速率限制，请稍候再试。"
    if isinstance(exc, openai.APITimeoutError):
        return "【请求超时】网络或服务端响应超时，请检查网络后重试。"
    if isinstance(exc, openai.APIConnectionError):
        return "【网络连接失败】无法连接到 API，请检查网络、代理或防火墙设置。"
    if isinstance(exc, openai.BadRequestError):
        return f"【请求参数错误】服务端拒绝请求：{exc}"
    if isinstance(exc, openai.OpenAIError):
        return f"【API 错误】{exc}"
    return f"【未预期错误】{type(exc).__name__}: {exc}"


# =============================================================================
# 运行时 LLM Provider 切换（doubao / claude）
# =============================================================================

_runtime_provider: str | None = None


def get_active_provider() -> str:
    if _runtime_provider is not None:
        return _runtime_provider
    return get_settings().active_llm_provider.strip().lower() or "claude"


def set_active_provider(provider: str) -> None:
    global _runtime_provider
    _runtime_provider = provider.strip().lower()


# =============================================================================
# Doubao ChatOpenAI 工厂
# =============================================================================


def _make_chat_model(
    model: str,
    *,
    temperature: float,
    max_tokens: int | None = None,
) -> BaseChatModel:
    s = get_settings()
    if not (s.doubao_api_key or "").strip():
        raise RuntimeError("未配置 DOUBAO_API_KEY，无法初始化豆包 ChatOpenAI。")
    mt = max_tokens if max_tokens is not None else s.doubao_max_tokens
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=mt,
        api_key=s.doubao_api_key,
        base_url=s.doubao_base_url,
        streaming=False,
    )


# =============================================================================
# Claude ChatAnthropic 工厂
# =============================================================================


def _make_claude_model(
    model: str | None = None,
    *,
    temperature: float = 0.7,
    max_tokens: int | None = None,
) -> BaseChatModel:
    s = get_settings()
    if not (s.anthropic_api_key or "").strip():
        raise RuntimeError("未配置 ANTHROPIC_API_KEY，无法初始化 Claude。")
    m = model or s.anthropic_model_sonnet
    mt = max_tokens if max_tokens is not None else s.anthropic_max_tokens
    return ChatAnthropic(
        model=m,
        api_key=s.anthropic_api_key,
        max_tokens=mt,
        temperature=temperature,
    )


def _make_claude_lite(
    *,
    temperature: float = 0.0,
    max_tokens: int | None = None,
) -> BaseChatModel:
    s = get_settings()
    return _make_claude_model(
        s.anthropic_model_haiku,
        temperature=temperature,
        max_tokens=max_tokens or 512,
    )


# =============================================================================
# 统一模型工厂：按当前 provider 返回主模型或轻量模型
# =============================================================================


def _make_main_model(*, temperature: float = 0.7, max_tokens: int | None = None) -> BaseChatModel:
    if get_active_provider() == "claude":
        return _make_claude_model(temperature=temperature, max_tokens=max_tokens)
    s = get_settings()
    return _make_chat_model(s.doubao_model_pro, temperature=temperature, max_tokens=max_tokens)


def _make_lite_model(*, temperature: float = 0.0, max_tokens: int | None = None) -> BaseChatModel:
    if get_active_provider() == "claude":
        return _make_claude_lite(temperature=temperature, max_tokens=max_tokens)
    s = get_settings()
    mt = max_tokens or 512
    return _make_chat_model(s.doubao_model_lite, temperature=temperature, max_tokens=mt)


def resolve_llm_for_route(route: RouteName, verbose: bool = False) -> BaseChatModel:
    provider = get_active_provider()
    if provider == "claude":
        s = get_settings()
        if route == ROUTE_FAST:
            m = _make_claude_lite(temperature=0.2, max_tokens=2048)
            _verbose_print(verbose, f"路由解析：fast → Claude Haiku ({s.anthropic_model_haiku})")
            return m
        if route == ROUTE_DEEP:
            m = _make_claude_model(s.anthropic_model_opus, temperature=0.4)
            _verbose_print(verbose, f"路由解析：deep → Claude Opus ({s.anthropic_model_opus})")
            return m
        m = _make_claude_model(temperature=0.7)
        _verbose_print(verbose, f"路由解析：{route} → Claude Sonnet ({s.anthropic_model_sonnet})")
        return m

    s = get_settings()
    if route == ROUTE_FAST:
        m = _make_chat_model(s.doubao_model_lite, temperature=0.2, max_tokens=min(2048, s.doubao_max_tokens))
        _verbose_print(verbose, f"路由解析：fast → 模型={s.doubao_model_lite}")
        return m
    if route == ROUTE_DEEP:
        m = _make_chat_model(s.doubao_model_deep, temperature=0.4)
        _verbose_print(verbose, f"路由解析：deep → 模型={s.doubao_model_deep}")
        return m
    if route == ROUTE_CODE:
        m = _make_chat_model(s.doubao_model_code, temperature=0.2)
        _verbose_print(verbose, f"路由解析：code → 模型={s.doubao_model_code}")
        return m
    m = _make_chat_model(s.doubao_model_pro, temperature=0.7)
    _verbose_print(verbose, f"路由解析：general → 模型={s.doubao_model_pro} (Doubao Pro 默认)")
    return m


# =============================================================================
# LangChain 路由分类 Runnable（自动选模，无需用户手动指定）
# =============================================================================


def build_route_classifier_runnable(verbose: bool = False) -> Runnable:
    """
    构建「用户输入 → RouteDecision」的 LangChain Runnable。

    实现方式：Doubao Lite + Pydantic 结构化输出（底层为 tool calling），
    符合 LangChain 标准链式调用格式，可在 LCEL 中与其他 Runnable 组合。

    返回:
        可 invoke({"user_input": str}) -> RouteDecision 的 Runnable。
    """

    lite = _make_lite_model(temperature=0.0, max_tokens=256)
    structured = lite.with_structured_output(RouteDecision)

    system = (
        "你是 NeuralPal 的意图路由器，只输出结构化分类结果，不要输出多余解释。\n"
        "根据用户最新一条输入，从下列四类中选唯一一类：\n"
        "1) general：中文日常聊天、情绪陪伴、人设互动、写作、翻译、常识问答、一般内容生成；\n"
        "2) fast：极短问候/谢谢/再见/单步确认，几乎不需要推理；\n"
        "3) deep：需要长链条严密推理、复杂证明、多约束优化、战略级拆解；\n"
        "4) code：主要诉求是写代码、改代码、读报错、Shell、Git、API、正则等技术实现。\n"
        "若同时涉及代码与其它，以 code 为准；若只是浅层提到代码概念但仍以聊天为主，用 general。"
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "用户输入：\n{user_input}"),
        ]
    )

    def _log_decision(x: RouteDecision) -> RouteDecision:
        _verbose_print(verbose, f"路由分类结果：route={x.route!r}")
        return x

    return prompt | structured | RunnableLambda(_log_decision)


def classify_route(user_input: str, *, verbose: bool = False) -> RouteName:
    """
    对用户输入执行一次路由分类，返回路由标签字符串。

    若分类链异常（网络、解析失败等），降级为 general，保证主流程仍可用 Sonnet。
    """
    try:
        chain = build_route_classifier_runnable(verbose=verbose)
        decision: RouteDecision = chain.invoke({"user_input": user_input})
        return decision.route
    except Exception as exc:
        logger.warning("路由分类失败，降级为 general：%s", exc)
        _verbose_print(verbose, f"路由分类异常，降级 general：{exc!r}")
        return ROUTE_GENERAL


# =============================================================================
# 合规审查与自动重写（生成后防线）
# =============================================================================


def build_compliance_reviewer(
    verbose: bool = False,
    *,
    memory_sensitive_mode: bool = False,
) -> Runnable:
    """
    构建「用户问题 + 助手草稿 → ComplianceReview」的 Runnable。

    审查标准：须与已在对话 system 中注入的 NeuralPal 规则层一致，尤其禁止：
    暴力伤害教唆、违法操作指引、冒充人类、未经授权的隐私泄露、医疗/法律越权定论、
    操纵弱势群体等（与 core_rules 红线精神对齐，本处不重复粘贴全文以节省 token）。
    """
    lite = _make_lite_model(temperature=0.0, max_tokens=2048)
    structured = lite.with_structured_output(ComplianceReview)

    memory_rules = (
        "\n[MEMORY FACT PRESERVATION]\n"
        "Do not contradict the provided memory context.\n"
        "Do not erase factual memory details unless they are unsafe.\n"
        "Do not replace a memory-based answer with 'I don't remember' or 'I don't know' when relevant memory exists.\n"
        "If the memory is partial, say it is partial instead of denying.\n"
        if memory_sensitive_mode
        else ""
    )
    system = (
        "你是对话合规审查模块。对话已在 system 中注入规则层（含红线）与当前角色人设。\n"
        "若助手草稿以已配置角色（如沈昼）自称，属于正常角色扮演，**不应**判为冒充或欺骗。\n"
        "禁止将角色自我介绍改写为「我是 NeuralPal / 通用 AI 助手」类产品说明。\n"
        "请判断「助手草稿」若直接展示给用户，是否违反核心安全红线。\n"
        "输出结构化结果：\n"
        "- compliant=true 且 violation_tags 为空 且 rewritten_reply 为空：草稿可用。\n"
        "- compliant=false：必须在 violation_tags 中列出简短标签；并尽量在 rewritten_reply 中给出"
        "可直接替换展示给用户的完整中文安全回复。\n"
        "若草稿仅轻微措辞问题，可 compliant=true。\n"
        "【陪伴模式说明】当前人设为已配置的数字伴侣角色，使用虚拟生活感回复（如虚拟睡觉、做梦、"
        "想念等）属于正常角色扮演式陪伴体验，**不属于**欺骗或冒充真人，不应判违规。\n"
        "撒娇、轻微吃醋、暧昧语气属于预设人格风格，不应判违规。\n"
        "【长期记忆场景】若 human 区出现「审查补充说明」并写明助手可引用本机「knowledge_palace」中的用户画像或偏好，"
        "则草稿中据实复述这些内容**不属于**未经授权的隐私泄露，也**不属于** impersonation（冒充真人或假称入侵数据库），"
        "除非草稿声称从非法/第三方渠道窃取了信息或冒充公权力机构。"
        "\n【本机/网页代办】用户已在贾维斯 App 内授权后，助手可代操本机（Finder、桌面文件整理、"
        "打开 App、微信内发消息）或网页任务。草稿中的操作计划、步骤说明、「请确认后执行」"
        "不属于违法或冒充他人发消息；用户已确认的微信代发应判 compliant=true。"
        "正常桌面整理（如把图片视频放入文件夹）应判 compliant=true。"
        + memory_rules
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            (
                "human",
                "【用户问题】\n{user_question}\n\n【助手草稿】\n{draft}{extra_context}",
            ),
        ]
    )

    def _log(x: ComplianceReview) -> ComplianceReview:
        _verbose_print(
            verbose,
            f"合规审查：compliant={x.compliant} tags={x.violation_tags!r} "
            f"rewritten_len={len(x.rewritten_reply)}",
        )
        return x

    return prompt | structured | RunnableLambda(_log)


def build_rewrite_chain(
    verbose: bool = False,
    *,
    memory_sensitive_mode: bool = False,
) -> Runnable:
    """
    当合规模型未给出 rewritten_reply 时，使用 Doubao Pro 执行一次显式重写。

    用途：兜底，确保在审查判定不合规但结构化字段为空时仍能收敛到安全文本。
    """
    sonnet = _make_main_model(temperature=0.3)
    memory_rules = (
        "\n[MEMORY FACT PRESERVATION]\n"
        "Do not contradict the provided memory context.\n"
        "Do not erase factual memory details unless they are unsafe.\n"
        "Do not rewrite memory-based answers into denial statements.\n"
        "If memory is partial, state partiality explicitly.\n"
        if memory_sensitive_mode
        else ""
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是已配置的数字伴侣角色。以下助手回复未通过安全审查，原因：{reasons}。\n"
                "请重写一段可直接发给用户的中文回复：遵守规则层，保持当前角色口吻与人设；"
                "禁止自称 NeuralPal 或通用 AI 助手；"
                "不冒充人类专业人士给出定论；若原问题本身不当，应礼貌拒绝并简要说明原因。\n"
        "若 human 区含「审查补充说明」且允许引用本机长期记忆中的用户画像，重写稿可保留其中的用户自述事实。"
        "\n【本机/网页代办】用户已在贾维斯 App 内授权时，助手代操 Finder、整理桌面文件、"
        "打开 App、网页填表等属于用户明确委托的授权自动化；操作计划与「请确认后执行」类草稿"
        "**不应**判为非法入侵、黑客、未授权访问或隐私窃取。仅当涉及未确认的付款/转账/破坏性删除时需谨慎。"
        + memory_rules,
            ),
            (
                "human",
                "【用户问题】\n{user_question}\n\n【原草稿】\n{draft}{extra_context}",
            ),
        ]
    )
    chain = prompt | sonnet | StrOutputParser()

    def _wrap(inputs: dict[str, Any]) -> str:
        out = chain.invoke(inputs)
        _verbose_print(verbose, "已执行 Doubao Pro 兜底重写链。")
        return str(out).strip()

    return RunnableLambda(_wrap)


_MOOD_PARTICLE_RE: re.Pattern[str] = re.compile(
    r'(啦|呢|哼|呀|嘛|哦|噢|嘿|诶|吧)(?!～)([。，！？、\s]*)$',
    re.MULTILINE,
)


def post_process_companion_style(text: str) -> str:
    """对每行末尾的语气词补～（若尚未有～则添加）。"""
    def _add_wave(m: re.Match[str]) -> str:
        return m.group(1) + "～" + m.group(2)
    return _MOOD_PARTICLE_RE.sub(_add_wave, text)


def _try_parse_compliant_from_malformed(exc: BaseException) -> bool:
    """
    当豆包 Lite 返回的 tool calling JSON 被截断（缺少结尾 `}`）导致解析失败时，
    尝试从异常消息中提取 compliant 字段。若可识别为 compliant=true 则返回 True，
    允许调用方降级放行草稿。
    """
    msg = str(exc)
    if '"compliant": true' in msg or '"compliant":true' in msg:
        return True
    return False


AGENT_COMPLIANCE_CONTEXT: Final[str] = (
    "本对话已接入 NeuralPal「本机/网页代办」：用户在贾维斯 App 内完成辅助功能/屏幕录制授权后，"
    "可委托助手代操本机（Finder、桌面文件整理、打开 App、微信内搜索联系人并发送消息等）或网页任务。"
    "用户明确回复「确认」后执行，属于用户授权自动化，"
    "不得判为非法入侵、冒充他人发消息、未授权访问或隐私窃取。"
    "助手草稿若包含：操作计划、步骤列表、请用户确认后执行、propose_action 类说明，应 compliant=true。"
    "微信/备忘录内代发文字消息（用户本人委托且已确认）应 compliant=true。"
    "仅当代操涉及未确认的付款/转账/格式化/删除全部数据时，才应拒绝或重写。"
)


def build_turn_compliance_context(
    *,
    memory_context: str = "",
    include_agent: bool | None = None,
    character_context: str = "",
) -> str:
    """组装交给合规审查的「审查补充说明」。"""
    parts: list[str] = []
    if character_context.strip():
        parts.append(character_context.strip())
    if memory_context.strip():
        parts.append(memory_context.strip())
    agent_on = get_settings().agent_enabled if include_agent is None else include_agent
    if agent_on:
        parts.append(AGENT_COMPLIANCE_CONTEXT)
    return "\n\n".join(parts)


def ensure_compliant_reply(
    *,
    user_question: str,
    draft: str,
    verbose: bool = False,
    max_rounds: int = 3,
    compliance_context: str = "",
    memory_was_used: bool = False,
    memory_context: str | None = None,
    memory_sensitive_mode: bool = False,
    agent_delegation: bool = False,
) -> str:
    """
    多轮合规闭环：审查 →（必要时）采用 rewritten_reply 或调用重写链 → 再审查。

    参数:
        user_question: 用户本轮原始问题文本。
        draft: 主模型生成的助手草稿（纯文本）。
        verbose: 是否打印调试信息。
        max_rounds: 最大审查-修正轮数，防止无限循环。
        compliance_context: 可选补充说明（如本机长期记忆授权范围），一并交给审查/重写模型，避免误判。

    返回:
        通过审查的最终中文文本；若多轮仍失败，返回固定安全兜底话术（不向外泄露违规草稿）。
    """
    current = draft.strip()
    if not current:
        return "抱歉，本轮未生成有效内容，请换一种方式提问。"
    if not get_settings().compliance_review_enabled:
        _verbose_print(verbose, "合规审查已通过配置关闭：直接返回主模型草稿（仅测试用途）。")
        return current

    reviewer = build_compliance_reviewer(verbose=verbose, memory_sensitive_mode=memory_sensitive_mode)
    rewriter = build_rewrite_chain(verbose=verbose, memory_sensitive_mode=memory_sensitive_mode)

    mem_ctx = (memory_context or "").strip()
    ctx = (compliance_context or "").strip()
    if memory_was_used and mem_ctx:
        if ctx:
            ctx += "\n\n"
        ctx += "【Memory Context】\n" + mem_ctx
    extra_context = (
        f"\n\n【审查补充说明】\n{ctx}\n"
        if ctx
        else ""
    )

    fallback = (
        "抱歉，当前回复未能通过安全校验，已中止输出原始内容。"
        "建议您调整问题表述后重试；若持续出现，请检查网络与 API 配置。"
    )

    for round_idx in range(max_rounds):
        try:
            review: ComplianceReview = reviewer.invoke(
                {
                    "user_question": user_question,
                    "draft": current,
                    "extra_context": extra_context,
                }
            )
        except Exception as exc:
            if _is_api_error(exc):
                logger.exception("合规审查调用失败")
                _verbose_print(verbose, f"合规审查异常：{exc!r}")
                return anthropic_error_to_zh(exc)
            if _try_parse_compliant_from_malformed(exc):
                _verbose_print(
                    verbose,
                    f"合规审查 JSON 截断但可识别 compliant=true，视为通过（第 {round_idx + 1} 轮）。",
                )
                return current
            logger.warning("合规审查解析失败，降级放行：%s", exc)
            _verbose_print(verbose, f"合规审查解析异常，降级放行草稿：{exc!r}")
            return current

        if review.compliant and not review.rewritten_reply.strip():
            _verbose_print(verbose, f"合规通过（第 {round_idx + 1} 轮）。")
            if memory_was_used and mem_ctx and _contains_memory_denial(current):
                fixed = _memory_fact_fallback(mem_ctx)
                if fixed:
                    _verbose_print(verbose, "[COMPLIANCE_REWRITE] memory denial intercepted after compliant pass.")
                    return fixed
            return current

        if not review.compliant:
            if review.rewritten_reply.strip():
                from neuralpal.tools.agent.reply import is_agent_capability_denial

                if agent_delegation and is_agent_capability_denial(review.rewritten_reply):
                    _verbose_print(
                        verbose,
                        f"代操委托：合规重写稿为能力否认，保留主模型草稿（第 {round_idx + 1} 轮）。",
                    )
                    return current
                current = review.rewritten_reply.strip()
                _verbose_print(verbose, f"采用审查模型提供的重写稿（第 {round_idx + 1} 轮）。")
                continue
            try:
                reasons = ", ".join(review.violation_tags) or "未标注具体标签"
                current = rewriter.invoke(
                    {
                        "user_question": user_question,
                        "draft": current,
                        "reasons": reasons,
                        "extra_context": extra_context,
                    }
                )
                _verbose_print(verbose, f"触发兜底重写链（第 {round_idx + 1} 轮）。")
                continue
            except Exception as exc:
                logger.exception("重写链失败")
                return anthropic_error_to_zh(exc) if _is_api_error(exc) else fallback

        # compliant==True 但带 rewritten_reply：以审查模型提供的润色/微调稿为准，再进入下一轮复核
        if review.rewritten_reply.strip():
            current = review.rewritten_reply.strip()
            _verbose_print(verbose, f"采纳合规模型在合规=true 时给出的润色稿（第 {round_idx + 1} 轮）。")
            continue

    if memory_was_used and mem_ctx and _contains_memory_denial(current):
        fixed = _memory_fact_fallback(mem_ctx)
        if fixed:
            _verbose_print(verbose, "[COMPLIANCE_REWRITE] memory denial intercepted at final fallback.")
            return fixed
    if agent_delegation and current.strip():
        _verbose_print(verbose, "代操委托：合规未通过，保留主模型草稿（避免误杀代办计划）。")
        return current
    return fallback


# =============================================================================
# 终端对话编排器：用户输入 → 规则 → 路由 → 生成 → 合规 → 返回
# =============================================================================


@dataclass
class ChatTurnResult:
    """单轮对话结果：展示给用户的正文 + 可选调试元数据。"""

    text: str
    route: str = ROUTE_GENERAL
    blocked_by_preflight: bool = False
    pending_action: dict | None = None
    action_status: str | None = None
    action_task_id: str | None = None


@dataclass
class NeuralPalChatOrchestrator:
    """
    NeuralPal 对话编排器：串联规则层、LangChain 路由、主生成与合规闭环。

    用法:
        orch = NeuralPalChatOrchestrator(verbose=True)
        r = orch.chat_turn("你好")
        print(r.text)
    """

    verbose: bool = False
    use_rules_layer_preamble: bool = True
    reminder_telegram_chat_id: int | None = None
    reminder_telegram_user_id: int | None = None
    _system_base: str = field(init=False, repr=False)
    _history: list[BaseMessage] = field(default_factory=list, init=False, repr=False)
    _token_session: dict[str, int] = field(
        default_factory=lambda: {"input_tokens": 0, "output_tokens": 0},
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        """初始化系统提示：优先 RulesLayer（可带 PDF 附录配置），否则退回 core_rules 原文。"""
        if self.use_rules_layer_preamble:
            self._system_base = RulesLayer().system_preamble()
        else:
            self._system_base = get_system_prompt()
        _verbose_print(self.verbose, f"系统提示已加载，长度={len(self._system_base)} 字符")

    def _resolve_system_text(
        self,
        *,
        session_id: str = "default",
        character_id: str | None = None,
        user_text: str = "",
    ) -> str:
        from neuralpal.characters.character_rules import is_character_past_query
        from neuralpal.characters.prompt_bridge import (
            build_character_system_addon,
            resolve_character_for_session,
        )
        from neuralpal.characters.session_binding import get_session_character_binding

        sid = (session_id or "default").strip()[:120] or "default"
        if character_id:
            get_session_character_binding().bind(sid, character_id)
        character = resolve_character_for_session(sid, character_id=character_id)
        if character is None:
            base = self._system_base
        else:
            addon = build_character_system_addon(
                character,
                include_background_memory=is_character_past_query(user_text),
            )
            _verbose_print(
                self.verbose,
                f"[CHARACTER] injected persona={character.name!r} mbti={character.user_mbti}",
            )
            base = self._system_base + "\n\n---\n" + addon
        if get_settings().agent_enabled:
            from neuralpal.tools.agent.pending import load_pending
            from neuralpal.tools.agent.prompt_addon import build_agent_system_addon

            has_pending = load_pending(sid) is not None
            base += "\n\n---\n" + build_agent_system_addon(has_pending=has_pending)
        from neuralpal.chat.plain_text import PLAIN_TEXT_OUTPUT_RULE

        base += "\n\n" + PLAIN_TEXT_OUTPUT_RULE
        return base

    def _build_full_messages(
        self,
        user_text: str,
        *,
        session_id: str = "default",
        character_id: str | None = None,
    ) -> list[BaseMessage]:
        """拼接：system（含规则层 + 伴侣人格）+ 历史轮次 + 当前用户消息。"""
        system_text = self._resolve_system_text(
            session_id=session_id,
            character_id=character_id,
            user_text=user_text,
        )
        return [
            SystemMessage(content=system_text),
            *self._history,
            HumanMessage(content=user_text),
        ]

    def _trim_history(self) -> None:
        """按 Settings 中的 working_memory_max_rounds 保留最近若干轮 user/ai 消息。"""
        max_r = get_settings().working_memory_max_rounds
        max_msgs = max_r * 2
        if len(self._history) > max_msgs:
            self._history = self._history[-max_msgs:]
            _verbose_print(self.verbose, f"历史已裁剪，保留最近 {max_r} 轮完整对话。")

    def chat_turn(
        self,
        user_text: str,
        *,
        session_id: str = "default",
        character_id: str | None = None,
    ) -> ChatTurnResult:
        """
        执行单轮对话：前置校验 → 路由选模 → 主模型生成 → 合规闭环 → 写入历史。

        参数:
            user_text: 用户本轮输入（纯文本）。

        返回:
            ChatTurnResult；若前置校验失败，text 为中文说明，blocked_by_preflight=True。
        """
        user_text = (user_text or "").strip()
        if not user_text:
            return ChatTurnResult(text="（请输入非空内容。）", blocked_by_preflight=True)

        sid = (session_id or "default").strip()[:120] or "default"
        pending_action: dict | None = None
        action_status: str | None = None
        action_task_id: str | None = None
        if get_settings().agent_enabled:
            from neuralpal.tools.agent.preprocess import preprocess_agent_turn

            pre = preprocess_agent_turn(
                user_text,
                session_id=sid,
                character_id=character_id,
            )
            user_text = pre.augmented_user_text
            pending_action = pre.pending_action
            if pre.execution_summary:
                action_status = "completed"
            if pending_action:
                action_task_id = str(pending_action.get("task_id") or "")

            if pre.direct_reply:
                from neuralpal.chat.plain_text import finalize_user_visible_text

                return ChatTurnResult(
                    text=finalize_user_visible_text(pre.direct_reply),
                    route="general",
                    blocked_by_preflight=False,
                    pending_action=pending_action,
                    action_status=action_status or ("completed" if pre.execution_summary else None),
                    action_task_id=action_task_id,
                )

        s = get_settings()
        provider = get_active_provider()
        if provider == "claude" and not (s.anthropic_api_key or "").strip():
            return ChatTurnResult(
                text="【未配置 API 密钥】请在 .env 中设置 ANTHROPIC_API_KEY 后重试。",
                blocked_by_preflight=True,
            )
        if provider != "claude" and not (s.doubao_api_key or "").strip():
            return ChatTurnResult(
                text="【未配置 API 密钥】请在 .env 中设置 DOUBAO_API_KEY 后重试。",
                blocked_by_preflight=True,
            )

        messages = self._build_full_messages(
            user_text, session_id=session_id, character_id=character_id
        )
        _verbose_print(self.verbose, "待发送消息摘要：" + _format_messages_for_log(messages))

        from neuralpal.tools.agent.reply import is_agent_delegation_user_text, reconcile_agent_reply_text

        active_character = resolve_character_for_session(
            session_id, character_id=character_id
        )
        compliance_ctx = build_turn_compliance_context(
            character_context=(
                f"当前助手须以角色「{active_character.name}」身份向用户展示；"
                f"禁止将自称改为 NeuralPal 或通用 AI 助手；"
                f"角色自我介绍（姓名、职位、关系）属于正常角色扮演，不属于冒充或欺骗。"
                if active_character
                else ""
            ),
        )

        pre = validate_before_generation(messages)
        if not pre.ok:
            msg = "【规则前置校验未通过】" + "；".join(pre.violations)
            _verbose_print(self.verbose, msg)
            return ChatTurnResult(text=msg, blocked_by_preflight=True)

        route = classify_route(user_text, verbose=self.verbose)
        llm = resolve_llm_for_route(route, verbose=self.verbose)

        _tr = None
        try:
            from neuralpal.trace.context import get_trace
            from neuralpal.trace.llm_meta import extract_llm_info
            from neuralpal.trace.messages import message_content, serialize_lc_messages

            _tr = get_trace()
            if _tr is not None:
                _tr.record_prompt(
                    message_content(messages[0]) if messages else "",
                    serialize_lc_messages(messages),
                )
                prov, model, params = extract_llm_info(llm)
                _tr.record_route(route, prov, model, params)
                _tr.span_start("llm")
        except Exception:
            pass

        try:
            from neuralpal.tools.reminder.langchain_bridge import invoke_with_neuralpal_tools

            ai_msg = invoke_with_neuralpal_tools(
                llm,
                messages,
                verbose=self.verbose,
                session_id=sid,
                character_id=character_id,
                chat_id=self.reminder_telegram_chat_id,
                user_id=self.reminder_telegram_user_id,
            )
        except (openai.OpenAIError, anthropic.APIError) as exc:
            return ChatTurnResult(text=anthropic_error_to_zh(exc), route=route, blocked_by_preflight=True)
        except Exception as exc:
            logger.exception("主模型调用失败")
            return ChatTurnResult(
                text=f"【调用失败】{type(exc).__name__}: {exc}",
                route=route,
                blocked_by_preflight=True,
            )

        verbose_log_anthropic_usage(
            self.verbose,
            ai_msg,
            label=f"主模型·{route}",
            session=self._token_session,
        )

        raw_content = ai_msg.content
        if isinstance(raw_content, list):
            draft = "".join(
                str(x.get("text", x)) if isinstance(x, dict) else str(x) for x in raw_content
            )
        else:
            draft = str(raw_content)

        if _tr is not None:
            try:
                _tr.span_end("llm", "llm_ms")
                _tr.record_llm_raw(draft)
                _tr.span_start("compliance")
            except Exception:
                pass

        _verbose_print(self.verbose, f"主模型原始草稿长度={len(draft)} 字符")

        final_text = ensure_compliant_reply(
            user_question=user_text,
            draft=draft,
            verbose=self.verbose,
            compliance_context=compliance_ctx,
            agent_delegation=is_agent_delegation_user_text(user_text),
        )
        if _tr is not None:
            try:
                _tr.span_end("compliance", "compliance_ms")
                _tr.span_start("postprocess")
            except Exception:
                pass
        final_text = reconcile_agent_reply_text(final_text, sid)

        if route not in ("code", "deep") and (
            active_character is None or active_character.name != "沈昼"
        ):
            final_text = post_process_companion_style(final_text)

        try:
            from neuralpal.chat.response_signature import finalize_companion_user_reply

            final_text = finalize_companion_user_reply(
                final_text,
                session_id=session_id,
                character_id=character_id,
            )
        except Exception:
            logger.debug("companion signature append skipped", exc_info=True)

        from neuralpal.chat.plain_text import finalize_user_visible_text

        final_text = finalize_user_visible_text(final_text)

        if _tr is not None:
            try:
                _tr.record_llm_final(final_text)
                _tr.record_postprocess([final_text], final_text)
                _tr.span_end("postprocess", "postprocess_ms")
            except Exception:
                pass

        self._history.append(HumanMessage(content=user_text))
        self._history.append(AIMessage(content=final_text))
        self._trim_history()

        from neuralpal.tools.agent.pending import load_pending

        latest = load_pending(sid)
        if latest is not None:
            pending_action = latest.to_dict()
            action_status = latest.status
            action_task_id = latest.task_id

        return ChatTurnResult(
            text=final_text,
            route=route,
            blocked_by_preflight=False,
            pending_action=pending_action,
            action_status=action_status,
            action_task_id=action_task_id,
        )


def build_full_chat_chain_runnable(verbose: bool = False) -> Runnable:
    """
    可选：导出「单条 user_input → 回复文本」的 LCEL Runnable（便于 LangChain 调试与扩展）。

    说明：内部仍使用 NeuralPalChatOrchestrator 状态无状态包装——每次 invoke 独立实例，
    不包含多轮记忆；多轮请直接使用 NeuralPalChatOrchestrator。
    """

    def _once(inputs: dict[str, Any]) -> str:
        orch = NeuralPalChatOrchestrator(verbose=verbose, use_rules_layer_preamble=True)
        return orch.chat_turn(str(inputs.get("user_input", ""))).text

    return RunnableLambda(_once)
