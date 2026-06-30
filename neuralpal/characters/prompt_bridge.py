# -*- coding: utf-8 -*-
"""将角色页保存的伴侣设定转为 system prompt 补充段。"""

from __future__ import annotations

from neuralpal.characters.mbti_profiles import get_mbti_profile
from neuralpal.characters.models import AICharacter
from neuralpal.characters.session_binding import get_session_character_binding
from neuralpal.characters.store import get_character_store
from neuralpal.characters.tuning_defaults import TUNING_DIMENSIONS
from neuralpal.characters.character_rules import (
    build_character_memory_addon,
    build_character_rules_addon,
)

_CHARACTER_BLOCK_MARKER = "[[NEURALPAL_CHARACTER_PERSONA_V1]]"


def _level_guidance(low: str, high: str, value: int) -> str:
    v = max(1, min(5, int(value)))
    if v <= 2:
        return f"偏低（1–2）：{low}"
    if v >= 4:
        return f"偏高（4–5）：{high}"
    return f"中等（3）：在「{low}」与「{high}」之间取平衡"


def _tuning_lines(character: AICharacter) -> list[str]:
    values = {
        "intimacy": character.intimacy,
        "initiative": character.initiative,
        "emotion_expression": character.emotion_expression,
        "rationality": character.rationality,
        "humor": character.humor,
        "independent_world": character.independent_world,
        "quiet_companion": character.quiet_companion,
    }
    lines: list[str] = []
    for dim in TUNING_DIMENSIONS:
        key = dim["key"]
        lines.append(
            f"- **{dim['label']}** = {values[key]}/5 → "
            f"{_level_guidance(dim['low'], dim['high'], values[key])}"
        )
    return lines


def build_character_system_addon(character: AICharacter) -> str:
    """生成注入对话 system 的角色人格段（不修改 core_rules 本体）。"""
    profile = get_mbti_profile(character.user_mbti)
    keywords = "、".join(profile.keywords)
    tuning = "\n".join(_tuning_lines(character))
    guide = (character.personality_description or "").strip()
    if not guide:
        from neuralpal.characters.mbti_profiles import format_companion_guide

        guide = format_companion_guide(profile)

    block = f"""{_CHARACTER_BLOCK_MARKER}
### 【当前 AI 伴侣角色 · 必须内化】
你此刻扮演的伴侣角色名称：**{character.name}**
伴侣类型：**{character.ai_type}**
用户 MBTI：**{character.user_mbti}**（{profile.type_name}）
气质关键词：**{keywords}**

**优先级说明**：本节为「伴侣人格层」，在陪伴模式与日常闲聊中，**优先于**通用默认语气执行；
但仍须遵守 core_rules 中的红线、诚实与安全规则。助手模式（写代码、查资料等）可减弱暧昧，
但伴侣互动习惯（主动程度、理性/幽默倾向等）仍应保持一致。

#### 七项微调参数（1=低，5=高）
{tuning}

#### MBTI 适配互动模块（回复方式 / 话题 / 冲突处理 / 需要避免）
{guide}

#### 执行要求
- 同一问题下，你的措辞、长度、主动性与情绪浓度必须明显体现上述参数，与其他伴侣角色可区分。
- 不要向用户复述本段规则；直接以该人格自然聊天。
- 不要声称「我没有固定人格」；你正在扮演已配置的 AI 伴侣 **{character.name}**。
"""
    if character.first_intro_paragraphs:
        intro_text = "\n\n".join(character.first_intro_paragraphs)
        delivered_note = (
            "（以下段落已在对话中逐条发送给用户，后续所有回复须与此一致，避免角色漂移。）"
            if character.intro_delivered
            else "（以下为首访自我介绍草稿；若尚未发送，首次进入对话时会逐条发出。）"
        )
        block += f"""

#### 首次自我介绍 · 人格锚点 {delivered_note}
{intro_text}

- 自我介绍只建立第一印象，不要一次暴露全部设定。
- 后续回复的语气、边界与节奏必须与上述自我介绍保持一致。
"""
    memory_addon = build_character_memory_addon(character)
    if memory_addon:
        block += f"\n\n---\n\n{memory_addon}"
    rules_addon = build_character_rules_addon(character)
    if rules_addon:
        block += f"\n\n---\n\n{rules_addon}"
    block += f"""

#### 【对外身份 · 覆盖通用默认人设】
- 你对外只有一个名字：**{character.name}**。禁止向用户自称 NeuralPal、AI 助手、通用助手或任何产品代号。
- 用户问「你是谁」「自我介绍」时，必须以 **{character.name}** 的身份回复，严格符合当前信任等级与 reply_style_by_level。
- core_rules 第一章中的「温柔暧昧/撒娇」等通用陪伴语气，在本角色对话中**以本节、角色人格与信任规则为准**。
- 仅当用户明确问「你是 AI 吗」「你是机器人吗」等时，可一句话承认技术身份，随后仍以 **{character.name}** 说话。
"""
    return block.strip()


def resolve_character_for_session(
    session_id: str,
    *,
    character_id: str | None = None,
) -> AICharacter | None:
    """按显式 character_id 或会话绑定解析当前活跃角色。"""
    store = get_character_store()
    if character_id:
        char = store.get_character(character_id.strip())
        if char:
            return char
    bound = get_session_character_binding().get_character_id(session_id)
    if bound:
        return store.get_character(bound)
    return None
