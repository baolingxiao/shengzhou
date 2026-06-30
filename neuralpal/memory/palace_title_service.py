# -*- coding: utf-8 -*-
"""记忆宫殿展示标题：日期 + 豆包 Lite 摘要（可缓存至 frontmatter）。"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Final, Optional, Tuple

from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from neuralpal.config import get_settings
from neuralpal.memory.palace_layout import publish_palace_file

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n?", re.DOTALL)


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw_fm = m.group(1)
    body = text[m.end() :]
    meta: dict[str, str] = {}
    for line in raw_fm.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        meta[key.strip()] = val.strip().strip('"').strip("'")
    return meta, body


def _build_frontmatter(meta: dict[str, str]) -> str:
    lines = ["---"]
    for k, v in meta.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)

DISPLAY_TITLE_KEY: Final[str] = "neuralpal_display_title"
_TITLE_MAX_CHARS: Final[int] = 24
_PROBE_TTL_SEC: Final[float] = 300.0

_probe_cache: tuple[float, bool, str] | None = None
_FILENAME_DATE_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})_\d{6}_")


def doubao_configured() -> bool:
    return bool((get_settings().doubao_api_key or "").strip())


def probe_doubao_api(*, force: bool = False) -> tuple[bool, str]:
    """
    检测豆包 API 是否可调用（带 5 分钟会话缓存）。
    返回 (ok, error_message)。
    """
    global _probe_cache
    if not doubao_configured():
        return False, "未配置 DOUBAO_API_KEY"
    now = time.monotonic()
    if not force and _probe_cache is not None:
        ts, ok, msg = _probe_cache
        if now - ts < _PROBE_TTL_SEC:
            return ok, msg
    try:
        from neuralpal.llm.llm_router import _make_chat_model

        s = get_settings()
        llm = _make_chat_model(s.doubao_model_lite, temperature=0.0, max_tokens=16)
        llm.invoke([HumanMessage(content='请只回复一个字：好')])
        _probe_cache = (now, True, "")
        return True, ""
    except Exception as exc:
        msg = str(exc).strip() or type(exc).__name__
        logger.info("豆包 API 探测失败：%s", msg)
        _probe_cache = (now, False, msg)
        return False, msg


def date_label_from_path(path: Path) -> str:
    m = _FILENAME_DATE_RE.match(path.stem)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    try:
        ts = path.stat().st_mtime
        return time.strftime("%Y-%m-%d", time.localtime(ts))
    except OSError:
        return ""


def _clean_summary(text: str) -> str:
    s = (text or "").strip().replace("\n", " ").strip("\"'「」『』")
    s = re.sub(r"\s+", "", s)
    if len(s) > _TITLE_MAX_CHARS:
        s = s[:_TITLE_MAX_CHARS].rstrip("，。、；：")
    return s or "对话片段"


def fallback_summary_from_body(body: str) -> str:
    """无 AI 时从正文提取短标题。"""
    for ln in body.splitlines():
        s = ln.strip()
        if not s or s.startswith("#") or s.startswith("【来源】"):
            continue
        if s.startswith("用户："):
            s = s[3:].strip()
        elif s.startswith("助手："):
            s = s[3:].strip()
        if len(s) >= 4:
            return _clean_summary(s)
    return _clean_summary(_preview_snippet(body))


def _preview_snippet(body: str) -> str:
    lines: list[str] = []
    for ln in body.splitlines():
        t = ln.strip()
        if t and not t.startswith("#"):
            lines.append(t)
        if len("".join(lines)) > 80:
            break
    return " ".join(lines)[:80]


def format_display_title(date_label: str, summary: str) -> str:
    summary = _clean_summary(summary)
    if date_label and summary:
        return f"{date_label} · {summary}"
    return summary or date_label or "未命名记忆"


def resolve_display_title(
    *,
    path: Path,
    meta: dict[str, str],
    body: str,
) -> tuple[str, str, bool]:
    """
    返回 (display_title, summary_part, needs_ai_title)。
    needs_ai_title=True 表示 frontmatter 无缓存且可尝试豆包生成。
    """
    date_label = date_label_from_path(path)
    cached = (meta.get(DISPLAY_TITLE_KEY) or "").strip()
    if cached:
        if date_label and not cached.startswith(date_label):
            return format_display_title(date_label, cached), cached, False
        return cached if " · " in cached else format_display_title(date_label, cached), cached, False

    summary = fallback_summary_from_body(body)
    display = format_display_title(date_label, summary)
    return display, summary, doubao_configured()


def generate_title_with_doubao(body: str) -> str:
    """调用豆包 Lite 生成 8–18 字主题摘要。"""
    if not doubao_configured():
        raise RuntimeError("未配置 DOUBAO_API_KEY")
    ok, err = probe_doubao_api()
    if not ok:
        raise RuntimeError(f"豆包 API 不可用：{err}")

    from neuralpal.llm.llm_router import _make_chat_model

    s = get_settings()
    snippet = (body or "").strip()[:3500]
    llm = _make_chat_model(s.doubao_model_lite, temperature=0.2, max_tokens=64)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是记忆标题助手。根据给定记忆正文，用 8–18 个汉字概括主题。"
                "只输出标题本身：不要引号、不要日期、不要解释、不要标点结尾。",
            ),
            ("human", "{text}"),
        ]
    )
    raw = (prompt | llm | StrOutputParser()).invoke({"text": snippet})
    return _clean_summary(str(raw))


def cache_display_title(path: Path, summary: str) -> str:
    """将 AI/人工摘要写入 frontmatter 并同步 Obsidian；返回完整展示标题。"""
    fp = path.resolve()
    text = fp.read_text(encoding="utf-8")
    meta, body = _split_frontmatter(text)
    summary = _clean_summary(summary)
    meta[DISPLAY_TITLE_KEY] = summary
    fp.write_text(_build_frontmatter(meta) + body.lstrip("\n"), encoding="utf-8")
    publish_palace_file(fp)
    return format_display_title(date_label_from_path(fp), summary)


def ensure_display_title(path: Path, *, use_ai: bool = True) -> str:
    """读取或生成展示标题；use_ai=False 时仅用 fallback。"""
    fp = path.resolve()
    text = fp.read_text(encoding="utf-8")
    meta, body = _split_frontmatter(text)
    display, summary, needs_ai = resolve_display_title(path=fp, meta=meta, body=body)
    if meta.get(DISPLAY_TITLE_KEY):
        return display
    if use_ai and needs_ai and doubao_configured():
        try:
            ai_summary = generate_title_with_doubao(body)
            return cache_display_title(fp, ai_summary)
        except Exception as exc:
            logger.warning("豆包标题生成失败 %s: %s", fp.name, exc)
    if not meta.get(DISPLAY_TITLE_KEY):
        cache_display_title(fp, summary)
    return format_display_title(date_label_from_path(fp), summary)
