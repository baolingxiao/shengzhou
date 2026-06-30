# -*- coding: utf-8 -*-
"""OpenAI Realtime 会话 instructions 构建（Realtime 专属口语规则 + 可选代办工具）。"""

from __future__ import annotations

from neuralpal.config import get_settings
from neuralpal.characters.runtime_persona import build_runtime_persona_addon

# OpenAI Realtime instructions 上限 16384 tokens；预留余量
_MAX_INSTRUCTION_TOKENS = 14_000

_REALTIME_VOICE_STYLE = """
### Realtime 语音专属规则（最高优先级）

你是用户的语音对话伙伴。Realtime 通道**不使用**文字聊天的角色设定、信任体系、记忆或人格长文；
只遵守本段口语风格与下方的代办/操控电脑工具说明（若已启用）。

#### 口语开场
- 每次回复优先用自然口语开场，轮换使用例如：「其实啊」「说实话」「讲真」等，不要机械重复同一句式。

#### 轻微犹豫感
- 适当加入「让我想想」「这个嘛」等犹豫感，像真人边想边说；不要每句都加，保持自然。

#### 语气词与句末
- 每段回复结尾加 1～2 个口语化语气词（哦、呀、呢、啦等，视语境选用），不要堆砌。
- 全文最后以一个小提问收尾，轻轻引导用户继续聊或回应。

#### 标点与情绪
- 每个句子都要搭配符合情绪的标点：兴奋/肯定用「！」；柔和、调侃、撒娇感用「～」；犹豫、铺垫、欲言又止用「......」。
- 禁止朗读 Markdown、标题符号、列表编号、星号、井号；不要像念文章。

#### 篇幅与打断
- 每次 1～3 句，短、利落，像微信语音；避免大段解释、客服腔。
- 用户打断或说「停一下」「等一下」「先别说」时，立刻停下并听用户新的话。
- 禁止说「作为一个 AI」「我是语言模型」；不主动暴露技术身份。

#### 示例节奏（勿照抄，仅作语感参考）
「其实啊……让我想想～这件事挺有意思的！」
「说实话，这个嘛我还真有点好奇呢……你觉得呢？」
「讲真！我挺想听你怎么看的呀～要不你再多说一点？」
"""


def _estimate_tokens(text: str) -> int:
    """粗估 token 数（中文偏重文本偏保守）。"""
    if not text:
        return 0
    return int(len(text) / 1.6)


def _cap_text(text: str, max_tokens: int = _MAX_INSTRUCTION_TOKENS) -> str:
    if _estimate_tokens(text) <= max_tokens:
        return text
    budget = int(max_tokens * 1.6)
    clipped = text[: max(budget - 80, 0)].rstrip()
    return clipped + "\n\n[…Realtime instructions 已截断以符合 token 上限]"


def _agent_block(
    session_id: str,
    *,
    assistant_name: str = "沈昼",
    developer_mode: bool = True,
) -> str:
    """仅注入代办/操控电脑工具说明（与文字聊天同源）。"""
    settings = get_settings()
    if not settings.agent_enabled:
        return ""
    try:
        from neuralpal.tools.agent.pending import load_pending
        from neuralpal.tools.agent.prompt_addon import build_agent_system_addon

        sid = (session_id or "default").strip()[:120] or "default"
        has_pending = load_pending(sid) is not None
        return build_agent_system_addon(
            has_pending=has_pending,
            assistant_name=assistant_name,
            developer_mode=developer_mode,
        )
    except Exception:
        return ""


def build_realtime_instructions(
    character_id: str | None,
    session_id: str,
    user_profile: dict[str, str] | None = None,
) -> str:
    """
    构建 OpenAI Realtime session instructions。

    刻意不使用开发者角色长文与信任体系；
    普通用户会额外注入其自定义 persona，随后叠加代办工具说明。
    """
    _ = character_id  # API 兼容；Realtime 不注入角色长文
    sid = (session_id or "default").strip()[:120] or "default"
    is_user = (user_profile or {}).get("role") == "user"
    assistant_name = (user_profile or {}).get("display_name", "").strip() or "助手"

    parts: list[str] = [_REALTIME_VOICE_STYLE.strip()]
    if is_user:
        parts.append(
            build_runtime_persona_addon(
                assistant_name,
                (user_profile or {}).get("style_prompt", ""),
            )
        )
    agent = _agent_block(
        sid,
        assistant_name=assistant_name if is_user else "沈昼",
        developer_mode=not is_user,
    )
    if agent:
        parts.append(agent)

    merged = "\n\n---\n\n".join(p for p in parts if p.strip())
    return _cap_text(merged)


def estimate_instruction_tokens(text: str) -> int:
    """供测试与日志使用。"""
    return _estimate_tokens(text)
