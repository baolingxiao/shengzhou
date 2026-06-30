# -*- coding: utf-8 -*-
"""记忆宫殿浏览：列出短期/中期/长期记忆，支持删除与标记（仓库 + Obsidian 同步）。"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Final, Iterable, List, Optional

from neuralpal.memory.palace_layout import (
    DIR_LONG,
    DIR_MEDIUM,
    DIR_SHORT,
    ensure_palace_layout,
    get_obsidian_palace_root,
    get_repo_palace_root,
    publish_palace_file,
    _rel_to_repo_palace,
)
from neuralpal.memory.constants import LONG_TERM_COLLECTION_NAME
from neuralpal.memory.palace_title_service import (
    DISPLAY_TITLE_KEY,
    date_label_from_path,
    resolve_display_title,
)

logger = logging.getLogger(__name__)

_active_palace_root: Path | None = None
_active_chroma_path: Path | None = None


def set_palace_scope(*, palace_root: Path | None, chroma_path: Path | None = None) -> None:
    """限定本次操作的记忆宫殿根目录（角色后台用）。"""
    global _active_palace_root, _active_chroma_path
    _active_palace_root = palace_root.resolve() if palace_root else None
    _active_chroma_path = chroma_path.resolve() if chroma_path else None


def _resolve_palace_root() -> Path:
    if _active_palace_root is not None:
        return _active_palace_root
    return get_repo_palace_root()


def _resolve_chroma_path():
    if _active_chroma_path is not None:
        return _active_chroma_path
    from neuralpal.config import get_settings

    return Path(get_settings().long_term_memory_chroma_path).expanduser().resolve()

_MARK_KEY: Final[str] = "neuralpal_marked"
_MARK_TIME_KEY: Final[str] = "neuralpal_marked_at"
_SKIP_NAMES: Final[frozenset[str]] = frozenset(
    {
        "neuralpal_system_prompt_backup.md",
        "neuralpal_system_prompt_backup.txt",
        ".rules_fingerprint.md",
        ".rules_fingerprint.txt",
    }
)
_LONG_SKIP_DIRS: Final[frozenset[str]] = frozenset({"_系统锚点", "anchors"})
_PREVIEW_CHARS: Final[int] = 280

_FRONTMATTER_RE = re.compile(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n?", re.DOTALL)
_YAML_BOOL_RE = re.compile(rf"^{re.escape(_MARK_KEY)}\s*:\s*(true|yes|1)\s*$", re.IGNORECASE | re.MULTILINE)


class MemoryTier(str, Enum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"

    @property
    def label(self) -> str:
        return {
            MemoryTier.SHORT: "短期记忆",
            MemoryTier.MEDIUM: "中期记忆",
            MemoryTier.LONG: "长期记忆",
        }[self]

    @property
    def dir_name(self) -> str:
        return {
            MemoryTier.SHORT: DIR_SHORT,
            MemoryTier.MEDIUM: DIR_MEDIUM,
            MemoryTier.LONG: DIR_LONG,
        }[self]


@dataclass(frozen=True)
class MemoryEntry:
    """单条可展示记忆。"""

    id: str
    tier: MemoryTier
    path: Path
    rel_path: str
    title: str
    display_title: str
    date_label: str
    preview: str
    body: str
    marked: bool
    modified_at: float
    needs_ai_title: bool = False


def _tier_root(tier: MemoryTier) -> Path:
    return _resolve_palace_root() / tier.dir_name


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


def _is_marked(meta: dict[str, str], body: str) -> bool:
    val = (meta.get(_MARK_KEY) or "").lower()
    if val in ("true", "yes", "1"):
        return True
    return bool(_YAML_BOOL_RE.search(body[:400]))


def _preview_from_body(body: str) -> str:
    lines: list[str] = []
    for ln in body.splitlines():
        s = ln.strip()
        if not s or s == "---":
            continue
        if s.startswith("#"):
            continue
        lines.append(s)
        if len(" ".join(lines)) >= _PREVIEW_CHARS:
            break
    text = " ".join(lines).strip() or body.strip()
    if len(text) > _PREVIEW_CHARS:
        return text[:_PREVIEW_CHARS].rstrip() + "…"
    return text


def _iter_tier_files(tier: MemoryTier) -> Iterable[Path]:
    root = _tier_root(tier)
    if not root.is_dir():
        return
    if tier == MemoryTier.LONG:
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            if any(part in _LONG_SKIP_DIRS for part in p.relative_to(root).parts):
                continue
            if p.name.startswith(".") or p.name in _SKIP_NAMES:
                continue
            if p.suffix.lower() not in (".md", ".txt"):
                continue
            yield p
        return
    for p in sorted(root.iterdir()):
        if not p.is_file():
            continue
        if p.name.startswith(".") or p.name in _SKIP_NAMES:
            continue
        if p.suffix.lower() not in (".md", ".txt"):
            continue
        yield p


def list_memory_entries(tier: MemoryTier) -> List[MemoryEntry]:
    """列出指定层级的全部记忆条目（按修改时间倒序）。"""
    ensure_palace_layout(_resolve_palace_root())
    repo = _resolve_palace_root()
    entries: list[MemoryEntry] = []
    for fp in _iter_tier_files(tier):
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.debug("读取记忆失败 %s: %s", fp, exc)
            continue
        meta, body = _split_frontmatter(text)
        try:
            rel = str(fp.resolve().relative_to(repo.resolve())).replace("\\", "/")
        except ValueError:
            rel = fp.name
        try:
            mtime = fp.stat().st_mtime
        except OSError:
            mtime = 0.0
        display_title, _, _ = resolve_display_title(path=fp, meta=meta, body=body)
        entries.append(
            MemoryEntry(
                id=rel,
                tier=tier,
                path=fp.resolve(),
                rel_path=rel,
                title=display_title,
                display_title=display_title,
                date_label=date_label_from_path(fp),
                preview=_preview_from_body(body),
                body=body.strip(),
                marked=_is_marked(meta, text),
                modified_at=mtime,
                needs_ai_title=not bool((meta.get(DISPLAY_TITLE_KEY) or "").strip()),
            )
        )
    entries.sort(key=lambda e: e.modified_at, reverse=True)
    return entries


def _build_frontmatter(meta: dict[str, str]) -> str:
    lines = ["---"]
    for k, v in meta.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _apply_mark_to_text(text: str, *, marked: bool) -> str:
    meta, body = _split_frontmatter(text)
    if marked:
        meta[_MARK_KEY] = "true"
        meta[_MARK_TIME_KEY] = datetime.now().isoformat(timespec="seconds")
    else:
        meta.pop(_MARK_KEY, None)
        meta.pop(_MARK_TIME_KEY, None)
    if meta:
        return _build_frontmatter(meta) + body.lstrip("\n")
    return body.lstrip("\n")


def read_memory_detail(path: Path) -> tuple[str, str]:
    """返回 (展示标题, 正文不含 frontmatter)。"""
    fp = path.resolve()
    text = fp.read_text(encoding="utf-8")
    meta, body = _split_frontmatter(text)
    display, _, _ = resolve_display_title(path=fp, meta=meta, body=body)
    return display, body.strip()


def entries_needing_ai_titles(entries: List[MemoryEntry], *, limit: int = 24) -> List[MemoryEntry]:
    """筛选待生成 AI 标题的条目（已缓存的跳过）。"""
    out: list[MemoryEntry] = []
    for e in entries:
        if e.needs_ai_title:
            out.append(e)
        if len(out) >= limit:
            break
    return out


def toggle_memory_mark(path: Path) -> bool:
    """
    切换单条记忆的重要标记；写入仓库后镜像 Obsidian。
    返回切换后的 marked 状态；失败时抛出 OSError。
    """
    fp = path.resolve()
    if not fp.is_file():
        raise OSError(f"文件不存在：{fp}")
    text = fp.read_text(encoding="utf-8")
    meta, _ = _split_frontmatter(text)
    new_marked = not _is_marked(meta, text)
    fp.write_text(_apply_mark_to_text(text, marked=new_marked), encoding="utf-8")
    publish_palace_file(fp)
    return new_marked


def _delete_chroma_for_file(file_path: Path) -> int:
    """按 file_path 元数据删除 Chroma 向量；返回删除条数。"""
    fp_str = str(file_path.resolve())
    try:
        from neuralpal.memory.chroma_runtime import get_chroma_client
        from langchain_chroma import Chroma

        from neuralpal.memory.chroma_embeddings import get_memory_embeddings

        chroma_dir = _resolve_chroma_path()
        if not chroma_dir.is_dir():
            return 0

        client = get_chroma_client(chroma_dir)
        vs = Chroma(
            collection_name=LONG_TERM_COLLECTION_NAME,
            embedding_function=get_memory_embeddings(),
            persist_directory=str(chroma_dir),
            client=client,
        )
        col = vs._collection
        got = col.get(include=["metadatas"])
        ids_to_delete: list[str] = []
        for vid, meta in zip(got.get("ids") or [], got.get("metadatas") or []):
            m = meta or {}
            stored = str(m.get("file_path") or "")
            if stored == fp_str or stored.endswith(file_path.name):
                ids_to_delete.append(vid)
        if ids_to_delete:
            col.delete(ids=ids_to_delete)
        return len(ids_to_delete)
    except Exception as exc:
        logger.warning("Chroma 删除失败（文件已删）：%s", exc)
        return 0


def delete_palace_memory(path: Path) -> None:
    """删除仓库记忆文件、Obsidian 镜像及 Chroma 索引。"""
    fp = path.resolve()
    repo = _resolve_palace_root()
    if not fp.is_file():
        raise OSError(f"文件不存在：{fp}")
    try:
        fp.relative_to(repo.resolve())
    except ValueError as exc:
        raise OSError("只能删除 knowledge_palace 仓库内的记忆文件") from exc

    rel = _rel_to_repo_palace(fp)
    _delete_chroma_for_file(fp)

    fp.unlink()

    obs_root = get_obsidian_palace_root()
    if obs_root is not None and rel is not None:
        obs_file = obs_root / rel
        if obs_file.is_file():
            try:
                obs_file.unlink()
            except OSError as exc:
                logger.warning("Obsidian 镜像删除失败 %s: %s", obs_file, exc)
