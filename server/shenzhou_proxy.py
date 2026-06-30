# -*- coding: utf-8 -*-
"""将公网 /world/* 反代到沈昼世界引擎（nginx 未单独配置时由贾维斯兜底）。"""

from __future__ import annotations

import asyncio
import logging
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Request, Response

from neuralpal.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()

_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


def _forward_headers(request: Request) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in request.headers.items():
        lk = key.lower()
        if lk in _HOP_BY_HOP:
            continue
        headers[key] = value
    token = get_settings().shenzhou_internal_token.strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _sync_proxy(
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes | None,
    *,
    timeout: float,
) -> tuple[int, Iterable[tuple[str, str]], bytes]:
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            resp_headers = list(resp.headers.items())
            return resp.status, resp_headers, resp.read()
    except HTTPError as exc:
        return exc.code, list(exc.headers.items()), exc.read()
    except URLError as exc:
        raise RuntimeError(f"world engine unreachable: {exc}") from exc


@router.api_route(
    "/world/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
)
async def proxy_shenzhou_world(path: str, request: Request) -> Response:
    settings = get_settings()
    if not settings.shenzhou_integration_enabled:
        return Response(
            content='{"error":"shenzhou integration disabled"}',
            status_code=503,
            media_type="application/json",
        )

    base = settings.shenzhou_world_api_url.rstrip("/")
    query = request.url.query
    target = f"{base}/{path}" + (f"?{query}" if query else "")
    body = await request.body()
    timeout = settings.shenzhou_api_timeout_seconds
    if path.startswith("api/cron/"):
        timeout = max(timeout, 300.0)

    try:
        status, resp_headers, content = await asyncio.to_thread(
            _sync_proxy,
            request.method,
            target,
            _forward_headers(request),
            body if body else None,
            timeout=timeout,
        )
    except RuntimeError as exc:
        logger.warning("[shenzhou-proxy] %s → %s", request.url.path, exc)
        return Response(
            content=f'{{"error":"{exc}"}}',
            status_code=502,
            media_type="application/json",
        )

    out_headers: dict[str, str] = {}
    for key, value in resp_headers:
        lk = key.lower()
        if lk in _HOP_BY_HOP:
            continue
        out_headers[key] = value

    return Response(content=content, status_code=status, headers=out_headers)
