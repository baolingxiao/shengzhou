# -*- coding: utf-8 -*-
"""本机 App 启动（macOS open -a，不依赖 Claude Computer Use）。"""

from __future__ import annotations

import re
import subprocess

from neuralpal.desktop.routing import needs_computer_use, proposal_blob

# 中文俗称 → macOS 可识别的 App 名（按顺序尝试）
_APP_CANDIDATES: dict[str, list[str]] = {
    "微信": ["WeChat", "微信"],
    "wechat": ["WeChat", "微信"],
    "备忘录": ["Notes", "备忘录"],
    "notes": ["Notes", "备忘录"],
    "safari": ["Safari"],
    "浏览器": ["Safari", "Google Chrome", "Microsoft Edge"],
    "chrome": ["Google Chrome"],
    "谷歌浏览器": ["Google Chrome"],
    "edge": ["Microsoft Edge"],
    "finder": ["Finder"],
    "访达": ["Finder"],
    "终端": ["Terminal", "终端"],
    "terminal": ["Terminal", "终端"],
    "系统设置": ["System Settings", "系统设置"],
    "设置": ["System Settings", "系统设置"],
    "邮件": ["Mail", "邮件"],
    "mail": ["Mail", "邮件"],
    "音乐": ["Music", "音乐"],
    "music": ["Music", "音乐"],
    "日历": ["Calendar", "日历"],
    "calendar": ["Calendar", "日历"],
    "照片": ["Photos", "照片"],
    "photos": ["Photos", "照片"],
    "预览": ["Preview", "预览"],
    "preview": ["Preview", "预览"],
    "活动监视器": ["Activity Monitor", "活动监视器"],
}

_OPEN_VERBS = ("打开", "启动", "运行", "开启", "open", "launch")


def _extract_app_name(text: str) -> str | None:
    quoted = re.findall(r"[「『\"']([^」』\"']+)[」』\"']", text)
    for name in quoted:
        name = name.strip()
        if name and name not in ("桌面", "媒体文件"):
            return name
    for pat in (
        r"(?:打开|启动|运行|开启|open|launch)\s*[「『\"']?([^」』\"'\s，。]+)",
        r"([^」』\"'\s，。]+)\s*(?:应用|app|App)",
    ):
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            if name and name not in _OPEN_VERBS:
                return name
    return None


def looks_like_open_app(proposal) -> bool:
    if needs_computer_use(proposal):
        return False
    blob = proposal_blob(proposal).lower()
    if not any(v in blob for v in _OPEN_VERBS):
        return False
    # 排除「打开文件夹/文件/网页」
    if any(k in blob for k in ("文件夹", "文件", "网页", "网站", "http", ".mp4", ".jpg")):
        return False
    return _extract_app_name(blob) is not None


def _resolve_candidates(name: str) -> list[str]:
    key = name.strip().lower()
    if key in _APP_CANDIDATES:
        return list(_APP_CANDIDATES[key])
    if name.strip() in _APP_CANDIDATES:
        return list(_APP_CANDIDATES[name.strip()])
    return [name.strip()]


def open_mac_application(app_name: str) -> str:
    name = (app_name or "").strip()
    if not name:
        return "【执行失败】未指定要打开的应用。"

    tried: list[str] = []
    for candidate in _resolve_candidates(name):
        if not candidate or candidate in tried:
            continue
        tried.append(candidate)
        try:
            proc = subprocess.run(
                ["open", "-a", candidate],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if proc.returncode == 0:
                return f"已完成：已打开「{candidate}」"
            err = (proc.stderr or proc.stdout or "").strip()
            if err:
                tried.append(f"{candidate}({err[:80]})")
        except subprocess.TimeoutExpired:
            return f"【执行失败】打开「{candidate}」超时。"
        except OSError as exc:
            tried.append(f"{candidate}({exc})")

    return (
        f"【执行失败】未能打开「{name}」。"
        f"已尝试：{', '.join(tried) or name}。"
        "请确认该 App 已安装，或告诉我准确的英文应用名。"
    )


def run_local_app_task(proposal) -> str | None:
    if not looks_like_open_app(proposal):
        return None
    blob = " ".join([str(proposal.goal or ""), *list(proposal.steps or [])])
    app = _extract_app_name(blob)
    if not app:
        return None
    return open_mac_application(app)
