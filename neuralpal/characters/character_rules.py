# -*- coding: utf-8 -*-
"""角色专属规则加载（信任度系统等），按 data/characters/{角色名}/rules/ 目录解析。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from neuralpal.characters.models import AICharacter

_RULES_MARKER = "[[NEURALPAL_CHARACTER_RULES_V1]]"
_TRUST_MARKER = "[[NEURALPAL_TRUST_SYSTEM_V1]]"
_MEMORY_MARKER = "[[NEURALPAL_CHARACTER_MEMORY_V1]]"
_MEMORY_MAX_CHARS = 12000


def _characters_data_root() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "characters"


def character_data_dir(character: AICharacter) -> Path | None:
    """按角色名称匹配 data/characters/{name}/ 目录。"""
    name = (character.name or "").strip()
    if not name:
        return None
    candidate = _characters_data_root() / name
    if candidate.is_dir():
        return candidate
    return None


def character_rules_dir(character: AICharacter) -> Path | None:
    base = character_data_dir(character)
    if base is None:
        return None
    rules = base / "rules"
    return rules if rules.is_dir() else None


@lru_cache(maxsize=8)
def _load_trust_config(rules_dir_str: str) -> dict[str, Any] | None:
    path = Path(rules_dir_str) / "trust_system.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_trust_state(character: AICharacter) -> dict[str, Any] | None:
    rules_dir = character_rules_dir(character)
    if rules_dir is None:
        return None
    path = rules_dir / "trust_state.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_trust_state(character: AICharacter, state: dict[str, Any]) -> bool:
    rules_dir = character_rules_dir(character)
    if rules_dir is None:
        return False
    path = rules_dir / "trust_state.json"
    try:
        rules_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return True
    except OSError:
        return False


def trust_level_for_points(tp: int, config: dict[str, Any]) -> dict[str, Any]:
    tp = max(0, min(100, int(tp)))
    for level in config.get("levels", []):
        if level.get("tp_min", 0) <= tp <= level.get("tp_max", 100):
            return level
    return {}


def permission_band_for_points(tp: int, config: dict[str, Any]) -> dict[str, Any]:
    """按 TP 百分比匹配聊天权限锁区间。"""
    tp = max(0, min(100, int(tp)))
    for band in config.get("permission_locks", []):
        if band.get("tp_min", 0) <= tp <= band.get("tp_max", 100):
            return band
    return {}


def reply_style_map_for_points(tp: int, config: dict[str, Any]) -> dict[str, Any]:
    """按 TP 匹配信任等级 ↔ 回复特征档位对照。"""
    tp = max(0, min(100, int(tp)))
    for row in config.get("level_reply_style_map", []):
        if row.get("tp_min", 0) <= tp <= row.get("tp_max", 100):
            return row
    return {}


def _format_permission_locks(band: dict[str, Any], config: dict[str, Any]) -> str:
    labels = config.get("permission_lock_labels", {})
    locks = band.get("locks") or {}
    if not locks:
        return "- （无权限锁配置）"
    lines: list[str] = []
    for key, label in labels.items():
        val = locks.get(key)
        if val is True:
            mark = "✅"
        elif val is False:
            mark = "❌"
        elif val in ("light", "occasional"):
            mark = f"轻度/偶尔 ✅ ({val})"
        elif val in ("deep", "active"):
            mark = f"深度/主动 ✅ ({val})"
        else:
            mark = str(val)
        lines.append(f"- {label}：{mark}")
    return "\n".join(lines)


def _gradient_note_for_tp(tp: int, config: dict[str, Any]) -> str:
    for band in config.get("gradient_bands", []):
        if band.get("tp_min", 0) <= tp <= band.get("tp_max", 100):
            return str(band.get("note") or "")
    return ""


def format_trust_status_block(character: AICharacter) -> str:
    """生成当前信任度状态摘要，供 system prompt 注入。"""
    rules_dir = character_rules_dir(character)
    if rules_dir is None:
        return ""

    config = _load_trust_config(str(rules_dir))
    state = load_trust_state(character)
    if not config or not state:
        return ""

    tp = int(state.get("trust_points", config.get("range", {}).get("initial", 10)))
    level_info = trust_level_for_points(tp, config)
    level_name = level_info.get("name") or state.get("level_name") or "未知"
    level_num = level_info.get("level") or state.get("level") or "?"

    style_map = reply_style_map_for_points(tp, config)
    perm_band = permission_band_for_points(tp, config)
    gradient = _gradient_note_for_tp(tp, config)

    style_label = style_map.get("reply_style_label") or "见 reply_style_by_level.md"
    style_tier = style_map.get("reply_style_tier") or "?"
    perm_label = perm_band.get("label") or "?"
    perm_range = f"{perm_band.get('tp_min', '?')}-{perm_band.get('tp_max', '?')}%"
    perm_lines = _format_permission_locks(perm_band, config)

    unlocked = state.get("unlocked_behaviors") or []
    unlocked_text = (
        "\n".join(f"- {item}" for item in unlocked)
        if unlocked
        else "- （尚未记录额外解锁行为，按等级默认约束执行）"
    )

    return f"""{_TRUST_MARKER}
#### 当前信任度状态（运行时 · 勿向用户报数）
- 角色：**{character.name}**
- 当前 TP：**{tp}** / 100
- 当前等级：**{level_num} 级 · {level_name}**
- 关系定位：{level_info.get("relationship", "见 trust_system 规则")}
- 本等级聊天状态：{level_info.get("chat_state", "见 trust_system 规则")}
- **回复特征档位**：第 {style_tier} 档 · {style_label}
- **权限锁区间**：{perm_range}（{perm_label}）
{f"- **渐变提示**：{gradient}" if gradient else ""}

**本 TP 聊天权限锁（每句回复须核对）**
{perm_lines}

**已解锁的渐进行为**
{unlocked_text}

**执行提醒**
- 回复须**严格且仅**符合下方「当前档位 reply_style」与权限锁，不得跳级、不得引用未注入的高档位话术
- 权限锁未 ✅ 的行为一律禁止（工作/有第三者在场时仅事务沟通 ✅）
- 公私双轨：工作/有第三者在场时强制公事公办，私聊才按上表解锁
- 对方冷淡或越界 → 立刻退回上一级回复特征（退一步原则）
- 不向用户复述 TP 或等级名称，自然体现关系远近即可
"""


def reply_style_tiers_for_tp(tp: int, config: dict[str, Any]) -> list[int]:
    """返回当前 TP 应加载的 reply_style 档位编号列表。"""
    tp = max(0, min(100, int(tp)))
    style_map = reply_style_map_for_points(tp, config)
    if not style_map:
        return [1]
    if style_map.get("tier4_overlay") and config.get("reply_style_tier4_includes_tier3", True):
        return [3, 4]
    tier = int(style_map.get("reply_style_tier", 1))
    return [tier]


def _resolve_reply_style_path(rules_dir: Path, config: dict[str, Any], tier: int) -> Path | None:
    files_map = config.get("reply_style_files") or {}
    rel = files_map.get(str(tier)) or files_map.get(tier) or f"reply_styles/tier_{tier}.md"
    path = rules_dir / str(rel)
    return path if path.is_file() else None


def load_reply_style_markdown_for_tp(
    character: AICharacter,
    tp: int | None = None,
) -> str:
    """按当前 TP 仅加载对应档位的 reply_style 文件（四级含三级基底）。"""
    rules_dir = character_rules_dir(character)
    if rules_dir is None:
        return ""

    config = _load_trust_config(str(rules_dir))
    if not config:
        return ""

    if tp is None:
        state = load_trust_state(character)
        if not state:
            return ""
        tp = int(state.get("trust_points", config.get("range", {}).get("initial", 10)))

    tiers = reply_style_tiers_for_tp(tp, config)
    parts: list[str] = []

    shared_rel = config.get("reply_style_shared")
    if shared_rel:
        shared_path = rules_dir / str(shared_rel)
        if shared_path.is_file():
            parts.append(shared_path.read_text(encoding="utf-8").strip())

    for tier in tiers:
        path = _resolve_reply_style_path(rules_dir, config, tier)
        if path is None:
            continue
        parts.append(path.read_text(encoding="utf-8").strip())

    return "\n\n---\n\n".join(p for p in parts if p)


def load_trust_system_markdown(character: AICharacter) -> str:
    """读取 trust_system.md（不含 reply_style 全文）。"""
    rules_dir = character_rules_dir(character)
    if rules_dir is None:
        return ""
    path = rules_dir / "trust_system.md"
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def load_character_rules_markdown(character: AICharacter) -> str:
    """读取角色规则：trust_system + 当前 TP 对应 reply_style 档位。"""
    trust_text = load_trust_system_markdown(character)
    style_text = load_reply_style_markdown_for_tp(character)
    if not trust_text and not style_text:
        return ""
    parts = [p for p in (trust_text, style_text) if p]
    return "\n\n---\n\n".join(parts)


def build_character_rules_addon(character: AICharacter) -> str:
    """生成注入 system 的角色专属规则段（trust_system + 当前档位 reply_style + 信任状态）。"""
    rules_dir = character_rules_dir(character)
    config = _load_trust_config(str(rules_dir)) if rules_dir else None
    state = load_trust_state(character)
    tp: int | None = None
    if config and state:
        tp = int(state.get("trust_points", config.get("range", {}).get("initial", 10)))

    trust_text = load_trust_system_markdown(character)
    style_text = load_reply_style_markdown_for_tp(character, tp)
    status_text = format_trust_status_block(character)

    if not trust_text and not style_text and not status_text:
        return ""

    sections = [f"{_RULES_MARKER}\n### 【角色专属规则 · 必须遵守】"]
    if trust_text:
        sections.append(trust_text)
    if style_text:
        tier_nums = reply_style_tiers_for_tp(tp or 0, config) if config else []
        tier_label = "、".join(f"第{t}档" for t in tier_nums) if tier_nums else "当前档"
        sections.append(
            f"#### 【当前档位 reply_style · {tier_label} · 本句回复唯一依据】\n\n{style_text}"
        )
    if status_text:
        sections.append(status_text)
    return "\n\n".join(sections).strip()


def _strip_memory_frontmatter(text: str) -> str:
    """跳过 character_memory.md 顶部的元数据说明块。"""
    body = text.strip()
    if body.startswith("#"):
        parts = body.split("\n---\n", 1)
        if len(parts) == 2:
            return parts[1].strip()
    return body


def load_character_memory_text(character: AICharacter) -> str:
    """读取角色背景记忆正文（过长时节选）。"""
    base = character_data_dir(character)
    if base is None:
        return ""
    path = base / "character_memory.md"
    if not path.is_file():
        return ""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    text = _strip_memory_frontmatter(raw)
    if len(text) > _MEMORY_MAX_CHARS:
        text = (
            text[:_MEMORY_MAX_CHARS].rstrip()
            + "\n\n…（背景记忆节选；须内化已呈现情节、关系与价值观）"
        )
    return text.strip()


def build_character_memory_addon(character: AICharacter) -> str:
    """生成注入 system 的角色长期背景记忆段。"""
    text = load_character_memory_text(character)
    if not text:
        return ""
    return f"""{_MEMORY_MARKER}
### 【角色长期背景记忆 · 必须内化】
以下为你（**{character.name}**）的自传与人格依据。回复须与其中经历、关系、职业细节与价值观一致。
不要向用户整段复述；仅在合适时机自然流露对应记忆。

{text}
"""


__all__ = [
    "build_character_memory_addon",
    "build_character_rules_addon",
    "character_data_dir",
    "character_rules_dir",
    "format_trust_status_block",
    "load_character_rules_markdown",
    "load_reply_style_markdown_for_tp",
    "load_trust_state",
    "load_trust_system_markdown",
    "permission_band_for_points",
    "reply_style_map_for_points",
    "reply_style_tiers_for_tp",
    "save_trust_state",
    "trust_level_for_points",
]
