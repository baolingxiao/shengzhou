# -*- coding: utf-8 -*-
"""记忆宫殿与聊天记录管理 API。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

from neuralpal.characters.constants import DEFAULT_CHARACTER_ID, DEFAULT_SESSION_ID
from neuralpal.memory.admin_service import (
    default_maintenance_hint,
    delete_memory,
    delete_memory_messages,
    get_memory_detail,
    list_memories,
    mark_memory,
    resolve_character_name,
    run_maintenance,
    summarize_tiers,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


class MaintenanceRequest(BaseModel):
    character_id: str | None = Field(default=None)
    action: str = Field(..., description="daily | weekly | monthly | catchup")
    dry_run: bool = False


class DeleteMemoryRequest(BaseModel):
    character_id: str | None = None
    rel_path: str


class MarkMemoryRequest(BaseModel):
    character_id: str | None = None
    rel_path: str


class DeleteMessagesRequest(BaseModel):
    character_id: str | None = None
    rel_path: str | None = None
    session_id: str | None = None
    indices: list[int] = Field(..., min_length=1)


def _character_name(character_id: str | None) -> str:
    return resolve_character_name(character_id)


@router.get("/memory/summary")
async def memory_summary(character_id: str = DEFAULT_CHARACTER_ID) -> dict[str, Any]:
    name = _character_name(character_id)
    try:
        counts = summarize_tiers(name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {
        "character": name,
        "character_id": character_id,
        "counts": counts,
        "maintenance_hint": default_maintenance_hint(),
    }


@router.get("/memory")
async def memory_list(
    tier: str = Query(..., description="short | medium | long"),
    character_id: str = DEFAULT_CHARACTER_ID,
) -> dict[str, Any]:
    name = _character_name(character_id)
    try:
        items = list_memories(name, tier)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"character": name, "tier": tier, "items": items}


@router.get("/memory/detail")
async def memory_detail(
    rel_path: str,
    character_id: str = DEFAULT_CHARACTER_ID,
) -> dict[str, Any]:
    name = _character_name(character_id)
    try:
        return get_memory_detail(name, rel_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/memory")
async def memory_delete(payload: DeleteMemoryRequest) -> dict[str, bool]:
    name = _character_name(payload.character_id)
    try:
        delete_memory(name, payload.rel_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/memory/mark")
async def memory_mark(payload: MarkMemoryRequest) -> dict[str, Any]:
    name = _character_name(payload.character_id)
    try:
        marked = mark_memory(name, payload.rel_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "marked": marked}


@router.post("/memory/maintenance")
async def memory_maintenance(payload: MaintenanceRequest) -> dict[str, Any]:
    name = _character_name(payload.character_id)
    try:
        result = run_maintenance(name, action=payload.action, dry_run=payload.dry_run)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"character": name, "result": result}


@router.post("/memory/titles")
async def memory_optimize_titles(
    background_tasks: BackgroundTasks,
    character_id: str = DEFAULT_CHARACTER_ID,
    limit: int = Query(24, ge=1, le=60),
) -> dict[str, Any]:
    """后台为未命名记忆生成「日期 + 摘要」展示标题（豆包 Lite，异步不阻塞列表）。"""
    from neuralpal.memory.admin_service import optimize_memory_titles

    name = _character_name(character_id)

    def _run() -> None:
        try:
            optimize_memory_titles(name, limit=limit)
        except Exception:
            import logging

            logging.getLogger(__name__).exception("optimize_memory_titles failed")

    background_tasks.add_task(_run)
    return {"character": name, "updated": 0, "queued": True}


def attach_memory_message_routes(router: APIRouter, chat_service: Any) -> None:
    @router.post("/memory/messages/delete")
    async def memory_messages_delete(payload: DeleteMessagesRequest) -> dict[str, Any]:
        name = _character_name(payload.character_id)
        if not payload.indices:
            raise HTTPException(status_code=400, detail="请指定要删除的消息下标")
        try:
            if payload.session_id and not payload.rel_path:
                result = chat_service.delete_live_messages(
                    payload.session_id,
                    payload.indices,
                    character_id=payload.character_id,
                )
                return {"character": name, "result": result}

            if not payload.rel_path:
                raise HTTPException(status_code=400, detail="缺少 rel_path 或 session_id")

            result = delete_memory_messages(name, payload.rel_path, payload.indices)
            session_id = str(result.get("session_id") or "")
            if session_id:
                chat_service.sync_orchestrator_after_file_edit(session_id)
            return {"character": name, "result": result}
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc


def attach_chat_admin_routes(router: APIRouter, chat_service: Any) -> None:
    """挂载聊天记录管理到同一 admin router。"""

    @router.get("/chat/history")
    async def chat_history(session_id: str = DEFAULT_SESSION_ID) -> dict[str, Any]:
        messages = chat_service.get_session_history(session_id)
        return {"session_id": session_id, "messages": messages, "count": len(messages)}

    @router.delete("/chat/session")
    async def chat_session_clear(session_id: str = DEFAULT_SESSION_ID) -> dict[str, bool]:
        chat_service.reset_session(session_id)
        return {"ok": True}
