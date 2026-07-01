# -*- coding: utf-8 -*-
"""记忆宫殿专属编号：ST_ / MT_ / LT_ 注册、回填与解析。"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Final

from neuralpal.memory.palace_browser import MemoryTier, _split_frontmatter
from neuralpal.memory.palace_layout import path_long, path_medium, path_short, publish_palace_file

logger = logging.getLogger(__name__)

MEMORY_ID_KEY: Final[str] = "neuralpal_memory_id"
REGISTRY_FILENAME: Final[str] = ".memory_id_registry.json"

_ID_RE = re.compile(r"^(ST|MT|LT)_(\d{4,})$")


def _tier_prefix(tier: MemoryTier | str) -> str:
    if isinstance(tier, MemoryTier):
        tier = tier.value
    return {"short": "ST", "medium": "MT", "long": "LT"}[tier.strip().lower()]


def _registry_path(palace_root: Path) -> Path:
    return palace_root.resolve() / REGISTRY_FILENAME


def _default_registry() -> dict[str, Any]:
    return {
        "counters": {"ST": 0, "MT": 0, "LT": 0},
        "by_id": {},
    }


def load_registry(palace_root: Path) -> dict[str, Any]:
    fp = _registry_path(palace_root)
    if not fp.is_file():
        return _default_registry()
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _default_registry()
        out = _default_registry()
        if isinstance(data.get("counters"), dict):
            out["counters"].update({k: int(v) for k, v in data["counters"].items() if k in out["counters"]})
        if isinstance(data.get("by_id"), dict):
            out["by_id"] = {str(k): str(v) for k, v in data["by_id"].items()}
        return out
    except Exception as exc:
        logger.warning("memory id registry load failed: %s", exc)
        return _default_registry()


def save_registry(palace_root: Path, registry: dict[str, Any]) -> None:
    fp = _registry_path(palace_root)
    fp.parent.mkdir(parents=True, exist_ok=True)
    tmp = fp.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(registry, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(fp)
    publish_palace_file(fp)


def parse_memory_id(memory_id: str) -> tuple[str, int] | None:
    m = _ID_RE.match((memory_id or "").strip().upper())
    if not m:
        return None
    return m.group(1), int(m.group(2))


def memory_id_from_meta(meta: dict[str, str]) -> str:
    return (meta.get(MEMORY_ID_KEY) or "").strip().upper()


def _next_id(registry: dict[str, Any], prefix: str) -> str:
    counters = registry.setdefault("counters", {"ST": 0, "MT": 0, "LT": 0})
    n = int(counters.get(prefix, 0)) + 1
    counters[prefix] = n
    return f"{prefix}_{n:04d}"


def _rel_path(palace_root: Path, fp: Path) -> str:
    return str(fp.resolve().relative_to(palace_root.resolve())).replace("\\", "/")


def ensure_memory_id(
    palace_root: Path,
    fp: Path,
    tier: MemoryTier,
    *,
    registry: dict[str, Any] | None = None,
) -> str:
    """为文件写入 frontmatter 编号；已存在则复用。"""
    palace_root = palace_root.resolve()
    fp = fp.resolve()
    if registry is None:
        registry = load_registry(palace_root)

    text = fp.read_text(encoding="utf-8")
    meta, body = _split_frontmatter(text)
    existing = memory_id_from_meta(meta)
    if existing and existing in registry.get("by_id", {}):
        return existing

    by_id: dict[str, str] = registry.setdefault("by_id", {})
    rel = _rel_path(palace_root, fp)
    for mid, rpath in by_id.items():
        if rpath == rel:
            if not meta.get(MEMORY_ID_KEY):
                meta[MEMORY_ID_KEY] = mid
                _write_frontmatter(fp, meta, body)
            return mid

    prefix = _tier_prefix(tier)
    mid = _next_id(registry, prefix)
    meta[MEMORY_ID_KEY] = mid
    by_id[mid] = rel
    _write_frontmatter(fp, meta, body)
    save_registry(palace_root, registry)
    return mid


def _write_frontmatter(fp: Path, meta: dict[str, str], body: str) -> None:
    lines = ["---"]
    for k, v in meta.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    fp.write_text("\n".join(lines) + body.lstrip("\n"), encoding="utf-8")
    publish_palace_file(fp)


def backfill_memory_ids(palace_root: Path) -> int:
    """为宫殿内缺编号的文件顺序分配 ST/MT/LT。"""
    palace_root = palace_root.resolve()
    registry = load_registry(palace_root)
    updated = 0
    tier_dirs = [
        (MemoryTier.SHORT, path_short(palace_root)),
        (MemoryTier.MEDIUM, path_medium(palace_root)),
        (MemoryTier.LONG, path_long(palace_root)),
    ]
    for tier, root in tier_dirs:
        if not root.is_dir():
            continue
        files = sorted(root.rglob("*.md") if tier == MemoryTier.LONG else root.glob("*.md"))
        for fp in files:
            if not fp.is_file() or fp.name.startswith("."):
                continue
            if "_archive" in fp.parts:
                continue
            before = memory_id_from_meta(_split_frontmatter(fp.read_text(encoding="utf-8"))[0])
            mid = ensure_memory_id(palace_root, fp, tier, registry=registry)
            if mid != before:
                updated += 1
    save_registry(palace_root, registry)
    return updated


def resolve_memory_by_id(palace_root: Path, memory_id: str) -> dict[str, Any] | None:
    parsed = parse_memory_id(memory_id)
    if not parsed:
        return None
    registry = load_registry(palace_root)
    rel = registry.get("by_id", {}).get(memory_id.strip().upper())
    if not rel:
        return None
    fp = (palace_root / rel).resolve()
    if not fp.is_file():
        return None
    meta, body = _split_frontmatter(fp.read_text(encoding="utf-8"))
    prefix, _ = parsed
    tier = {"ST": "short", "MT": "medium", "LT": "long"}[prefix]
    from neuralpal.memory.palace_browser import _is_marked

    return {
        "memory_id": memory_id.strip().upper(),
        "tier": tier,
        "rel_path": rel,
        "marked": _is_marked(meta, body),
        "body": body.strip(),
    }


def list_memory_catalog(palace_root: Path, *, tier: str | None = None) -> list[dict[str, Any]]:
    """供 AI 选号用的轻量目录（编号 + 标题 + 是否标记）。"""
    from neuralpal.memory.palace_browser import list_memory_entries

    tiers = [MemoryTier(tier)] if tier else [MemoryTier.SHORT, MemoryTier.MEDIUM, MemoryTier.LONG]
    out: list[dict[str, Any]] = []
    registry = load_registry(palace_root)
    for t in tiers:
        for entry in list_memory_entries(t):
            mid = memory_id_from_meta(_split_frontmatter(entry.path.read_text(encoding="utf-8"))[0])
            if not mid:
                mid = ensure_memory_id(palace_root, entry.path, t, registry=registry)
            out.append(
                {
                    "memory_id": mid,
                    "tier": t.value,
                    "title": entry.display_title,
                    "marked": entry.marked,
                    "preview": entry.preview[:160],
                    "rel_path": entry.rel_path,
                }
            )
    save_registry(palace_root, registry)
    return out
