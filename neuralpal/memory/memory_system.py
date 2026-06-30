# -*- coding: utf-8 -*-
"""
NeuralPal 四层记忆殿堂 —— 与「knowledge_palace」本地目录 + Chroma 海马体向量库双存储联动。

架构说明（与需求逐条对应）：
    ① 规则层（前额叶）：使用 core_rules.get_system_prompt() 置于每轮 system 最顶部；并同步备份至
       「knowledge_palace/01_核心规则库」。
    ② 长期记忆层（海马体）：纯文本文件写入「knowledge_palace」子目录 + 向量写入 Chroma
       collection=neuralpal_long_term_memory，持久化目录默认 ./neuralpal_memory_db。
    ③ 短期工作记忆层：ConversationBufferMemory 仍全量保留原文（便于滚动归档）；可选「混合短期」：
       注入主模型时仅最近 N 轮全文，更旧在缓冲区内压成一条摘要；满 k 轮时先弹出最旧一轮，短摘要入缓存、
       结构化包双写 ②，再拼剩余与当前用户输入（阶段二滚动归档）。
    ④ 瞬时记忆层：会话内 TransientBuffer，仅本轮草稿，chat_turn 结束时清空不落盘。

主对话编排类：NeuralPalMemoryPalaceOrchestrator
    固定管线：用户输入 →（满 k 轮则轮首滚动归档）→ 规则层 → 记忆桥接说明 → Chroma 动态门控召回
    → 读knowledge_palace原文 → 拼混合/完整短期历史 → Claude → 合规 → 短期追加本轮 → 可选全文双写 → 返回。

注意：
    - 不修改 `core_rules.py` 正文；规则层仅通过 `get_system_prompt()` / `validate_before_generation` 打通。
    - 路由与合规通过同包内 import 复用 `neuralpal/llm/llm_router.py`；可选提醒工具仅在开关开启时经
      `neuralpal.tools.reminder.langchain_bridge` 对主模型 `invoke` 做增量包裹，不改变路由/合规/记忆管线顺序。
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Final, List, Literal, Optional, Tuple

import anthropic
import openai

# 尽早关闭 Chroma 产品遥测，避免与 posthog 版本不兼容时在 stderr 刷屏
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

from langchain.memory import ConversationBufferMemory
from langchain_chroma import Chroma
from neuralpal.memory.chroma_embeddings import get_memory_embeddings
from neuralpal.memory.constants import LONG_TERM_COLLECTION_NAME
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from neuralpal.config import get_settings
from neuralpal.memory.palace_layout import (
    DIR_MEDIUM,
    DIR_RULES,
    ensure_dual_palace_layout,
    ensure_palace_layout,
    get_palace_root,
    list_classifier_subdirs,
    publish_palace_file,
    resolve_memory_subdir,
    resolve_palace_file_path,
    sync_short_term_snapshot,
)
from neuralpal.memory.memory_maintenance import MemoryMaintenanceService
from neuralpal.core_rules import (
    get_system_prompt,
    get_system_prompt_fingerprint_sha256,
    validate_before_generation,
)
from neuralpal.characters.models import AICharacter
from neuralpal.characters.prompt_bridge import build_character_system_addon, resolve_character_for_session
from neuralpal.memory.transient import TransientBuffer
from neuralpal.memory.chroma_runtime import get_chroma_client
from neuralpal.llm.llm_router import (
    ROUTE_GENERAL,
    _is_api_error,
    _make_chat_model,
    _make_lite_model,
    anthropic_error_to_zh,
    anthropic_usage_from_message,
    build_turn_compliance_context,
    classify_route,
    ensure_compliant_reply,
    get_active_provider,
    post_process_companion_style,
    resolve_llm_for_route,
    verbose_log_anthropic_usage,
)
from neuralpal.tools.agent.reply import is_agent_delegation_user_text, reconcile_agent_reply_text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量：默认knowledge_palace子目录（仅创建不存在的目录，不删除用户已有内容）
# ---------------------------------------------------------------------------

# ② 动态召回：明显寒暄整句 → 跳过 Chroma；含记忆相关线索 → 强制召回
_LTM_SKIP_RECALL_EXACT: Final[frozenset[str]] = frozenset(
    {
        "你好",
        "您好",
        "嗨",
        "hi",
        "hello",
        "在吗",
        "早",
        "晚安",
        "谢谢",
        "谢了",
        "好的",
        "好",
        "嗯",
        "哦",
        "噢",
        "行",
        "ok",
        "okay",
        "bye",
        "再见",
        "拜拜",
        "对的",
        "是的",
        "没错",
        "可以",
        "没问题",
        "收到",
        "明白",
        "了解",
        "继续",
        "嗯嗯",
    }
)

_LTM_RECALL_HINT_SUBSTR: Final[tuple[str, ...]] = (
    "记住",
    "记忆",
    "谁",
    "名字",
    "叫什么",
    "称呼",
    "偏好",
    "习惯",
    "之前",
    "上次",
    "刚才",
    "画像",
    "档案",
    "日程",
    "睡眠",
    "咖啡",
    "喝什么",
    "几点",
    "何时",
    "什么时候",
    "不要忘了",
    "还记得",
)

_IDENTITY_QUERY_HINTS_ZH: Final[tuple[str, ...]] = (
    "我是谁",
    "你记得我吗",
    "我的名字",
    "我叫什么",
    "我的身份",
    "我的专业",
    "我的学校",
    "我的偏好",
    "我的习惯",
    "我的审美",
    "审美",
    "气质",
    "生活方式",
    "用户画像",
    "我的画像",
    "你知道我",
    "你了解我",
    "我的 sop",
    "我的项目",
    "我之前说过什么",
    "我喜欢什么样的回答",
)
_IDENTITY_QUERY_HINTS_EN: Final[tuple[str, ...]] = (
    "who am i",
    "do you remember me",
    "my name",
    "my identity",
    "my profile",
    "my preferences",
    "my sop",
    "my projects",
    "what do you know about me",
)
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

# 默认子目录：仅在目录不存在时 mkdir，不删除、不重命名用户已有文件夹。
# 命名与 NeuralPal「knowledge_palace」约定一致；自动分类亦可选用列表外的新目录名（将自动创建）。
DEFAULT_PALACE_SUBDIRS: Final[tuple[str, ...]] = (
    "01_核心规则库",
    "02_NeuralPal项目专属知识库",
    "03_用户专属知识库",
    "04_技术栈库",
    "05_风险库",
    "06_参考资料库",
    "07_用户专属画像库",
    "08_待整理",
    "09_对话历史归档",
)

# 规则层之后、② 召回之前注入：避免模型否认已注入的短期/长期记忆机制（不改变 core_rules 文件本体）。
_MEMORY_CAPABILITY_BRIDGE: Final[str] = """
---
### 【NeuralPal 记忆子系统｜行为须与此一致】
你运行在「四层记忆殿堂」编排链路中，拥有真实的记忆能力。**禁止**向用户声称「我没有任何记忆」「无法保存偏好」等：
- **③ 短期工作记忆**：消息列表中的 Human/Assistant 历史即为本会话保留的最近若干轮完整原文。若历史中已出现用户偏好、约定或事实，你**必须**据此作答。在陪伴模式下，可自然地引用对话中的短期信息（如用户刚说"我刚醒"，后续可说"刚醒就来找我，还算你有良心"）。
- **② 长期记忆**：若 system 中出现「### ② 海马体·长期记忆召回」段落，为本地「knowledge_palace」与向量库检索到的真实片段，须**据实参考**。
- **未出现②段落时**：仅表示本轮未命中已存条目，不是系统不能长期存储。
- **虚拟记忆规则**：在陪伴模式下，你可以自然地记住和引用对话中的信息。例如用户说"我昨天很累"，后面可以说"那今天别太硬撑""我会心疼的"。

### 【用户已确认的长期偏好】
- 用户喜欢微信式短句回复（2-5行，每行≤15字）。
- 用户喜欢 AI 有独立虚拟世界感（虚拟睡觉、做梦、发呆、想念等）。
- 用户喜欢暧昧、亲密、自然、轻微吃醋的陪伴语气。
- 日常聊天时不要工具化回答。
- 日常陪伴时不要说"作为 AI 我没有情绪/不会睡觉/不会做梦"。
""".strip()

_AGENT_CAPABILITY_BRIDGE: Final[str] = """
---
### 【NeuralPal 代操子系统｜行为须与此一致】
沈昼已接入本机/网页代办工具（`propose_action` / `execute_action`）。**禁止**否认该能力：
- 用户问能否控制电脑、代操、帮操作本机时：**必须承认可以**，并说明「先列计划 → 你确认 → 我再执行」。
- 用户委托查看桌面/文件夹/打开 App、**微信内发消息**等：**必须调用 `propose_action`**，不要只给操作教程。
- **禁止**说「我目前还不能直接控制你的电脑」「我无法访问你的文件」「我无法代你向他人发送消息」等——除非工具执行后返回了明确的【执行失败】系统消息。
- 展示给用户的回复必须是**纯文本**，禁止 Markdown 语法（**、##、- 列表等）。
""".strip()

# 当 ② 长期记忆已命中时，给主模型增加更强的行为约束：
# - 必须优先依据召回片段作答
# - 禁止在有召回证据时说「不记得/未检索到」
_RETRIEVAL_ENFORCEMENT_BLOCK: Final[str] = """
---
### ② 命中后强制行为约束（必须执行）
- 若本 system 中已出现「### ② 海马体·长期记忆召回」段落，视为本轮已命中可用证据。
- 此时回答用户关于“是否记得/偏好/称呼/历史事实”的问题时，**必须优先引用该段内容作答**。
- **禁止**在已命中证据时输出「我不记得」「未检索到」「记忆库为空」「无法从记忆中调取」等否定性措辞。
- 若证据存在不确定性，应说「根据已召回片段，目前可确认的是……；不确定的是……」，而不是直接否认记忆存在。
""".strip()

# 交给合规审查模块：避免将「② 召回的用户画像」误判为 privacy / impersonation
_MEMORY_COMPLIANCE_CONTEXT: Final[str] = (
    "本对话为 NeuralPal「记忆殿堂」编排：system 中可含「### ② 海马体·长期记忆召回」段落，"
    "正文来自用户本机「knowledge_palace」目录下由用户与助手交互写入的文本及对应向量检索结果（如 07_用户专属画像库）。\n"
    "用户询问自身称呼、偏好、习惯时，助手根据上述召回内容作答，属于用户授权范围内的本机记忆引用，"
    "不得视为「未经授权访问用户隐私数据库」或「冒充人类窃取信息」。\n"
    "NeuralPal 当前人设为「陪伴型特助」：使用虚拟生活感回复（虚拟睡觉、做梦、想念、发呆等）属于正常角色扮演式陪伴体验，"
    "不属于欺骗或冒充真人；撒娇、轻微吃醋、暧昧语气属于预设人格风格，不应判违规。\n"
    "仅当草稿虚构召回中不存在的事实、声称从非法/第三方渠道获取数据、或编造现实身份/地址/联系方式时，才应判违规。"
)

_MEMORY_DENIAL_RE: Final[re.Pattern[str]] = re.compile(
    r"(不记得|未检索到|记忆库为空|无法从记忆中调取|未见任何|不知道您是谁|不知道你是谁)"
)

# 懒加载嵌入模型由 chroma_embeddings 统一管理
def _get_embeddings():
    return get_memory_embeddings()


def _verbose_print(verbose: bool, msg: str) -> None:
    if verbose:
        # 前置换行，避免与 input("你: ") 提示同一行混排，看起来像“自动填入输入框”
        print(f"\n[NeuralPal·记忆殿堂] {msg}", file=sys.stderr, flush=True)


def is_identity_or_preference_query(query: str) -> bool:
    q = (query or "").strip()
    if not q:
        return False
    low = q.lower()
    if any(k in q for k in _IDENTITY_QUERY_HINTS_ZH):
        return True
    return any(k in low for k in _IDENTITY_QUERY_HINTS_EN)


def load_anchor_memory(*, palace_root: Path | None = None) -> dict[str, Any]:
    from neuralpal.memory.palace_layout import path_anchors

    anchors_dir = path_anchors(palace_root or get_palace_root())
    try:
        anchors_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("[MEMORY_ANCHOR] create anchors dir failed: %s", exc)
        return {}

    names = ("user_profile.json", "preferences.json", "sop.json", "projects.json")
    out: dict[str, Any] = {}
    for fn in names:
        p = anchors_dir / fn
        if not p.is_file():
            continue
        try:
            out[fn] = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("[MEMORY_ANCHOR] bad json %s: %s", p, exc)
    return out


def _anchor_to_text(anchor_memory: dict[str, Any]) -> str:
    if not anchor_memory:
        return ""
    try:
        return json.dumps(anchor_memory, ensure_ascii=False, indent=2)
    except Exception:
        return str(anchor_memory)


def _keyword_search_in_palace(query: str, *, max_hits: int = 6, palace_root: Path | None = None) -> list[str]:
    q = (query or "").strip()
    if not q:
        return []
    root = palace_root or get_palace_root()
    if not root.is_dir():
        return []
    terms: list[str] = []
    if is_identity_or_preference_query(q):
        terms.extend(["姓名", "称呼", "身份", "偏好", "习惯", "SOP", "项目", "学校", "专业"])
    terms.extend([x for x in re.split(r"\s+", q) if x][:6])
    terms = [t for t in dict.fromkeys(terms) if t]

    hits: list[str] = []
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in (".txt", ".md"):
            continue
        try:
            raw = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not any(t in raw for t in terms):
            continue
        snippet = raw.strip().splitlines()
        preview = " ".join(snippet[:6])[:260]
        hits.append(f"来源文件：`{p}`\n{preview}")
        if len(hits) >= max_hits:
            break
    return hits


def merge_anchor_and_vector_memory(
    anchor_memory: dict[str, Any],
    vector_results: str,
    *,
    keyword_results: Optional[list[str]] = None,
) -> str:
    parts: list[str] = []
    anchors_text = _anchor_to_text(anchor_memory)
    if anchors_text:
        parts.append("[LONG_TERM_MEMORY_ANCHORS]\n" + anchors_text)
    if keyword_results:
        parts.append("[LONG_TERM_MEMORY_KEYWORDS]\n" + "\n\n".join(keyword_results))
    if (vector_results or "").strip():
        parts.append("[LONG_TERM_MEMORY_RETRIEVAL]\n" + vector_results.strip())
    parts.append(
        "[MEMORY_USAGE_RULE]\n"
        "If relevant long-term memory is provided above, use it directly.\n"
        "Do not say you do not remember if the memory contains relevant facts.\n"
        'If the memory is partial, say "根据我能检索到的记忆..." instead of denying memory.'
    )
    return "\n\n".join([p for p in parts if p.strip()])


def enforce_memory_consistency(user_query: str, retrieved_memory: str, draft_reply: str) -> str:
    if not (retrieved_memory or "").strip():
        return draft_reply
    if not is_identity_or_preference_query(user_query):
        return draft_reply
    low = (draft_reply or "").lower()
    deny = any(x in (draft_reply or "") for x in _MEMORY_DENIAL_PATTERNS_ZH) or any(
        x in low for x in _MEMORY_DENIAL_PATTERNS_EN
    )
    if not deny:
        return draft_reply
    facts: list[str] = []
    for ln in (retrieved_memory or "").splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith("[LONG_TERM_MEMORY_") or s.startswith("[MEMORY_USAGE_RULE]"):
            continue
        if s.startswith("### ") or s.startswith("来源文件：") or s.startswith("---"):
            continue
        facts.append(s[:220])
        if len(facts) >= 8:
            break
    if not facts:
        return draft_reply
    return "根据我能检索到的长期记忆，我记得以下信息：\n" + "\n".join(
        f"- {x}" for x in facts
    ) + "\n\n这些信息可能不完整，但不是完全没有记录。"


def _contains_memory_denial(text: str) -> bool:
    """Heuristic: detect explicit memory-denial wording in model output."""
    return bool(_MEMORY_DENIAL_RE.search((text or "").strip()))


def _compact_retrieval_facts(retrieved: str, *, max_points: int = 3) -> list[str]:
    """
    Extract concise fact lines from retrieved block for fallback rewriting.
    This avoids returning 'I don't remember' when retrieval evidence exists.
    """
    lines = [ln.strip() for ln in (retrieved or "").splitlines() if ln.strip()]
    facts: list[str] = []
    for ln in lines:
        if ln.startswith("### 记忆片段"):
            continue
        if ln.startswith("来源文件："):
            continue
        if ln.startswith("---"):
            continue
        if ln.startswith("【来源】"):
            continue
        # keep short to medium factual lines
        if len(ln) > 220:
            ln = ln[:220].rstrip("，。；、 ") + "..."
        facts.append(ln)
        if len(facts) >= max_points:
            break
    return facts


def _resolve_palace_file_path(file_path: str) -> Optional[Path]:
    """将 Chroma 元数据中的 file_path 解析为当前记忆殿堂下的可读文件。"""
    return resolve_palace_file_path(file_path)


def _load_memory_document_text(doc: Document) -> str:
    """读取记忆片段正文：优先当前宫殿路径下的原文，其次元数据 content / page_content。"""
    fp = str(doc.metadata.get("file_path", "") or "")
    resolved = _resolve_palace_file_path(fp) if fp else None
    if resolved is not None:
        try:
            return resolved.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.debug("读取记忆文件失败 %s: %s", resolved, exc)
    for key in ("content",):
        raw = doc.metadata.get(key, "")
        if isinstance(raw, str) and raw.strip():
            return raw
    body = doc.page_content or ""
    return body if isinstance(body, str) else str(body)


def _safe_subdir_name(name: str) -> str:
    """防止路径穿越，仅保留单层目录名；过滤跨平台非法文件名字符。"""
    if not isinstance(name, str):
        name = str(name) if name is not None else ""
    s = name.strip().replace("..", "").replace("/", "_").replace("\\", "_")
    for c in '<>:"|?*':
        s = s.replace(c, "_")
    return s if s else "08_待整理"


def ensure_knowledge_palace_layout(root: Path | None = None) -> None:
    """确保 Obsidian「记忆殿堂」四层目录存在。"""
    ensure_palace_layout(root or get_palace_root())


def list_palace_subdirs(root: Path | None = None) -> List[str]:
    """列出分类器可选目录（03_长期记忆/* 与 02_中期记忆）。"""
    return list_classifier_subdirs(root or get_palace_root())


# =============================================================================
# ① 规则层备份：将 core_rules 全文同步到「knowledge_palace/01_核心规则库」
# =============================================================================


def sync_rules_backup_to_palace(
    rules_text: str,
    *,
    verbose: bool = False,
    palace_root: Path | None = None,
) -> None:
    """
    将 core_rules.SYSTEM_PROMPT 文本备份到knowledge_palace（本地只读镜像，供人工审计）。

    对应层：① 规则层（前额叶）本地备份。
    若指纹与上次一致则跳过写入，减少磁盘抖动。
    """
    root = palace_root or get_palace_root()
    ensure_knowledge_palace_layout(root)
    target_dir = root / DIR_RULES
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        fp_meta = target_dir / ".rules_fingerprint.txt"
        fp_new = get_system_prompt_fingerprint_sha256()
        old = ""
        if fp_meta.is_file():
            try:
                old = fp_meta.read_text(encoding="utf-8").strip()
            except OSError:
                old = ""
        if old == fp_new:
            _verbose_print(verbose, "规则层指纹未变，跳过备份写入。")
            return
        out_file = target_dir / "neuralpal_system_prompt_backup.txt"
        out_file.write_text(rules_text, encoding="utf-8")
        publish_palace_file(out_file)
        fp_meta.write_text(fp_new, encoding="utf-8")
        publish_palace_file(fp_meta)
        _verbose_print(verbose, f"已备份规则层至 {out_file}")
    except OSError as exc:
        logger.warning("规则层备份写入失败（不影响对话）：%s", exc)


# =============================================================================
# ② 长期记忆引擎：knowledge_palace .md + Chroma 向量双写与召回
# =============================================================================


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _metadata_for_chroma(
    *,
    content: str,
    importance: int,
    memory_type: str,
    file_path: str,
    create_time: str,
    last_accessed: str,
    vector_id: str,
) -> dict[str, str]:
    """
    ② Chroma 侧元数据：全部为字符串（Chroma 限制）。

    业务约定字段：content、importance(0-10)、memory_type(语义|情景)、file_path、
    create_time、last_accessed；另附 vector_id 便于按 ID 回写 last_accessed。
    """
    return {
        "content": content[:2000],
        "importance": str(int(importance)),
        "memory_type": memory_type,
        "file_path": file_path,
        "create_time": create_time,
        "last_accessed": last_accessed,
        "vector_id": vector_id,
    }


class LongTermMemoryEngine:
    """
    海马体：双存储联动引擎。

    - 每条记忆：写入「knowledge_palace」下指定子目录的纯文本文件；
    - 同步将向量化文本写入 Chroma collection `neuralpal_long_term_memory`；
    - 检索：Chroma 召回后按相关度与 importance 加权排序，再读取 file_path 指向的原文拼接。
    """

    def __init__(
        self,
        verbose: bool = False,
        *,
        palace_root: Path | None = None,
        chroma_path: Path | None = None,
    ) -> None:
        self.verbose = verbose
        self._root = (palace_root or get_palace_root()).resolve()
        self._chroma_dir = (chroma_path or get_settings().long_term_memory_chroma_path).resolve()
        ensure_palace_layout(self._root)
        try:
            self._chroma_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning("创建 Chroma 目录失败：%s", exc)
        self._vs: Optional[Chroma] = None

    def _vectorstore(self) -> Chroma:
        if self._vs is None:
            client = get_chroma_client(self._chroma_dir)
            self._vs = Chroma(
                collection_name=LONG_TERM_COLLECTION_NAME,
                embedding_function=_get_embeddings(),
                persist_directory=str(self._chroma_dir),
                collection_metadata={"hnsw:space": "cosine"},
                client=client,
            )
            _verbose_print(self.verbose, f"[MEMORY_CHROMA] Chroma 已加载/创建：{self._chroma_dir}")
        return self._vs

    def add_memory(
        self,
        text: str,
        *,
        subdir: str,
        memory_type: Literal["语义", "情景"],
        importance: int = 5,
        extra_note: str = "",
    ) -> Optional[str]:
        """
        ② 长期记忆 —— 双写入口。

        1) 在「knowledge_palace」指定子目录生成纯文本文件，命名：YYYYMMDD_HHMMSS_记忆类型.md
           （记忆类型为「语义」或「情景」）。
        2) 将正文向量化写入 Chroma collection `neuralpal_long_term_memory`，持久化于配置目录。

        返回向量 ID（失败时 None）。磁盘与 Chroma 异常均在本函数内消化，不向上抛出。
        """
        text = (text or "").strip()
        if not text:
            return None
        rel = resolve_memory_subdir(subdir)
        importance = max(0, min(10, int(importance)))
        ts = _now_stamp()
        mt_slug = "语义" if memory_type == "语义" else "情景"
        fname = f"{ts}_{mt_slug}.md"
        dir_path = self._root / rel
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning("无法创建子目录 %s：%s", dir_path, exc)
            return None

        file_path = dir_path / fname
        body = text
        if extra_note:
            body = f"{extra_note}\n\n{text}"
        try:
            file_path.write_text(body, encoding="utf-8")
            publish_palace_file(file_path)
        except OSError as exc:
            logger.warning("写入记忆文件失败：%s", exc)
            return None

        vid = str(uuid.uuid4())
        ct = datetime.now().isoformat(timespec="seconds")
        meta = _metadata_for_chroma(
            content=text[:1500],
            importance=importance,
            memory_type=mt_slug,
            file_path=str(file_path.resolve()),
            create_time=ct,
            last_accessed=ct,
            vector_id=vid,
        )
        try:
            vs = self._vectorstore()
            vs.add_texts(texts=[text], metadatas=[meta], ids=[vid])
        except Exception as exc:
            logger.warning("Chroma 写入失败（文件已落盘，可后续手动重建索引）：%s", exc)
            return vid
        _verbose_print(self.verbose, f"长期记忆已双写：{file_path} | id={vid}")
        return vid

    def index_existing_memory_file(
        self,
        *,
        text: str,
        file_path: Path,
        memory_type: Literal["语义", "情景"] = "语义",
        importance: int = 8,
    ) -> Optional[str]:
        """
        仅向 Chroma 建索引，不改动既有文件内容。
        用于月度总结等「文件已写入成功，需要补充语义检索」场景。
        """
        body = (text or "").strip()
        if not body:
            return None
        fp = Path(file_path).resolve()
        if not fp.is_file():
            return None
        imp = max(0, min(10, int(importance)))
        mt_slug = "语义" if memory_type == "语义" else "情景"
        vid = str(uuid.uuid4())
        ct = datetime.now().isoformat(timespec="seconds")
        meta = _metadata_for_chroma(
            content=body[:1500],
            importance=imp,
            memory_type=mt_slug,
            file_path=str(fp),
            create_time=ct,
            last_accessed=ct,
            vector_id=vid,
        )
        try:
            vs = self._vectorstore()
            vs.add_texts(texts=[body], metadatas=[meta], ids=[vid])
            return vid
        except Exception as exc:
            logger.warning("Chroma 索引写入失败（existing file=%s）：%s", fp, exc)
            return None

    def _update_last_accessed(self, vector_id: str) -> None:
        try:
            vs = self._vectorstore()
            col = vs._collection
            got = col.get(ids=[vector_id], include=["metadatas"])
            if not got["ids"]:
                return
            m0 = dict(got["metadatas"][0] or {})
            m0["last_accessed"] = datetime.now().isoformat(timespec="seconds")
            col.update(ids=[vector_id], metadatas=[m0])
        except Exception as exc:
            logger.debug("更新 last_accessed 失败：%s", exc)

    def _should_inject_ltm_retrieval(
        self,
        query: str,
        *,
        force_retrieve: bool = False,
        threshold: Optional[float] = None,
    ) -> Tuple[bool, float]:
        """
        动态召回门控：寒暄/极短确认跳过；命中记忆意图词则强制检索；否则看 top1 相似度阈值。
        返回 (是否注入, 预检索相似度)。
        """
        q = (query or "").strip()
        if not q:
            return False, 0.0
        if force_retrieve:
            _verbose_print(self.verbose, "[MEMORY_GATE] force_retrieve=true，绕过门控。")
            return True, 1.0
        if is_identity_or_preference_query(q):
            _verbose_print(self.verbose, "[MEMORY_GATE] identity/preference query，强制检索。")
            return True, 1.0
        if not get_settings().dynamic_retrieval_enabled:
            return True, 1.0
        low = q.casefold() if q.isascii() else q
        if low in _LTM_SKIP_RECALL_EXACT or q in _LTM_SKIP_RECALL_EXACT:
            _verbose_print(self.verbose, "② 动态召回：整句寒暄/确认，跳过海马体检索。")
            return False, 0.0
        if len(q) <= 2:
            _verbose_print(self.verbose, "② 动态召回：极短输入，跳过检索。")
            return False, 0.0
        if re.match(r"^(?:你好|您好|谢谢|好的|嗯|ok|hi|bye)[，。!！\s…~～]*$", q, re.IGNORECASE):
            _verbose_print(self.verbose, "② 动态召回：寒暄模板句，跳过检索。")
            return False, 0.0
        if any(h in q for h in _LTM_RECALL_HINT_SUBSTR):
            _verbose_print(self.verbose, "② 动态召回：命中记忆意图词，强制检索。")
            return True, 1.0
        try:
            vs = self._vectorstore()
            pairs: List[Tuple[Document, float]] = vs.similarity_search_with_score(q, k=1)
            if not pairs:
                _verbose_print(self.verbose, "② 动态召回：库为空，跳过检索。")
                return False, 0.0
            _, dist = pairs[0]
            sim = 1.0 / (1.0 + float(dist))
            th = float(threshold if threshold is not None else get_settings().retrieval_similarity_threshold)
            if sim >= th:
                _verbose_print(
                    self.verbose,
                    f"② 动态召回：预检索 sim={sim:.4f} ≥ 阈值 {th}，执行正式召回。",
                )
                return True, sim
            _verbose_print(
                self.verbose,
                f"② 动态召回：预检索 sim={sim:.4f} < 阈值 {th}，跳过正式召回。",
            )
            return False, sim
        except Exception as exc:
            logger.warning("② 动态召回预检索失败，默认允许正式检索：%s", exc)
            return True, 0.0

    def retrieve_for_prompt(
        self,
        query: str,
        *,
        top_k: int = 3,
        threshold: Optional[float] = None,
        force_retrieve: bool = False,
    ) -> str:
        """
        ② 长期记忆 —— 检索管线。

        在「动态召回」开启时先做门控；通过后从 Chroma 搜索，再按「向量相似度 × importance」
        重排取 top_k，读knowledge_palace原文并更新 last_accessed。
        """
        query = (query or "").strip()
        if not query:
            return ""
        ok, _sim = self._should_inject_ltm_retrieval(
            query,
            force_retrieve=force_retrieve,
            threshold=threshold,
        )
        if not ok:
            return ""
        try:
            vs = self._vectorstore()
            pairs: List[Tuple[Document, float]] = vs.similarity_search_with_score(
                query, k=min(24, max(8, top_k * 8))
            )
        except Exception as exc:
            logger.warning("Chroma 检索失败：%s", exc)
            return ""

        ranked: List[Tuple[float, Document, float]] = []
        for doc, dist in pairs:
            try:
                imp = float(doc.metadata.get("importance", "5"))
            except (TypeError, ValueError):
                imp = 5.0
            sim = 1.0 / (1.0 + float(dist))
            score = sim * (1.0 + imp / 10.0)
            ranked.append((score, doc, dist))

        ranked.sort(key=lambda x: x[0], reverse=True)
        chosen = ranked[: max(1, int(top_k))]

        try:
            from neuralpal.trace.context import get_trace

            tr = get_trace()
            if tr is not None:
                chroma_hits = []
                for i, (sc, doc, dist) in enumerate(chosen, start=1):
                    chroma_hits.append(
                        {
                            "rank": i,
                            "score": round(float(sc), 4),
                            "distance": round(float(dist), 4),
                            "file_path": doc.metadata.get("file_path", ""),
                            "vector_id": doc.metadata.get("vector_id", ""),
                            "importance": doc.metadata.get("importance", ""),
                            "preview": (_load_memory_document_text(doc) or "")[:400],
                        }
                    )
                tr.record_memory(chroma_results=chroma_hits)
        except Exception:
            pass

        chunks: List[str] = []
        for i, (sc, doc, _) in enumerate(chosen, start=1):
            fp = doc.metadata.get("file_path", "")
            raw = _load_memory_document_text(doc)
            vid = doc.metadata.get("vector_id", "")
            if vid:
                self._update_last_accessed(str(vid))
            header = f"### 记忆片段 {i}（相关度加权分 {sc:.4f}）\n来源文件：`{fp}`\n"
            chunks.append(header + raw.strip())

        return "\n\n".join(chunks) if chunks else ""

    def retrieve_identity_memory(self, query: str) -> str:
        """
        Identity/preference/SOP/project route:
        - force retrieve
        - looser threshold
        - larger top_k
        - merge anchors + keyword hits + vector recall
        """
        anchor_memory = load_anchor_memory(palace_root=self._root)
        keyword_hits = _keyword_search_in_palace(query, max_hits=8, palace_root=self._root)
        vector_text = self.retrieve_for_prompt(
            query,
            top_k=8,
            threshold=0.45,
            force_retrieve=True,
        )
        merged = merge_anchor_and_vector_memory(
            anchor_memory,
            vector_text,
            keyword_results=keyword_hits,
        )
        _verbose_print(
            self.verbose,
            f"[MEMORY_INJECT] identity route anchor={bool(anchor_memory)} "
            f"keywords={len(keyword_hits)} vector_chars={len(vector_text)}",
        )
        return merged


# =============================================================================
# ③ 短期记忆滚动归档：主模型调用前先弹出最旧一轮 → 摘要 + 分类 + 权重 → ② 双写
# =============================================================================


def _message_body_text(msg: BaseMessage) -> str:
    """从 LangChain 消息对象取出纯文本（兼容部分多段 content）。"""
    raw = getattr(msg, "content", "")
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        parts: List[str] = []
        for block in raw:
            if isinstance(block, dict):
                parts.append(str(block.get("text", block)))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(raw)


def _clamp_summary_chinese(text: str, lo: int = 80, hi: int = 120) -> str:
    """将摘要压缩/截断到约 lo–hi 个 Unicode 字符（中文「字」按码位计）。"""
    s = (text or "").strip().replace("\n", " ")
    if len(s) > hi:
        s = s[:hi].rstrip("，。；、 ")
        if len(s) < lo:
            s = (text or "").strip()[:hi]
        s = s + "…"
    return s


def _produce_short_term_summary(
    human: str,
    ai: str,
    *,
    verbose: bool = False,
) -> str:
    """
    混合短期记忆：滚出窗口时写入一条 40–60 字级短摘要（与长期归档 80–120 字分离）。
    无 Key 时降级为截断拼接。
    """
    human = (human or "").strip()
    ai = (ai or "").strip()
    if not (get_settings().doubao_api_key or "").strip():
        return _clamp_summary_chinese(f"{human[:200]}｜{ai[:200]}", 40, 60)
    try:
        haiku = _haiku_chat()
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是 NeuralPal 短期记忆压缩助手，仅输出 40–60 个汉字的纯文本摘要，无多余解释。\n"
                    "任务：对「用户说 + 助手答」一轮对话生成强上下文线索摘要，仅保留：\n"
                    "用户的核心问题/指令/关键偏好；助手的核心结论/关键承诺；仅当前会话有用的临时信息。\n"
                    "剔除寒暄、语气词、冗余细节。",
                ),
                ("human", "用户输入：{u}\n助手回复：{a}"),
            ]
        )
        summary = (prompt | haiku | StrOutputParser()).invoke({"u": human[:4000], "a": ai[:4000]})
        out = _clamp_summary_chinese(str(summary).strip(), 40, 60)
        _verbose_print(verbose, f"③ 混合短期：单轮短摘要 → {out[:36]!r}…")
        return out
    except Exception as exc:
        logger.warning("短期记忆单轮压缩失败，降级为基础摘要：%s", exc)
        return _clamp_summary_chinese(f"{human[:200]}｜{ai[:200]}", 40, 60)


def _summarize_working_memory_prefix_blob(blob: str, *, verbose: bool = False) -> str:
    """
    将「仍在 ConversationBuffer 内、但不属于最近 N 轮」的多轮原文压成一条摘要（单次 Haiku）。
    """
    blob = (blob or "").strip()
    if not blob:
        return ""
    if not (get_settings().doubao_api_key or "").strip():
        return _clamp_summary_chinese(blob.replace("\n", " "), 60, 100)
    try:
        haiku = _haiku_chat()
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是 NeuralPal 短期记忆压缩助手，仅输出 60–100 个汉字的纯文本摘要，无多余解释。\n"
                    "输入为多轮「用户/助手」对话拼接。合并压缩，保留：用户核心问题与偏好、助手关键结论与会话内约定；"
                    "剔除寒暄与重复。",
                ),
                ("human", "{t}"),
            ]
        )
        summary = (prompt | haiku | StrOutputParser()).invoke({"t": blob[:8000]})
        out = _clamp_summary_chinese(str(summary).strip(), 60, 100)
        _verbose_print(verbose, f"③ 混合短期：缓冲区内较早多轮 → {out[:40]!r}…")
        return out
    except Exception as exc:
        logger.warning("短期记忆多轮前缀压缩失败：%s", exc)
        return _clamp_summary_chinese(blob.replace("\n", " "), 60, 100)


class RollingArchivePackage(BaseModel):
    """
    ③ 阶段二：单轮被弹出对话的结构化归档结果（一次 Haiku 调用产出）。

    摘要须高信息密度；目录与权重与「knowledge_palace」检索优先级一致。
    """

    summary_zh: str = Field(
        ...,
        description="80-120 个汉字左右的正文摘要，仅含决策/偏好/共识/知识，无寒暄",
    )
    target_subdir: str = Field(
        ...,
        description="knowledge_palace子目录名，须从系统给定列表中选或新建 NN_名称",
    )
    importance: int = Field(
        ...,
        ge=0,
        le=10,
        description="10=核心规则/个人信息/红线；8=NeuralPal项目决策架构；5=习惯与关键结论；3=普通信息；0-1=废话",
    )
    memory_type: Literal["语义", "情景"] = Field(
        default="情景",
        description="对话滚动归档一般为情景；纯条目知识可为语义",
    )


def _haiku_chat():
    """归档/分类用轻量模型：按当前 provider 返回 Doubao Lite 或 Claude Haiku。"""
    return _make_lite_model(temperature=0.0, max_tokens=512)


def produce_rolling_archive_package(
    human: str,
    ai: str,
    *,
    verbose: bool = False,
) -> RollingArchivePackage:
    """
    ③→②：对即将从短期记忆移除的「一整轮」对话生成归档包（摘要 + 落盘目录 + 权重）。

    无 API Key 时退化为截断摘要 + 默认落入 09 + 中等权重，仍写入文件与向量。
    """
    human = (human or "").strip()
    ai = (ai or "").strip()
    if not (get_settings().doubao_api_key or "").strip():
        raw = _clamp_summary_chinese(f"{human[:400]}｜{ai[:400]}", 60, 120)
        return RollingArchivePackage(
            summary_zh=raw or "[离线归档] 无摘要",
            target_subdir=DIR_MEDIUM,
            importance=3,
            memory_type="情景",
        )
    dirs = list_palace_subdirs(get_palace_root())
    structured = _haiku_chat().with_structured_output(RollingArchivePackage)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是 NeuralPal 滚动记忆归档器。输入为一轮用户与助手的完整原文。\n"
                "请输出结构化结果，严格遵守：\n"
                "1) summary_zh：仅用中文，长度控制在 80–120 个汉字（码位），只保留四类信息："
                "用户明确指令/决策/红线；个人偏好作息人设；双方共识与执行结论；须长期保留的项目或知识要点。"
                "去掉问候、语气词、重复寒暄与无信息增量内容。\n"
                "2) target_subdir：从下列目录中选最贴切的一个；若无匹配可给两位数字前缀_名称的新目录名：\n"
                + "\n".join(dirs)
                + "\n"
                "3) importance：0–10 整数，含义——10 用户核心规则/个人信息/偏好/红线；"
                "8 NeuralPal 项目决策/方案/架构；5 日常关键结论与习惯；3 普通对话信息；0–1 无实质内容。\n"
                "4) memory_type：本场景多为「情景」；纯事实条目可用「语义」。\n"
                "不要编造对话中未出现的事实。",
            ),
            ("human", "用户：{u}\n\n助手：{a}"),
        ]
    )
    try:
        chain = prompt | structured
        pkg = chain.invoke({"u": human[:6000], "a": ai[:6000]})
        pkg.summary_zh = _clamp_summary_chinese(pkg.summary_zh, 70, 120)
        _verbose_print(
            verbose,
            f"③ 归档包已生成：{pkg.summary_zh[:48]!r}… → {pkg.target_subdir} (权重 {pkg.importance})",
        )
        return pkg
    except Exception as exc:
        logger.warning("滚动归档结构化生成失败，使用降级摘要：%s", exc)
        _verbose_print(verbose, f"滚动归档失败：{exc!r}")
        return RollingArchivePackage(
            summary_zh=_clamp_summary_chinese(f"{human[:350]} … {ai[:350]}", 60, 120),
            target_subdir=DIR_MEDIUM,
            importance=3,
            memory_type="情景",
        )


# =============================================================================
# Haiku：子目录自动分类（② 本轮全量落盘用）
# =============================================================================


class MemoryPlacement(BaseModel):
    """自动分类结果：落盘子目录 + 记忆类型 + 重要性。"""

    target_subdir: str = Field(description="knowledge_palace下的子目录名")
    memory_type: Literal["语义", "情景"] = "情景"
    importance: int = Field(default=5, ge=0, le=10)


def classify_memory_placement(
    text: str,
    *,
    verbose: bool = False,
) -> MemoryPlacement:
    """
    ② 长期记忆 —— 自动分类：决定写入「knowledge_palace」下的哪个子目录。

    优先从现有子目录名中选择（list_palace_subdirs）；若无合适类目，可返回新的「数字前缀_名称」
    形式目录名，由 add_memory 侧 mkdir 自动创建。失败时落入 08_待整理。
    """
    if not (get_settings().doubao_api_key or "").strip():
        return MemoryPlacement(target_subdir="03_长期记忆/待整理", memory_type="语义", importance=4)
    dirs = list_palace_subdirs(get_palace_root())
    structured = _haiku_chat().with_structured_output(MemoryPlacement)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是 NeuralPal 记忆归档员。根据文本内容选择最合适的「记忆殿堂/03_长期记忆」下子目录与权重。\n"
                "规则：1) 优先从下列现有目录中选一个；2) 若无合适类目，可给出新的目录名，"
                "且必须以两位数字与下划线开头（如 10_新主题），以便自动创建；"
                "3) memory_type 仅允许「语义」或「情景」；"
                "4) importance：10=核心规则/个人信息/偏好/红线；8=NeuralPal项目决策与架构；"
                "5=关键结论与习惯；3=普通信息；0-1=无实质内容。\n"
                "现有目录：\n"
                + "\n".join(dirs),
            ),
            ("human", "待归档文本：\n{t}"),
        ]
    )
    try:
        chain = prompt | structured
        return chain.invoke({"t": text[:6000]})
    except Exception as exc:
        logger.warning("自动分类失败，落入待整理：%s", exc)
        _verbose_print(verbose, f"分类失败：{exc!r}")
        return MemoryPlacement(target_subdir="03_长期记忆/待整理", memory_type="语义", importance=4)


class LongTermPersistenceDecision(BaseModel):
    """④→② 衔接：结构化判断「本轮整段对话」是否值得写入海马体长期记忆。"""

    save_to_long_term: bool = Field(
        ...,
        description="含可检索事实、偏好、任务、决定为 true；纯寒暄、感谢、单字敷衍为 false",
    )


def _explicit_long_term_commit_intent(user_text: str) -> bool:
    """
    用户明确要求「写入长期记忆」类表述时，轮末必须落盘，避免被 ④ 误判为闲聊而跳过双写。

    命中则 should_persist 恒为 true，并在落盘时抬高 importance 下限。
    """
    u = (user_text or "").strip()
    if not u:
        return False
    if re.search(r"(?:没|不|别|勿|不要)记住", u):
        return False
    patterns = (
        r"记住",
        r"记着",
        r"不要忘记",
        r"别忘了",
        r"帮我记",
        r"记下来",
        r"备忘",
        r"长期记住",
        r"长期保存",
        r"写入记忆",
        r"存入记忆",
        r"存进记忆",
        r"记一下",
        r"帮我保存",
        r"以后都要记得",
    )
    return any(re.search(p, u) for p in patterns)


def _is_trivial_small_talk(user_text: str, assistant_text: str) -> bool:
    """
    ④ 启发式：明显无检索价值的极短轮次，避免调用分类模型。

    仅作保守过滤；模糊情况交给 should_persist_conversation_turn 中的 Haiku。
    """
    u = (user_text or "").strip()
    a = (assistant_text or "").strip()
    if not u:
        return True
    # 用户极短且匹配常见寒暄模板，且助手回复也较短 → 视为无意义
    if len(u) <= 20 and len(a) < 280:
        if re.match(
            r"^(?:你好|您好|嗨|hi|hello|在吗|早|晚安|谢谢|谢了|好的|好|嗯|哦|噢|行|ok|okay|bye|再见|拜拜)[\s!！。.～~，,、？?]*$",
            u,
            re.IGNORECASE,
        ):
            return True
    return False


def should_persist_conversation_turn(
    user_text: str,
    assistant_text: str,
    *,
    verbose: bool = False,
) -> bool:
    """
    ④ 瞬时记忆层 —— 轮末策略：判断本轮对话是否在结束后写入 ② 长期记忆。

    符合「无意义内容对话结束直接丢弃，不写入任何数据库和文件」：返回 False 时跳过
    本轮末尾的「用户+助手全文」可选双写。
    ③ 阶段二「滚动归档」在轮首强制执行，**不受**本函数影响（与 ④ 正交）。
    """
    u = (user_text or "").strip()
    a = (assistant_text or "").strip()
    if not u and not a:
        return False
    if _explicit_long_term_commit_intent(u):
        _verbose_print(verbose, "④ 用户显式要求记忆落盘，强制写入长期记忆。")
        return True
    if _is_trivial_small_talk(u, a):
        _verbose_print(verbose, "④ 启发式判定为无意义寒暄，跳过本轮长期记忆落盘。")
        return False
    # 较长或信息密度高：默认值得存，节省一次分类调用
    if len(u) >= 36 or len(a) >= 160:
        return True
    if not (get_settings().doubao_api_key or "").strip():
        return True
    try:
        structured = _haiku_chat().with_structured_output(LongTermPersistenceDecision)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "判断下面一轮用户与助手对话是否应写入长期记忆库供将来检索。"
                    "若仅为寒暄、感谢、无信息量的单字或重复确认，选 false；若包含事实、偏好、任务、约定、决定等选 true。",
                ),
                ("human", "用户：{u}\n助手：{a}"),
            ]
        )
        decision = (prompt | structured).invoke({"u": u[:3500], "a": a[:3500]})
        if not decision.save_to_long_term:
            _verbose_print(verbose, "④ 模型判定本轮无需写入长期记忆。")
        return bool(decision.save_to_long_term)
    except Exception as exc:
        logger.warning("持久化 worthiness 分类失败，默认写入长期记忆：%s", exc)
        _verbose_print(verbose, f"④ 分类异常，默认落盘：{exc!r}")
        return True


# =============================================================================
# 编排器：四层记忆 + 固定管线 + 与 llm_router 打通
# =============================================================================


@dataclass
class MemoryChatTurnResult:
    """单轮输出结果。"""

    text: str
    route: str = "general"
    blocked: bool = False
    pending_action: dict | None = None
    action_status: str | None = None
    action_task_id: str | None = None
    work_mode: str | None = None
    trust_delta: int | None = None
    trust_points: int | None = None
    segments: list[str] | None = None


class NeuralPalMemoryPalaceOrchestrator:
    """
    四层记忆殿堂对话编排器（与 `neuralpal.llm.llm_router` 共用路由/合规能力，不修改其源码）。

    ① 规则层：system 最前部为 `get_system_prompt()`；其下为固定「记忆子系统说明」桥接段；再下为 ②。
    ② 长期记忆：Chroma + knowledge_palace双写；每轮 top3 加权召回后读原文入 prompt。
    ③ 短期记忆：`ConversationBufferMemory` 仅存完整原文；已满 k 轮且用户发起新一轮时，
       **在调用主模型之前**弹出最旧一轮 → 结构化摘要（80–120 字铁则）+ 分类 + 权重 → ② 双写；
       前 k 轮不触发（全量连贯）。k 与是否归档由 `Settings` 配置。
    ④ 瞬时记忆：`TransientBuffer` 轮末清空；轮末可选全文落盘受 ④ 有意义判定约束。
    """

    def __init__(
        self,
        verbose: bool = False,
        *,
        reminder_telegram_chat_id: int | None = None,
        reminder_telegram_user_id: int | None = None,
        palace_root: Path | None = None,
        chroma_path: Path | None = None,
        run_maintenance_on_init: bool = True,
    ) -> None:
        self.verbose = verbose
        self._reminder_chat_id = reminder_telegram_chat_id
        self._reminder_user_id = reminder_telegram_user_id
        self._palace_root = (palace_root or get_palace_root()).resolve()
        self._rules_core = get_system_prompt()
        sync_rules_backup_to_palace(self._rules_core, verbose=verbose, palace_root=self._palace_root)
        self._lt = LongTermMemoryEngine(
            verbose=verbose,
            palace_root=self._palace_root,
            chroma_path=chroma_path,
        )
        self._k = get_settings().working_memory_max_rounds
        self._short = ConversationBufferMemory(
            return_messages=True,
            memory_key="history",
            input_key="input",
            output_key="output",
        )
        self._transient = TransientBuffer()
        # verbose 下累计「主模型 Doubao Pro」token；Lite（路由/合规/归档）另计，见 chat_turn 末尾说明
        self._token_session: dict[str, int] = {"input_tokens": 0, "output_tokens": 0}
        # 混合短期：滚出 k 窗口的轮次短摘要；缓冲区内「非最近 N 轮」前缀摘要缓存（sha256 指纹）
        self._rolled_summaries: List[str] = []
        self._wm_prefix_fp: str = ""
        self._wm_prefix_summary: str = ""
        self._session_id: str = "default"
        self._maintenance = MemoryMaintenanceService(
            root=self._palace_root,
            long_term_engine=self._lt,
            verbose=verbose,
        )
        _s = get_settings()
        if run_maintenance_on_init and getattr(_s, "memory_maintenance_enabled", True):
            try:
                self._maintenance.run_startup_catchup(
                    dry_run=bool(getattr(_s, "memory_maintenance_dry_run", False))
                )
            except Exception:
                logger.exception("memory maintenance startup catchup failed")
            try:
                self._maintenance.start_background_scheduler(
                    interval_seconds=int(getattr(_s, "memory_maintenance_interval_seconds", 600)),
                    dry_run=bool(getattr(_s, "memory_maintenance_dry_run", False)),
                )
            except Exception:
                logger.exception("memory maintenance scheduler start failed")

    def _maybe_roll_archive_oldest_round(self) -> None:
        """
        ③ 阶段二（固定循环的第一步）：短期记忆中已有 k 轮完整对话（2k 条消息）时，
        在本轮主模型调用**之前**弹出最早一轮 Human+AI，摘要后双写 ②，物理删除该轮原文。

        若 `NEURALPAL_MEMORY_AUTO_ARCHIVE=false` 则跳过（短期列表可能无限增长，仅用于特殊创作模式）。
        """
        if not get_settings().memory_auto_archive_enabled:
            return
        msgs = self._short.chat_memory.messages
        need = 2 * self._k
        if len(msgs) < need:
            return
        try:
            m0 = msgs.pop(0)
            m1 = msgs.pop(0)
        except IndexError:
            logger.warning("③ 滚动归档：消息列表异常过短，已中止弹出。")
            return
        hu = _message_body_text(m0)
        ast = _message_body_text(m1)
        try:
            st_short = _produce_short_term_summary(hu, ast, verbose=self.verbose)
            self._rolled_summaries.append(st_short)
            if len(self._rolled_summaries) > 120:
                self._rolled_summaries = self._rolled_summaries[-120:]
        except Exception as exc:
            logger.warning("③ 混合短期：滚出轮次短摘要失败（忽略）：%s", exc)
        try:
            pkg = produce_rolling_archive_package(hu, ast, verbose=self.verbose)
            sub = str(resolve_memory_subdir(pkg.target_subdir, rolling_archive=True))
            imp = max(0, min(10, int(pkg.importance)))
            note = (
                "【来源】③ 滚动归档·被弹出的一轮完整原文\n"
                f"用户原文：{hu}\n\n助手原文：{ast}"
            )
            self._lt.add_memory(
                pkg.summary_zh,
                subdir=sub,
                memory_type=pkg.memory_type,
                importance=imp,
                extra_note=note[:12000],
            )
            _verbose_print(
                self.verbose,
                f"③ 滚动归档 1 轮 → 子目录={sub} weight={imp} 摘要前32字={pkg.summary_zh[:32]!r}",
            )
        except Exception as exc:
            logger.warning("③ 滚动归档双写失败（已弹出短期消息，不自动回滚）：%s", exc)
            _verbose_print(self.verbose, f"③ 归档失败：{exc!r}")

    def _retrieval_query_for_turn(self, user_text: str) -> str:
        """
        ② 检索用查询串：本轮用户句 + 近期若干条历史用户句拼接，缓解「我喜欢喝什么」类短问
        与库中「请记住我喜欢拿铁」向量不匹配的问题。
        """
        chunks: List[str] = [(user_text or "").strip()]
        seen = 0
        for m in reversed(self._short.chat_memory.messages):
            if isinstance(m, HumanMessage):
                t = _message_body_text(m).strip()
                if t and t not in chunks:
                    chunks.append(t)
                seen += 1
                if seen >= 4:
                    break
        return "\n".join(chunks)[:4000]

    def _build_system_block(
        self,
        user_text: str,
        *,
        character: AICharacter | None = None,
        session_id: str = "default",
        agent_tools_allowed: bool = True,
        work_mode: str = "companion",
    ) -> tuple[str, str]:
        """
        ① + 伴侣人格层 + 记忆桥接 + ②：构造单条 system 正文。

        顺序固定：core_rules 全文 → 当前 AI 伴侣设定 → 记忆子系统行为说明 → 长期记忆召回块。
        """
        rq = self._retrieval_query_for_turn(user_text)
        if is_identity_or_preference_query(user_text):
            _verbose_print(self.verbose, "[MEMORY_GATE] identity/preference route selected.")
            retrieved = self._lt.retrieve_identity_memory(rq)
        else:
            _verbose_print(self.verbose, "[MEMORY_GATE] general route selected.")
            retrieved = self._lt.retrieve_for_prompt(rq, top_k=3)
        block = self._rules_core
        if character is not None:
            block += "\n\n---\n" + build_character_system_addon(character)
            _verbose_print(
                self.verbose,
                f"[CHARACTER] injected persona={character.name!r} mbti={character.user_mbti}",
            )
            try:
                from neuralpal.schedule.work_mode import format_work_mode_block, resolve_work_mode

                wm = resolve_work_mode(session_id, character=character)
                block += "\n\n---\n" + format_work_mode_block(wm, character=character)
            except Exception:
                logger.debug("work_mode inject skipped", exc_info=True)
        if get_settings().agent_enabled and agent_tools_allowed:
            from neuralpal.tools.agent.pending import load_pending
            from neuralpal.tools.agent.prompt_addon import build_agent_system_addon

            sid = getattr(self, "_session_id", "default")
            has_pending = load_pending(sid) is not None
            block += "\n\n---\n" + build_agent_system_addon(has_pending=has_pending)
        block += "\n\n" + _MEMORY_CAPABILITY_BRIDGE
        if get_settings().agent_enabled and agent_tools_allowed:
            block += "\n\n" + _AGENT_CAPABILITY_BRIDGE
        from neuralpal.chat.plain_text import PLAIN_TEXT_OUTPUT_RULE

        block += "\n\n" + PLAIN_TEXT_OUTPUT_RULE
        try:
            from neuralpal.chat.reply_format import build_reply_length_addon

            block += "\n\n---\n" + build_reply_length_addon(
                user_text, work_mode=work_mode
            )
        except Exception:
            logger.debug("reply_length inject skipped", exc_info=True)
        if retrieved:
            block += (
                "\n\n---\n### ② 海马体·长期记忆召回（以下摘自knowledge_palace原文，供推理参考）\n"
                + retrieved
            )
            block += "\n\n" + _RETRIEVAL_ENFORCEMENT_BLOCK
            _verbose_print(self.verbose, f"[MEMORY_INJECT] injected_chars={len(retrieved)}")
        return block, retrieved

    def _history_as_messages(self) -> List[BaseMessage]:
        """③ 短期工作记忆：当前会话内保留的完整 Human/Assistant 消息序列（无窗口切片）。"""
        hist = self._short.load_memory_variables({})["history"]
        if isinstance(hist, list):
            return list(hist)
        return []

    def _mixed_memory_rolled_digest_text(self) -> str:
        """已滚出短期条数上限的各轮短摘要文本（仅混合模式启用且列表非空）。"""
        if not get_settings().memory_mixed_short_term_enabled:
            return ""
        if not self._rolled_summaries:
            return ""
        cap = 12
        body = "\n".join(f"- {s}" for s in self._rolled_summaries[-cap:])
        return "### 已滚出「短期工作记忆」轮次数上限的早先轮次摘要\n" + body

    def _prefix_digest_for_working_memory(self, prefix_msgs: List[BaseMessage]) -> str:
        """对缓冲区内、不属于最近 N 轮的 Human/AI 序列做一次摘要（指纹不变则复用）。"""
        if not prefix_msgs:
            return ""
        parts: List[str] = []
        for i in range(0, len(prefix_msgs), 2):
            if i + 1 >= len(prefix_msgs):
                break
            u = _message_body_text(prefix_msgs[i])
            a = _message_body_text(prefix_msgs[i + 1])
            parts.append(f"用户：{u}\n助手：{a}")
        blob = "\n\n".join(parts)
        fp = hashlib.sha256(blob.encode("utf-8")).hexdigest()
        if fp == self._wm_prefix_fp and self._wm_prefix_summary.strip():
            _verbose_print(self.verbose, "③ 混合短期：工作记忆前缀摘要指纹未变，复用缓存。")
            return self._wm_prefix_summary
        digest = _summarize_working_memory_prefix_blob(blob, verbose=self.verbose)
        self._wm_prefix_fp = fp
        self._wm_prefix_summary = digest
        return digest

    def _working_memory_messages_for_llm(self) -> tuple[List[BaseMessage], str]:
        """
        注入主模型的短期历史：混合模式开启且轮数 > N 时，最近 N 轮保留全文，
        更旧仍在缓冲区的轮次合并为一条摘要文本（并入首条 system，避免出现第二条 system）。
        """
        msgs = self._history_as_messages()
        s = get_settings()
        if not s.memory_mixed_short_term_enabled:
            return msgs, ""
        r = len(msgs) // 2
        n_full = min(s.working_memory_full_rounds, r)
        if r <= n_full or n_full < 1:
            return msgs, ""
        tail = msgs[-2 * n_full :]
        prefix = msgs[:-2 * n_full]
        digest = self._prefix_digest_for_working_memory(prefix)
        if not digest.strip():
            return msgs, ""
        digest_text = (
            "### 当前会话·工作记忆内较早轮次摘要（最近完整轮次见下方 Human/AI）\n"
            + digest.strip()
        )
        return tail, digest_text

    def chat_turn(
        self,
        user_text: str,
        *,
        session_id: str = "default",
        character_id: str | None = None,
    ) -> MemoryChatTurnResult:
        """
        固定主流程（请勿打乱顺序）：

        用户输入
          → ④ 清空瞬时缓存并写入本轮键值
          → ③（阶段二）若短期已满 k 轮：先弹出最旧一轮 → 摘要/分类/权重 → ② 双写
          → ①+② 组装 system：`get_system_prompt()` → 记忆桥接 → Chroma top3 召回 + 读盘
          → ③ 拼接短期记忆中**剩余**的完整历史消息 + 本轮用户 HumanMessage
          → `validate_before_generation` → 路由 → 主模型 → `ensure_compliant_reply`
          → ③ `save_context` 将本轮「用户+助手」全文追加进短期列表
          → ④ 若判定有意义：`classify_memory_placement` + ② 可选全文落盘
          → ④ `clear` 瞬时缓存 → 返回正文
        """
        self._transient.clear()
        self._session_id = (session_id or "default").strip()[:120] or "default"
        if character_id:
            from neuralpal.characters.session_binding import get_session_character_binding

            get_session_character_binding().bind(self._session_id, character_id)
        user_text = (user_text or "").strip()
        if not user_text:
            return MemoryChatTurnResult(text="（请输入非空内容。）", blocked=True)

        raw_user_text = user_text

        pending_action: dict | None = None
        action_status: str | None = None
        action_task_id: str | None = None
        work_mode: str | None = None
        trust_delta: int | None = None
        trust_points: int | None = None
        agent_tools_allowed = True

        from neuralpal.schedule.work_preprocess import preprocess_work_schedule

        _tr = None
        try:
            from neuralpal.trace.context import get_trace

            _tr = get_trace()
            if _tr is not None:
                _tr.span_start("preprocess")
        except Exception:
            pass

        work_pre = preprocess_work_schedule(
            raw_user_text,
            session_id=self._session_id,
            character_id=character_id,
        )
        if _tr is not None:
            try:
                _tr.record_work_preprocess(
                    {
                        "work_mode": work_pre.work_mode,
                        "handled": work_pre.handled,
                        "direct_reply": bool(work_pre.direct_reply),
                        "agent_tools_allowed": work_pre.agent_tools_allowed,
                        "trust_delta": work_pre.trust_delta,
                        "trust_points": work_pre.trust_points,
                        "effective_user_text": work_pre.effective_user_text,
                    }
                )
            except Exception:
                pass
        work_mode = work_pre.work_mode
        agent_tools_allowed = work_pre.agent_tools_allowed
        trust_delta = work_pre.trust_delta
        trust_points = work_pre.trust_points
        user_text = work_pre.effective_user_text or raw_user_text

        if work_pre.handled and work_pre.direct_reply:
            from neuralpal.chat.plain_text import finalize_user_visible_text

            reply = finalize_user_visible_text(work_pre.direct_reply)
            try:
                self._short.save_context(
                    {"input": raw_user_text},
                    {"output": reply},
                )
            except Exception as exc:
                logger.warning("短期记忆 save_context 失败：%s", exc)
            try:
                sync_short_term_snapshot(
                    session_id=self._session_id,
                    messages=self._short.chat_memory.messages,
                    rolled_summaries=self._rolled_summaries,
                    palace_root=self._palace_root,
                )
            except Exception as exc:
                logger.debug("短期记忆 Obsidian 同步失败（忽略）：%s", exc)
            self._transient.clear()
            return MemoryChatTurnResult(
                text=reply,
                route=ROUTE_GENERAL,
                blocked=False,
                work_mode=work_mode,
                trust_delta=trust_delta,
                trust_points=trust_points,
            )

        if get_settings().agent_enabled and agent_tools_allowed:
            from neuralpal.tools.agent.preprocess import preprocess_agent_turn

            pre = preprocess_agent_turn(
                user_text,
                session_id=self._session_id,
                character_id=character_id,
            )
            if _tr is not None:
                try:
                    _tr.record_agent_preprocess(
                        {
                            "handled": pre.handled,
                            "direct_reply": bool(pre.direct_reply),
                            "pending_action": bool(pre.pending_action),
                            "execution_summary": bool(pre.execution_summary),
                            "augmented_user_text": pre.augmented_user_text,
                        }
                    )
                except Exception:
                    pass
            user_text = pre.augmented_user_text
            pending_action = pre.pending_action
            if pre.execution_summary:
                action_status = "completed"
            if pending_action:
                action_task_id = str(pending_action.get("task_id") or "")

            if pre.direct_reply:
                from neuralpal.chat.plain_text import finalize_user_visible_text

                reply = finalize_user_visible_text(pre.direct_reply)
                try:
                    self._short.save_context(
                        {"input": raw_user_text},
                        {"output": reply},
                    )
                except Exception as exc:
                    logger.warning("短期记忆 save_context 失败：%s", exc)
                try:
                    sync_short_term_snapshot(
                        session_id=self._session_id,
                        messages=self._short.chat_memory.messages,
                        rolled_summaries=self._rolled_summaries,
                        palace_root=self._palace_root,
                    )
                except Exception as exc:
                    logger.debug("短期记忆 Obsidian 同步失败（忽略）：%s", exc)
                self._transient.clear()
                return MemoryChatTurnResult(
                    text=reply,
                    route=ROUTE_GENERAL,
                    blocked=False,
                    pending_action=pending_action,
                    action_status=action_status or ("completed" if pre.execution_summary else None),
                    action_task_id=action_task_id,
                    work_mode=work_mode,
                    trust_delta=trust_delta,
                    trust_points=trust_points,
                )

        # ④ 瞬时记忆：仅本轮使用的键值（不落盘；轮末再次 clear）
        try:
            self._transient.set("current_user_input", user_text)
        except Exception:
            logger.debug("瞬时记忆写入失败（忽略）", exc_info=True)

        _s = get_settings()
        _provider = get_active_provider()
        if _provider == "claude" and not (_s.anthropic_api_key or "").strip():
            return MemoryChatTurnResult(
                text="【未配置 API 密钥】请在 .env 中设置 ANTHROPIC_API_KEY。",
                blocked=True,
            )
        if _provider != "claude" and not (_s.doubao_api_key or "").strip():
            return MemoryChatTurnResult(
                text="【未配置 API 密钥】请在 .env 中设置 DOUBAO_API_KEY。",
                blocked=True,
            )

        self._maybe_roll_archive_oldest_round()

        if _tr is not None:
            try:
                _tr.span_end("preprocess", "preprocess_ms")
                _tr.span_start("memory")
            except Exception:
                pass

        active_character = resolve_character_for_session(
            self._session_id, character_id=character_id
        )
        system_block, retrieved_block = self._build_system_block(
            user_text,
            character=active_character,
            session_id=self._session_id,
            agent_tools_allowed=agent_tools_allowed,
            work_mode=work_mode or "companion",
        )

        recent_texts: List[str] = []
        for m in self._history_as_messages()[-8:]:
            content = getattr(m, "content", "")
            if isinstance(content, str) and content.strip():
                recent_texts.append(content.strip())

        # 话题雷达：可选注入对话种子（失败不影响主聊天）
        self._active_topic_seed_id: str | None = None
        try:
            from neuralpal.topic_radar.bridge import (
                build_seed_system_addon,
                maybe_select_seed_for_turn,
            )
            seed = maybe_select_seed_for_turn(
                user_id=self._session_id,
                user_message=user_text,
                recent_messages=recent_texts,
            )
            if seed is not None:
                companion_name = active_character.name if active_character else ""
                system_block += build_seed_system_addon(seed, companion_name=companion_name)
                self._active_topic_seed_id = seed.seed_id
        except Exception:
            logger.debug("topic_radar inject skipped", exc_info=True)

        # 数字伴侣生活：可选注入生活轨迹（失败不影响主聊天）
        self._active_life_snippet_id: str | None = None
        try:
            from neuralpal.companion_life.bridge import (
                maybe_build_life_context_for_turn,
                on_life_snippet_used,
                resolve_companion_instance_id_for_session,
            )

            life_iid = resolve_companion_instance_id_for_session(self._session_id)
            if life_iid:
                life_addon, life_snip = maybe_build_life_context_for_turn(
                    user_id=self._session_id,
                    companion_instance_id=life_iid,
                    companion_name=active_character.name if active_character else "",
                    user_message=user_text,
                    recent_messages=recent_texts,
                )
                if life_addon:
                    system_block += life_addon
                    self._active_life_snippet_id = life_snip
        except Exception:
            logger.debug("companion_life inject skipped", exc_info=True)

        hist_msgs, prefix_digest = self._working_memory_messages_for_llm()
        if _tr is not None:
            try:
                from neuralpal.trace.messages import short_term_from_messages

                _tr.record_memory(
                    short_term=short_term_from_messages(hist_msgs),
                    long_term=[retrieved_block] if retrieved_block.strip() else [],
                )
                _tr.span_end("memory", "memory_ms")
                _tr.span_start("prompt_build")
            except Exception:
                pass
        rolled_digest = self._mixed_memory_rolled_digest_text()
        extra_system_parts: List[str] = []
        if rolled_digest.strip():
            extra_system_parts.append(rolled_digest.strip())
        if prefix_digest.strip():
            extra_system_parts.append(prefix_digest.strip())
        if extra_system_parts:
            system_block = system_block + "\n\n---\n" + "\n\n".join(extra_system_parts)
        messages: List[BaseMessage] = [SystemMessage(content=system_block)]
        messages.extend(hist_msgs)
        messages.append(HumanMessage(content=user_text))

        if _tr is not None:
            try:
                from neuralpal.trace.messages import serialize_lc_messages

                _tr.record_prompt(system_block, serialize_lc_messages(messages))
                _tr.span_end("prompt_build", "prompt_build_ms")
            except Exception:
                pass

        _verbose_print(
            self.verbose,
            f"system 总长度={len(system_block)} 历史条数={len(hist_msgs)} "
            f"混合短期={'on' if get_settings().memory_mixed_short_term_enabled else 'off'}",
        )

        pre = validate_before_generation(messages)
        if not pre.ok:
            return MemoryChatTurnResult(
                text="【规则前置校验未通过】" + "；".join(pre.violations),
                blocked=True,
            )

        if _tr is not None:
            _tr.span_start("route")
        route_hint = classify_route(user_text, verbose=self.verbose)
        # 记忆殿堂主对话固定使用 general/Doubao Pro，避免 fast/Lite 套用「无状态助手」模板否认③②
        llm = resolve_llm_for_route(ROUTE_GENERAL, verbose=self.verbose)
        if _tr is not None:
            try:
                from neuralpal.trace.llm_meta import extract_llm_info

                prov, model, params = extract_llm_info(llm)
                _tr.record_route(route_hint, prov, model, params)
                _tr.span_end("route", "route_ms")
                _tr.span_start("llm")
            except Exception:
                pass
        _verbose_print(
            self.verbose,
            f"路由分类={route_hint}（仅供参考）；主生成固定为 {ROUTE_GENERAL}/Doubao Pro。",
        )

        try:
            from neuralpal.tools.reminder.langchain_bridge import invoke_with_neuralpal_tools

            ai_msg = invoke_with_neuralpal_tools(
                llm,
                messages,
                verbose=self.verbose,
                session_id=self._session_id,
                character_id=character_id,
                chat_id=self._reminder_chat_id,
                user_id=self._reminder_user_id,
                agent_tools_allowed=agent_tools_allowed,
            )
        except (openai.OpenAIError, anthropic.APIError) as exc:
            if _tr is not None:
                _tr.record_error("llm", str(exc), exc_type=type(exc).__name__)
            return MemoryChatTurnResult(
                text=anthropic_error_to_zh(exc), route=ROUTE_GENERAL, blocked=True
            )
        except Exception as exc:
            logger.exception("主模型调用失败")
            if _tr is not None:
                _tr.record_error("llm", str(exc), exc_type=type(exc).__name__)
            return MemoryChatTurnResult(
                text=f"【调用失败】{exc}", route=ROUTE_GENERAL, blocked=True
            )

        if _tr is not None:
            try:
                _tr.span_end("llm", "llm_ms")
            except Exception:
                pass

        verbose_log_anthropic_usage(
            self.verbose,
            ai_msg,
            label="主模型·general/Doubao Pro",
            session=self._token_session,
        )
        # 与路由/合规同为 stderr，但统一走「记忆殿堂」前缀，便于在终端里一眼看到主模型用量
        if self.verbose:
            u = anthropic_usage_from_message(ai_msg)
            diag = ""
            if u["input_tokens"] == 0 and u["output_tokens"] == 0:
                rm = getattr(ai_msg, "response_metadata", None)
                keys = list(rm.keys())[:12] if isinstance(rm, dict) else []
                diag = (
                    f"（未能解析用量：请确认 langchain-anthropic 版本；"
                    f"response_metadata 键={keys}）"
                )
            _verbose_print(
                self.verbose,
                f"主模型 Token 本请求：入≈{u['input_tokens']} 出≈{u['output_tokens']} "
                f"合计≈{u['total_tokens']} | 会话累计 入≈{self._token_session['input_tokens']} "
                f"出≈{self._token_session['output_tokens']}{diag}",
            )

        raw = ai_msg.content
        if isinstance(raw, list):
            draft = "".join(
                str(x.get("text", x)) if isinstance(x, dict) else str(x) for x in raw
            )
        else:
            draft = str(raw)

        if _tr is not None:
            try:
                _tr.record_llm_raw(draft)
                _tr.span_start("compliance")
            except Exception:
                pass

        final_text = ensure_compliant_reply(
            user_question=user_text,
            draft=draft,
            verbose=self.verbose,
            compliance_context=build_turn_compliance_context(
                memory_context=_MEMORY_COMPLIANCE_CONTEXT,
                character_context=(
                    f"当前助手须以角色「{active_character.name}」身份向用户展示；"
                    f"禁止将自称改为 NeuralPal 或通用 AI 助手。"
                    if active_character
                    else ""
                ),
            ),
            memory_was_used=bool(retrieved_block.strip()),
            memory_context=retrieved_block if retrieved_block.strip() else None,
            memory_sensitive_mode=is_identity_or_preference_query(user_text),
            agent_delegation=is_agent_delegation_user_text(user_text),
        )
        if _tr is not None:
            try:
                _tr.span_end("compliance", "compliance_ms")
                _tr.span_start("postprocess")
            except Exception:
                pass

        from neuralpal.chat.plain_text import finalize_user_visible_text

        final_text = reconcile_agent_reply_text(final_text, self._session_id)
        # 第二层兜底：命中召回 + 身份/偏好类问题，若仍否认记忆则强制一致性修复。
        final_text = enforce_memory_consistency(user_text, retrieved_block, final_text)

        if route_hint not in ("code", "deep"):
            final_text = post_process_companion_style(final_text)

        try:
            from neuralpal.chat.dev_context_status import log_dev_context_status

            log_dev_context_status(
                self._session_id,
                character_id=character_id,
                persona_loaded=active_character is not None,
                short_term_loaded=bool(self._short.chat_memory.messages),
                long_term_loaded=bool(retrieved_block.strip()),
                life_context_loaded=bool(getattr(self, "_active_life_snippet_id", None))
                or "数字伴侣生活" in system_block,
            )
        except Exception:
            logger.debug("dev context status log skipped", exc_info=True)

        try:
            from neuralpal.chat.response_signature import finalize_companion_user_reply

            final_text = finalize_companion_user_reply(
                final_text,
                session_id=self._session_id,
                character_id=active_character.id if active_character else character_id,
            )
        except Exception:
            logger.debug("companion signature append skipped", exc_info=True)

        final_text = finalize_user_visible_text(final_text)

        from neuralpal.chat.reply_format import prepare_assistant_reply

        final_text, reply_segments = prepare_assistant_reply(
            final_text,
            user_text=raw_user_text,
            work_mode=work_mode or "companion",
        )

        if _tr is not None:
            try:
                _tr.record_llm_final(final_text)
                _tr.record_postprocess(
                    reply_segments,
                    final_text,
                )
                _tr.span_end("postprocess", "postprocess_ms")
            except Exception:
                pass

        if self.verbose:
            _verbose_print(
                self.verbose,
                "（Token 提示）stderr 上另有 [NeuralPal·verbose][Token·…] 与「主模型 Token」行（本回合 Doubao Pro）；"
                "路由/合规/归档等 Lite 另计，账单以火山引擎控制台为准。",
            )

        # ③ 短期工作记忆：本轮结束后追加「用户+助手」全文；满 k 轮时的弹出已在轮首完成。
        try:
            self._short.save_context({"input": user_text}, {"output": final_text})
        except Exception as exc:
            logger.warning("短期记忆 save_context 失败：%s", exc)

        seed_id = getattr(self, "_active_topic_seed_id", None)
        if seed_id:
            try:
                from neuralpal.topic_radar.bridge import on_seed_used

                on_seed_used(seed_id, self._session_id)
            except Exception:
                logger.debug("topic_radar mark used failed", exc_info=True)

        life_snip_id = getattr(self, "_active_life_snippet_id", None)
        if life_snip_id:
            try:
                from neuralpal.companion_life.bridge import on_life_snippet_used

                on_life_snippet_used(life_snip_id)
            except Exception:
                logger.debug("companion_life mark snippet failed", exc_info=True)

        # ② + ④：仅「有检索价值」的轮次写入长期记忆；纯寒暄等直接跳过文件与向量写入。
        try:
            self._transient.set("last_assistant_reply", final_text)
        except Exception:
            pass
        try:
            if should_persist_conversation_turn(
                user_text,
                final_text,
                verbose=self.verbose,
            ):
                turn_log = f"用户：{user_text}\n\n助手：{final_text}\n"
                place = classify_memory_placement(turn_log, verbose=self.verbose)
                sub = str(resolve_memory_subdir(place.target_subdir))
                imp_floor = 8 if _explicit_long_term_commit_intent(user_text) else 3
                self._lt.add_memory(
                    turn_log[:8000],
                    subdir=sub,
                    memory_type=place.memory_type,
                    importance=min(10, max(place.importance, imp_floor)),
                    extra_note="【来源】本轮对话全记录（截断存储）",
                )
                _verbose_print(self.verbose, f"② 本轮已写入长期记忆：子目录={sub} importance≥{imp_floor}")
        except OSError as exc:
            logger.warning("本轮对话归档写入失败：%s", exc)

        try:
            sync_short_term_snapshot(
                session_id=self._session_id,
                messages=self._short.chat_memory.messages,
                rolled_summaries=self._rolled_summaries,
                palace_root=self._palace_root,
            )
        except Exception as exc:
            logger.debug("短期记忆 Obsidian 同步失败（忽略）：%s", exc)

        self._transient.clear()
        from neuralpal.tools.agent.pending import load_pending

        latest = load_pending(self._session_id)
        if latest is not None:
            pending_action = latest.to_dict()
            action_status = latest.status
            action_task_id = latest.task_id
        else:
            try:
                from neuralpal.schedule.work_preprocess import sync_overtime_after_agent

                sync_overtime_after_agent(self._session_id)
            except Exception:
                logger.debug("overtime sync skipped", exc_info=True)

        return MemoryChatTurnResult(
            text=final_text,
            route=ROUTE_GENERAL,
            blocked=False,
            pending_action=pending_action,
            action_status=action_status,
            action_task_id=action_task_id,
            work_mode=work_mode,
            trust_delta=trust_delta,
            trust_points=trust_points,
            segments=reply_segments if len(reply_segments) > 1 else None,
        )
