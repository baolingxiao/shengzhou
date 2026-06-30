# -*- coding: utf-8 -*-
"""Trace HTTP 路由：客户端事件合并与查询。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from neuralpal.trace.recorder import merge_client_patch
from neuralpal.trace.storage import load_trace

router = APIRouter(prefix="/api/trace", tags=["trace"])


class ClientTracePatch(BaseModel):
    model_config = ConfigDict(extra="allow")

    trace_id: str = Field(..., min_length=8)
    pipeline: dict[str, Any] | None = None
    tts: dict[str, Any] | None = None
    timings: dict[str, Any] | None = None
    errors: list[dict[str, Any]] | None = None


@router.get("/{trace_id}")
async def get_trace(trace_id: str) -> dict[str, Any]:
    data = load_trace(trace_id.strip())
    if data is None:
        raise HTTPException(status_code=404, detail="trace 不存在")
    return data


@router.post("/client")
async def post_client_trace(payload: ClientTracePatch) -> dict[str, object]:
    patch: dict[str, Any] = {}
    if payload.pipeline is not None:
        patch["pipeline"] = payload.pipeline
    if payload.tts is not None:
        patch["tts"] = payload.tts
    if payload.timings is not None:
        patch["timings"] = payload.timings
    if payload.errors:
        patch["errors"] = payload.errors
    extra = payload.model_dump(
        exclude={"trace_id", "pipeline", "tts", "timings", "errors"},
        exclude_none=True,
    )
    patch.update(extra)
    merged = merge_client_patch(payload.trace_id.strip(), patch)
    return {"ok": True, "trace_id": payload.trace_id, "path": f"data/traces/{payload.trace_id}.json"}
