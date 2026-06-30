# -*- coding: utf-8 -*-
"""应用版本检测与 Git 更新（用户确认后才 apply）。"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from neuralpal.config import get_settings

logger = logging.getLogger(__name__)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_package_version() -> str:
    pkg = _project_root() / "package.json"
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
        return str(data.get("version") or "0.0.0")
    except (OSError, json.JSONDecodeError):
        return "0.0.0"


def _git_short_rev() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_project_root(),
            capture_output=True,
            text=True,
            timeout=8,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _git_branch() -> str:
    s = get_settings()
    if s.desktop_update_git_branch.strip():
        return s.desktop_update_git_branch.strip()
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=_project_root(),
            capture_output=True,
            text=True,
            timeout=8,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return "main"


def _load_state() -> dict[str, Any]:
    path = get_settings().desktop_update_state_path
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(state: dict[str, Any]) -> None:
    path = get_settings().desktop_update_state_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_app_version_info() -> dict[str, Any]:
    ver = _read_package_version()
    rev = _git_short_rev()
    return {
        "app_name": "贾维斯 · Neural Pal",
        "version": ver,
        "build_id": f"{ver}+{rev}",
        "git_rev": rev,
        "git_branch": _git_branch(),
        "channel": "pwa",
    }


def check_git_update(*, force_fetch: bool = False) -> dict[str, Any]:
    s = get_settings()
    base = get_app_version_info()
    result: dict[str, Any] = {
        **base,
        "update_available": False,
        "check_enabled": bool(s.desktop_update_check_enabled),
        "remote_rev": base["git_rev"],
        "commits_behind": 0,
        "summary": "",
        "dismissed_build_id": (_load_state().get("dismissed_build_id") or ""),
    }

    if not s.desktop_update_check_enabled:
        result["summary"] = "更新检测已关闭。"
        return result

    root = _project_root()
    if not (root / ".git").is_dir():
        result["summary"] = "非 Git 仓库，跳过远程更新检测。"
        return result

    remote = s.desktop_update_git_remote.strip() or "origin"
    branch = _git_branch()

    try:
        if force_fetch:
            subprocess.run(
                ["git", "fetch", remote, branch],
                cwd=root,
                capture_output=True,
                timeout=60,
            )
        local = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=8,
        )
        remote_ref = subprocess.run(
            ["git", "rev-parse", f"{remote}/{branch}"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=8,
        )
        if local.returncode != 0 or remote_ref.returncode != 0:
            result["summary"] = "无法解析本地或远程版本。"
            return result

        local_rev = local.stdout.strip()
        remote_rev = remote_ref.stdout.strip()
        result["remote_rev"] = remote_rev[:7]

        if local_rev != remote_rev:
            count = subprocess.run(
                ["git", "rev-list", "--count", f"HEAD..{remote}/{branch}"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=8,
            )
            behind = int(count.stdout.strip()) if count.returncode == 0 else 0
            result["update_available"] = True
            result["commits_behind"] = behind
            result["build_id"] = f"{base['version']}+{remote_rev[:7]}"
            log = subprocess.run(
                ["git", "log", "--oneline", "-5", f"HEAD..{remote}/{branch}"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=8,
            )
            result["summary"] = (log.stdout.strip() if log.returncode == 0 else "") or (
                f"远程有 {behind} 个新提交。"
            )
        else:
            result["summary"] = "已是最新版本。"
    except Exception as exc:
        logger.exception("git update check failed")
        result["summary"] = f"更新检测失败：{exc}"

    dismissed = result.get("dismissed_build_id") or ""
    if dismissed and dismissed == result.get("build_id") and result.get("update_available"):
        result["update_available"] = False
        result["summary"] = "你已推迟此版本更新。"

    return result


def dismiss_update(build_id: str) -> dict[str, Any]:
    state = _load_state()
    state["dismissed_build_id"] = build_id.strip()
    state["dismissed_at"] = datetime.now(timezone.utc).isoformat()
    _save_state(state)
    return {"ok": True, "dismissed_build_id": build_id}


def apply_git_update() -> dict[str, Any]:
    s = get_settings()
    root = _project_root()
    remote = s.desktop_update_git_remote.strip() or "origin"
    branch = _git_branch()

    steps: list[str] = []
    try:
        pull = subprocess.run(
            ["git", "pull", remote, branch],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=120,
        )
        steps.append(pull.stdout.strip() or pull.stderr.strip() or "git pull 完成")
        if pull.returncode != 0:
            return {"ok": False, "message": pull.stderr.strip() or "git pull 失败", "steps": steps}

        subprocess.run(
            ["npm", "install"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=300,
        )
        steps.append("npm install 完成")

        build = subprocess.run(
            ["npm", "run", "build"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=600,
        )
        steps.append(build.stdout.strip()[-500:] if build.stdout else "npm run build 完成")
        if build.returncode != 0:
            return {
                "ok": False,
                "message": build.stderr.strip() or "前端构建失败",
                "steps": steps,
            }

        script = s.desktop_update_script
        if script.is_file():
            subprocess.Popen(  # noqa: S603
                ["/bin/bash", str(script)],
                cwd=root,
                start_new_session=True,
            )
            steps.append(f"已启动更新脚本：{script.name}")

        state = _load_state()
        state.pop("dismissed_build_id", None)
        state["last_applied_at"] = datetime.now(timezone.utc).isoformat()
        _save_state(state)

        return {
            "ok": True,
            "message": "更新已应用，请稍后刷新或重启贾维斯。",
            "steps": steps,
            "build_id": get_app_version_info()["build_id"],
        }
    except Exception as exc:
        logger.exception("apply update failed")
        return {"ok": False, "message": str(exc), "steps": steps}
