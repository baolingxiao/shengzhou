# -*- coding: utf-8 -*-
"""本机文件操作（不依赖 Claude Computer Use API）。"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from neuralpal.desktop.routing import looks_like_file_operation, proposal_blob

_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".heic", ".webp", ".bmp", ".tiff", ".tif"}
_VIDEO_EXT = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".wmv", ".webm"}


def _desktop_dir() -> Path:
    return Path.home() / "Desktop"


def _extract_folder_name(text: str) -> str:
    quoted = re.findall(r"[「『\"']([^」』\"']+)[」』\"']", text)
    for name in quoted:
        name = name.strip()
        if name and name not in ("桌面",):
            return name
    m = re.search(r"文件夹[「『\"']([^」』\"']+)[」』\"']", text)
    if m:
        return m.group(1).strip()
    if "媒体" in text:
        return "媒体文件"
    return "媒体文件"


def looks_like_desktop_media_organize(proposal) -> bool:
    if not looks_like_file_operation(proposal):
        return False
    blob = proposal_blob(proposal)
    keys = ("桌面", "图片", "照片", "视频", "媒体", "整理", "存放", "文件夹")
    if not any(k in blob for k in keys):
        return False
    return any(k in blob for k in ("图片", "照片", "视频", "媒体", ".jpg", ".mp4", "移动"))


def organize_desktop_media(*, folder_name: str | None = None) -> str:
    desktop = _desktop_dir()
    if not desktop.is_dir():
        return f"【执行失败】未找到桌面目录：{desktop}"

    target_name = (folder_name or "媒体文件").strip() or "媒体文件"
    dest = desktop / target_name
    dest.mkdir(exist_ok=True)

    moved: list[str] = []
    skipped: list[str] = []

    for item in sorted(desktop.iterdir()):
        if item.name.startswith("."):
            continue
        if item.name == target_name:
            continue
        if item.suffix.lower() not in _IMAGE_EXT | _VIDEO_EXT:
            continue
        if item.is_dir():
            skipped.append(item.name)
            continue
        try:
            target = dest / item.name
            if target.exists():
                stem, suf = item.stem, item.suffix
                n = 1
                while target.exists():
                    target = dest / f"{stem}_{n}{suf}"
                    n += 1
            shutil.move(str(item), str(target))
            moved.append(item.name)
        except Exception as exc:
            skipped.append(f"{item.name}({exc})")

    if not moved:
        return (
            f"桌面未发现可移动的图片/视频文件。"
            f"目标文件夹：{dest}"
            + (f"；跳过：{', '.join(skipped)}" if skipped else "")
        )

    lines = [
        f"已完成：将 {len(moved)} 个文件移入「{target_name}」",
        f"路径：{dest}",
        "文件：" + "、".join(moved[:20]) + ("…" if len(moved) > 20 else ""),
    ]
    if skipped:
        lines.append("跳过：" + "、".join(skipped[:10]))
    return "\n".join(lines)


def _extract_basename(text: str) -> str | None:
    quoted = re.findall(r"[「『\"']([^」』\"']+)[」』\"']", text)
    for name in quoted:
        name = name.strip()
        if name and name not in ("桌面", "媒体文件"):
            return name
    m = re.search(r"文件名(?:叫|是|为)?[「『\"']?([^」』\"'\s，。]+)", text)
    if m:
        return m.group(1).strip()
    return None


def looks_like_move_file_to_desktop(proposal) -> bool:
    if not looks_like_file_operation(proposal):
        return False
    blob = proposal_blob(proposal)
    move_keys = ("移动", "移到", "搬到", "放到桌面", "移出", "移到桌面")
    if not any(k in blob for k in move_keys):
        return False
    if _extract_basename(blob):
        return True
    return "桌面" in blob and any(k in blob for k in ("文件", "视频", "媒体"))


def find_and_move_to_desktop(*, basename: str, source_hint: str | None = None) -> str:
    desktop = _desktop_dir()
    if not desktop.is_dir():
        return f"【执行失败】未找到桌面目录：{desktop}"

    name = basename.strip()
    if not name:
        return "【执行失败】未指定文件名。"

    search_roots: list[Path] = []
    if source_hint:
        hint_path = desktop / source_hint.strip("/")
        if hint_path.is_dir():
            search_roots.append(hint_path)
    media = desktop / "媒体文件"
    if media.is_dir() and media not in search_roots:
        search_roots.append(media)
    search_roots.append(desktop)

    matches: list[Path] = []
    for root in search_roots:
        try:
            for item in root.iterdir():
                if item.is_file() and name.lower() in item.name.lower():
                    matches.append(item)
        except OSError:
            continue

    if not matches:
        searched = "、".join(str(p) for p in search_roots)
        return f"在以下位置未找到文件名含「{name}」的文件：{searched}"

    if len(matches) > 1:
        lines = [f"找到 {len(matches)} 个匹配，请指定更精确的文件名："]
        lines.extend(f"  · {p}" for p in matches[:10])
        return "\n".join(lines)

    src = matches[0]
    dest = desktop / src.name
    if src.resolve() == dest.resolve():
        return f"文件已在桌面：{dest}"

    try:
        if dest.exists():
            stem, suf = src.stem, src.suffix
            n = 1
            while dest.exists():
                dest = desktop / f"{stem}_{n}{suf}"
                n += 1
        shutil.move(str(src), str(dest))
        return f"已完成：将「{src.name}」从 {src.parent} 移到桌面\n路径：{dest}"
    except Exception as exc:
        return f"【执行失败】移动 {src} → {dest}：{exc}"


def run_local_file_task(proposal) -> str | None:
    blob = " ".join([str(proposal.goal or ""), *list(proposal.steps or [])])

    if looks_like_move_file_to_desktop(proposal):
        basename = _extract_basename(blob) or ""
        if not basename:
            for step in proposal.steps or []:
                basename = _extract_basename(str(step)) or basename
                if basename:
                    break
        if basename:
            source = "媒体文件" if "媒体" in blob else None
            return find_and_move_to_desktop(basename=basename, source_hint=source)

    if not looks_like_desktop_media_organize(proposal):
        return None
    folder = _extract_folder_name(
        " ".join([str(proposal.goal or ""), *list(proposal.steps or [])])
    )
    return organize_desktop_media(folder_name=folder)
