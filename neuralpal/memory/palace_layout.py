# -*- coding: utf-8 -*-
"""
记忆目录布局：仓库 knowledge_palace 为主存储，可选镜像到 Obsidian。

写入顺序：先仓库 → 再同步到 {Vault}/NeuralPal/knowledge_palace（相同相对路径）。

结构（仓库与 Obsidian 一致）：
    00_规则层/
    01_短期记忆/
    02_中期记忆/
    03_长期记忆/
"""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import Final, Iterable, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_OBSIDIAN_MEMORY_SUBDIR: Final[str] = "NeuralPal/knowledge_palace"

DIR_RULES: Final[str] = "00_规则层"
DIR_SHORT: Final[str] = "01_短期记忆"
DIR_MEDIUM: Final[str] = "02_中期记忆"
DIR_LONG: Final[str] = "03_长期记忆"

MEMORY_TIER_DIRS: Final[tuple[str, ...]] = (
    DIR_RULES,
    DIR_SHORT,
    DIR_MEDIUM,
    DIR_LONG,
)

DEFAULT_LONG_TERM_TOPICS: Final[tuple[str, ...]] = (
    "用户画像",
    "项目知识",
    "情景与对话",
    "参考资料",
    "风险合规",
    "行为模式",
    "生活事务",
    "待整理",
)

ANCHORS_DIR_NAME: Final[str] = "_系统锚点"

LEGACY_SUBDIR_MAP: Final[dict[str, str]] = {
    "01_核心规则库": DIR_RULES,
    "02_NeuralPal项目专属知识库": "项目知识",
    "03_用户专属知识库": "用户画像",
    "03_情景记录": "情景与对话",
    "04_项目相关": "项目知识",
    "04_技术栈库": "项目知识",
    "05_风险库": "风险合规",
    "06_参考资料库": "参考资料",
    "07_用户专属画像库": "用户画像",
    "07_生活事务": "生活事务",
    "07_行为模式库": "行为模式",
    "08_待整理": "待整理",
    "09_对话历史归档": DIR_MEDIUM,
}


def _project_root() -> Path:
    from neuralpal.config.settings import _project_root as pr

    return pr()


def obsidian_sync_enabled() -> bool:
    """是否将仓库 knowledge_palace 镜像到 Obsidian。"""
    from neuralpal.config import get_settings

    s = get_settings()
    if not bool(getattr(s, "memory_unify_obsidian", True)):
        return False
    return getattr(s, "obsidian_vault_path", None) is not None


def get_repo_palace_root() -> Path:
    """主存储：仓库内 NEURALPAL_KNOWLEDGE_PALACE。"""
    from neuralpal.config import get_settings

    return Path(get_settings().knowledge_palace_root).expanduser().resolve()


def get_obsidian_palace_root() -> Optional[Path]:
    """Obsidian 镜像根：{Vault}/NeuralPal/knowledge_palace；未配置 Vault 时返回 None。"""
    if not obsidian_sync_enabled():
        return None
    from neuralpal.config import get_settings

    s = get_settings()
    subdir = str(getattr(s, "obsidian_memory_subdir", "") or "").strip().strip("/")
    if not subdir:
        subdir = DEFAULT_OBSIDIAN_MEMORY_SUBDIR
    return Path(s.obsidian_vault_path).expanduser().resolve() / subdir


def get_palace_root() -> Path:
    """记忆读写的物理主根（仓库）。"""
    return get_repo_palace_root()


def legacy_palace_root() -> Path:
    """与 get_repo_palace_root 相同；兼容旧名。"""
    return get_repo_palace_root()


def path_rules(root: Path | None = None) -> Path:
    return (root or get_palace_root()) / DIR_RULES


def path_short(root: Path | None = None) -> Path:
    return (root or get_palace_root()) / DIR_SHORT


def path_medium(root: Path | None = None) -> Path:
    return (root or get_palace_root()) / DIR_MEDIUM


def path_long(root: Path | None = None) -> Path:
    return (root or get_palace_root()) / DIR_LONG


def path_anchors(root: Path | None = None) -> Path:
    return path_long(root) / ANCHORS_DIR_NAME


def path_magazine_reserve(root: Path | None = None) -> Path:
    return path_long(root) / "参考资料" / "杂志储备"


def _strip_legacy_prefix(name: str) -> str:
    s = (name or "").strip().replace("\\", "/")
    s = re.sub(r"^\d{2}_", "", s.split("/")[-1])
    return s or "待整理"


def resolve_memory_subdir(subdir: str, *, rolling_archive: bool = False) -> Path:
    if rolling_archive:
        return Path(DIR_MEDIUM)

    raw = (subdir or "").strip().replace("\\", "/")
    if not raw:
        return Path(DIR_LONG) / "待整理"

    if raw in MEMORY_TIER_DIRS:
        return Path(raw)

    if raw.startswith(f"{DIR_LONG}/"):
        return Path(raw)

    mapped = LEGACY_SUBDIR_MAP.get(raw)
    if mapped in MEMORY_TIER_DIRS:
        return Path(mapped)
    if mapped:
        return Path(DIR_LONG) / mapped

    if raw.startswith("03_长期记忆/"):
        return Path(raw)

    topic = _strip_legacy_prefix(raw)
    return Path(DIR_LONG) / topic


def ensure_palace_layout(root: Path | None = None) -> Path:
    """创建四层目录（默认仓库根）。"""
    r = root or get_palace_root()
    try:
        r.mkdir(parents=True, exist_ok=True)
        for tier in MEMORY_TIER_DIRS:
            (r / tier).mkdir(parents=True, exist_ok=True)
        for topic in DEFAULT_LONG_TERM_TOPICS:
            (r / DIR_LONG / topic).mkdir(parents=True, exist_ok=True)
        path_anchors(r).mkdir(parents=True, exist_ok=True)
        path_magazine_reserve(r).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("创建 knowledge_palace 目录失败：%s", exc)
    return r


def ensure_dual_palace_layout() -> tuple[Path, Optional[Path]]:
    """确保仓库与 Obsidian 两侧目录结构存在。"""
    repo = ensure_palace_layout(get_repo_palace_root())
    obs = get_obsidian_palace_root()
    if obs is not None:
        ensure_palace_layout(obs)
    return repo, obs


def _rel_to_repo_palace(abs_path: Path) -> Optional[Path]:
    repo = get_repo_palace_root()
    try:
        return abs_path.resolve().relative_to(repo.resolve())
    except ValueError:
        return None


def mirror_file_to_obsidian(src: Path) -> Optional[Path]:
    """
    将仓库内已写入的文件镜像到 Obsidian（覆盖同名文件）。
    src 必须在仓库 knowledge_palace 树下。
    """
    obs_root = get_obsidian_palace_root()
    if obs_root is None or not src.is_file():
        return None
    rel = _rel_to_repo_palace(src)
    if rel is None:
        return None
    dst = obs_root / rel
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return dst
    except OSError as exc:
        logger.warning("Obsidian 镜像失败 %s → %s：%s", src, dst, exc)
        return None


def publish_palace_file(src: Path) -> Path:
    """仓库文件写入完成后调用：镜像到 Obsidian。"""
    mirror_file_to_obsidian(src)
    return src


def list_classifier_subdirs(root: Path | None = None) -> List[str]:
    r = root or get_palace_root()
    ensure_palace_layout(r)
    long_root = r / DIR_LONG
    names: list[str] = []
    try:
        for p in sorted(long_root.iterdir()):
            if p.is_dir() and not p.name.startswith("."):
                names.append(f"{DIR_LONG}/{p.name}")
    except OSError:
        pass
    if not names:
        names = [f"{DIR_LONG}/{t}" for t in DEFAULT_LONG_TERM_TOPICS]
    names.append(DIR_MEDIUM)
    return names


def resolve_palace_file_path(file_path: str) -> Optional[Path]:
    if not file_path:
        return None
    p = Path(file_path)
    if p.is_file():
        return p

    normalized = str(p).replace("\\", "/")
    roots: list[Path] = [get_repo_palace_root()]
    obs = get_obsidian_palace_root()
    if obs is not None:
        roots.append(obs)

    for marker in ("knowledge_palace", "知识殿堂", "记忆殿堂"):
        if marker not in normalized:
            continue
        rel = normalized.split(marker, 1)[1].lstrip("/")
        if not rel:
            continue
        for root in roots:
            candidate = root / rel
            if candidate.is_file():
                return candidate
            if rel.startswith("09_对话历史归档/"):
                alt = root / DIR_MEDIUM / Path(rel).name
                if alt.is_file():
                    return alt

    # suffix swap fallback: .txt <-> .md
    if p.suffix.lower() == ".txt":
        for root in roots:
            alt = root / Path(normalized).name.replace(".txt", ".md")
            if alt.is_file():
                return alt
    elif p.suffix.lower() == ".md":
        for root in roots:
            alt = root / Path(normalized).name.replace(".md", ".txt")
            if alt.is_file():
                return alt

    name = p.name
    stem = p.stem
    for root in roots:
        matches = [m for m in root.rglob(name) if m.is_file()]
        if len(matches) == 1:
            return matches[0]
        # base-name fallback for migrated extension
        alt_matches = [m for m in root.rglob(f"{stem}.*") if m.is_file() and m.suffix.lower() in (".md", ".txt")]
        if len(alt_matches) == 1:
            return alt_matches[0]
    return None


def _safe_session_slug(session_id: str) -> str:
    s = re.sub(r"[^\w\-.]", "_", (session_id or "default").strip())[:80]
    return s or "default"


def sync_short_term_snapshot(
    *,
    session_id: str,
    messages: Iterable,
    rolled_summaries: Iterable[str] | None = None,
    palace_root: Path | None = None,
) -> Path | None:
    """短期记忆：先写仓库 01_短期记忆，再镜像 Obsidian。"""
    from langchain_core.messages import AIMessage, HumanMessage

    repo = ensure_palace_layout(palace_root or get_repo_palace_root())
    out = path_short(repo) / f"{_safe_session_slug(session_id)}.md"
    lines: list[str] = [
        "# 短期工作记忆",
        "",
        f"- 会话：`{session_id}`",
        f"- 仓库：`{repo}`",
        "",
        "## 当前窗口（完整轮次）",
        "",
    ]
    for m in messages:
        if isinstance(m, HumanMessage):
            role = "用户"
        elif isinstance(m, AIMessage):
            role = "助手"
        else:
            role = type(m).__name__
        body = getattr(m, "content", "")
        if isinstance(body, list):
            body = "".join(str(x) for x in body)
        lines.append(f"### {role}\n\n{str(body).strip()}\n")

    rolled = list(rolled_summaries or [])
    if rolled:
        lines.extend(["", "## 已滚出窗口的摘要", ""])
        for s in rolled[-12:]:
            lines.append(f"- {s.strip()}")

    try:
        out.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        publish_palace_file(out)
        try:
            from neuralpal.memory.memory_ids import ensure_memory_id
            from neuralpal.memory.palace_browser import MemoryTier

            ensure_memory_id(repo, out, MemoryTier.SHORT)
        except Exception as exc:
            logger.debug("短期记忆编号写入跳过：%s", exc)
        return out
    except OSError as exc:
        logger.warning("短期记忆快照写入失败：%s", exc)
        return None


def sync_repo_palace_to_obsidian(*, dry_run: bool = False) -> dict[str, int]:
    """
    将仓库 knowledge_palace 全量镜像到 Obsidian knowledge_palace（覆盖同名文件）。
    用于 /memory_sync 或首次对齐。
    """
    stats = {"copied": 0, "skipped": 0, "errors": 0}
    obs = get_obsidian_palace_root()
    if obs is None:
        return stats

    src = ensure_palace_layout(get_repo_palace_root())
    ensure_palace_layout(obs)

    for f in sorted(src.rglob("*")):
        if not f.is_file() or f.name.startswith("."):
            continue
        rel = f.relative_to(src)
        dst = obs / rel
        if dry_run:
            stats["copied"] += 1
            continue
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
            stats["copied"] += 1
        except OSError:
            stats["errors"] += 1

    return stats


def migrate_legacy_palace_to_obsidian(*, dry_run: bool = False) -> dict[str, int]:
    """
    将仓库内「旧版 NN_ 子目录」整理进四层布局后，再全量镜像 Obsidian。
    不删除旧目录中的源文件。
    """
    src = get_repo_palace_root()
    stats = {"copied": 0, "skipped": 0, "errors": 0}
    if not src.is_dir():
        return sync_repo_palace_to_obsidian(dry_run=dry_run)

    repo = ensure_palace_layout(src)

    def _import_file(sp: Path, target_dir: Path, name: str | None = None) -> None:
        target_dir.mkdir(parents=True, exist_ok=True)
        fname = name or sp.name
        dp = target_dir / fname
        if dp.exists():
            stats["skipped"] += 1
            return
        if dry_run:
            stats["copied"] += 1
            return
        try:
            shutil.copy2(sp, dp)
            stats["copied"] += 1
        except OSError:
            stats["errors"] += 1

    for item in sorted(src.iterdir()):
        if item.name.startswith(".") or not item.is_dir():
            continue
        if item.name in MEMORY_TIER_DIRS:
            continue
        if item.name == "anchors":
            for f in item.rglob("*"):
                if f.is_file():
                    _import_file(f, path_anchors(repo))
            continue
        if item.name == "01_核心规则库":
            for f in item.rglob("*"):
                if f.is_file():
                    _import_file(f, path_rules(repo), f.name)
            continue
        if item.name in ("09_对话历史归档", "03_情景记录"):
            for f in item.rglob("*"):
                if not f.is_file() or f.suffix.lower() not in (".txt", ".md"):
                    continue
                _import_file(f, path_medium(repo))
            continue
        topic = LEGACY_SUBDIR_MAP.get(item.name, _strip_legacy_prefix(item.name))
        if topic in MEMORY_TIER_DIRS:
            topic = _strip_legacy_prefix(item.name)
        target = path_long(repo) / topic
        for f in item.rglob("*"):
            if not f.is_file() or f.suffix.lower() not in (".txt", ".md"):
                continue
            _import_file(f, target, f.name)

    mirror_stats = sync_repo_palace_to_obsidian(dry_run=dry_run)
    stats["copied"] += mirror_stats["copied"]
    stats["errors"] += mirror_stats["errors"]
    return stats
