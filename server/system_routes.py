# -*- coding: utf-8 -*-
"""系统 API：版本、更新、macOS 权限。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from neuralpal.characters.constants import DEFAULT_SESSION_ID
from neuralpal.schedule.work_mode import get_work_mode_snapshot
from neuralpal.system.app_update import (
    apply_git_update,
    check_git_update,
    dismiss_update,
    get_app_version_info,
)
from neuralpal.system.permissions import (
    auto_setup_permissions,
    get_permissions_snapshot,
    open_system_settings,
)

router = APIRouter(prefix="/api/system", tags=["system"])


class DismissUpdateRequest(BaseModel):
    build_id: str = Field(..., min_length=1)


class OpenPermissionRequest(BaseModel):
    kind: Literal["accessibility", "screen_recording"]


@router.get("/version")
async def api_system_version() -> dict:
    return get_app_version_info()


@router.get("/update/check")
async def api_system_update_check(force: bool = False) -> dict:
    return check_git_update(force_fetch=force)


@router.post("/update/dismiss")
async def api_system_update_dismiss(payload: DismissUpdateRequest) -> dict:
    return dismiss_update(payload.build_id)


@router.post("/update/apply")
async def api_system_update_apply() -> dict:
    result = apply_git_update()
    if not result.get("ok"):
        raise HTTPException(status_code=500, detail=result.get("message") or "更新失败")
    return result


@router.get("/permissions")
async def api_system_permissions(force: bool = False) -> dict:
    del force  # 每次均实时探测；参数供前端区分「用户主动复检」
    snap = get_permissions_snapshot()
    snap["checked_at"] = datetime.now(timezone.utc).isoformat()
    return snap


@router.post("/permissions/open")
async def api_system_permissions_open(payload: OpenPermissionRequest) -> dict:
    ok = open_system_settings(payload.kind)
    if not ok:
        raise HTTPException(status_code=500, detail="无法打开系统设置")
    return {"ok": True, "kind": payload.kind}


@router.post("/permissions/auto-setup")
async def api_system_permissions_auto_setup() -> dict:
    """
    一键唤起 macOS 系统授权 UI（辅助功能 + 屏幕录制）。
    无法静默授权，但用户只需在系统弹窗/设置里点允许，无需手动 + 添加路径。
    """
    result = auto_setup_permissions()
    result["checked_at"] = datetime.now(timezone.utc).isoformat()
    return result


@router.get("/work-mode")
async def api_system_work_mode(
    session_id: str = DEFAULT_SESSION_ID,
    character_id: str | None = None,
) -> dict:
    """沈昼当前上下班 / 陪伴 / 加班模式。"""
    return get_work_mode_snapshot(session_id, character_id=character_id)
