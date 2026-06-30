# -*- coding: utf-8 -*-
"""沈昼桥接 API 鉴权（本地 Mac ↔ 云端贾维斯）。"""

from __future__ import annotations

from fastapi import Header, HTTPException

from neuralpal.config import get_settings


def require_shenzhou_bridge_token(authorization: str | None = Header(None, alias="Authorization")) -> None:
    token = get_settings().shenzhou_internal_token.strip()
    if not token:
        raise HTTPException(status_code=503, detail="SHENZHOU_INTERNAL_TOKEN not configured")
    expected = f"Bearer {token}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
