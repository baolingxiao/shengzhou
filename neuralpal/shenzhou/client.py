# -*- coding: utf-8 -*-
"""沈昼世界引擎 HTTP 客户端。"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from neuralpal.config import get_settings

logger = logging.getLogger(__name__)


def _base_url() -> str:
    return get_settings().shenzhou_world_api_url.rstrip("/")


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    token = get_settings().shenzhou_internal_token.strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _request(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    url = f"{_base_url()}{path}"
    data = json.dumps(body or {}, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = Request(url, data=data, headers=_headers(), method=method)
    t = timeout or settings.shenzhou_api_timeout_seconds
    try:
        with urlopen(req, timeout=t) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        logger.warning("[shenzhou] HTTP %s %s: %s", exc.code, path, detail[:300])
        raise RuntimeError(f"shenzhou HTTP {exc.code}: {detail[:200]}") from exc
    except URLError as exc:
        logger.warning("[shenzhou] unreachable %s: %s", path, exc)
        raise RuntimeError(f"shenzhou unreachable: {exc}") from exc


def fetch_life_context(day: date | None = None) -> dict[str, Any]:
    q = f"?date={day.isoformat()}" if day else ""
    return _request("GET", f"/api/life/context{q}")


def sync_user_day(payload: dict[str, Any]) -> dict[str, Any]:
    return _request("POST", "/api/world/sync/user-day", body=payload)


def run_daily_pipeline(day: date | None = None, *, skip_bulk_fix: bool = False) -> dict[str, Any]:
    body: dict[str, Any] = {"skipBulkFix": skip_bulk_fix}
    if day:
        body["date"] = day.isoformat()
    return _request("POST", "/api/cron/daily-pipeline", body=body, timeout=300.0)


def ping() -> bool:
    try:
        _request("GET", "/api/life/context", timeout=8.0)
        return True
    except Exception:
        return False
