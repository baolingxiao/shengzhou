# -*- coding: utf-8 -*-
"""亲密度（TP）API。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from neuralpal.characters.constants import DEFAULT_CHARACTER_ID
from server.auth import is_admin_username
from server.trust_service import get_trust_snapshot, set_trust_points

router = APIRouter(tags=["trust"])


@router.get("/api/auth/role")
async def api_auth_role(username: str = Query(..., min_length=1)) -> dict[str, object]:
    name = username.strip()
    return {"username": name, "is_admin": is_admin_username(name)}


class TrustUpdateRequest(BaseModel):
    username: str = Field(..., min_length=1)
    character_id: str | None = Field(default=None)
    trust_points: int = Field(..., ge=0, le=100)


@router.get("/api/trust")
async def api_get_trust(character_id: str = DEFAULT_CHARACTER_ID) -> dict[str, object]:
    try:
        return get_trust_snapshot(character_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/api/admin/trust")
async def api_set_trust(payload: TrustUpdateRequest) -> dict[str, object]:
    if not is_admin_username(payload.username.strip()):
        raise HTTPException(status_code=403, detail="仅管理者可调整亲密度")
    cid = (payload.character_id or DEFAULT_CHARACTER_ID).strip()
    try:
        return set_trust_points(cid, payload.trust_points, actor=payload.username.strip())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
