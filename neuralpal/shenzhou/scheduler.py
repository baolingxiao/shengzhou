# -*- coding: utf-8 -*-
"""沈昼世界定时任务：23:59 用户日结 → 00:05 世界流水线 → 00:15 拉取生活上下文。"""

from __future__ import annotations

import logging
import threading
from datetime import date, datetime
from zoneinfo import ZoneInfo

from neuralpal.config import get_settings
from neuralpal.shenzhou.client import fetch_life_context, ping, run_daily_pipeline
from neuralpal.shenzhou.sync import cache_life_context, push_user_day_to_world

logger = logging.getLogger(__name__)

_scheduler_lock = threading.Lock()
_scheduler_started = False


def _tz() -> ZoneInfo:
    return ZoneInfo(get_settings().shenzhou_timezone)


def _now_local() -> datetime:
    return datetime.now(_tz())


def job_sync_user_day(session_id: str | None = None) -> dict:
    settings = get_settings()
    sid = (session_id or settings.shenzhou_default_session_id).strip()
    if not sid:
        logger.warning("[shenzhou-scheduler] skip user sync: no session_id")
        return {"ok": False, "reason": "no_session"}
    try:
        result = push_user_day_to_world(
            sid,
            _now_local().date(),
            user_display_name=settings.shenzhou_user_display_name,
        )
        return {"ok": True, "result": result}
    except Exception as exc:
        logger.exception("[shenzhou-scheduler] user day sync failed")
        return {"ok": False, "error": str(exc)}


def job_world_daily_pipeline(*, skip_bulk_fix: bool = False, skip_simulation: bool = False) -> dict:
    try:
        result = run_daily_pipeline(
            _now_local().date(),
            skip_bulk_fix=skip_bulk_fix,
            skip_simulation=skip_simulation,
        )
        return {"ok": True, "result": result}
    except Exception as exc:
        logger.exception("[shenzhou-scheduler] daily pipeline failed")
        return {"ok": False, "error": str(exc)}


def job_pull_life_context() -> dict:
    today = _now_local().date()
    try:
        ctx = fetch_life_context(today)
        path = cache_life_context(ctx, today)
        return {"ok": True, "cache": str(path), "date": today.isoformat()}
    except Exception as exc:
        logger.exception("[shenzhou-scheduler] pull life context failed")
        return {"ok": False, "error": str(exc)}


def _should_run(hour: int, minute: int, last_key: str, state: dict) -> bool:
    now = _now_local()
    key = f"{now.date().isoformat()}:{hour:02d}:{minute:02d}"
    if now.hour == hour and now.minute == minute and state.get(last_key) != key:
        state[last_key] = key
        return True
    return False


def _tick(state: dict) -> None:
    settings = get_settings()
    if not settings.shenzhou_integration_enabled:
        return

    if _should_run(settings.shenzhou_sync_hour, settings.shenzhou_sync_minute, "last_sync", state):
        logger.info("[shenzhou-scheduler] running 23:59 user day sync")
        job_sync_user_day()

    if _should_run(
        settings.shenzhou_pipeline_hour,
        settings.shenzhou_pipeline_minute,
        "last_pipeline",
        state,
    ):
        logger.info("[shenzhou-scheduler] running world daily pipeline")
        job_world_daily_pipeline()

    if _should_run(
        settings.shenzhou_pull_hour,
        settings.shenzhou_pull_minute,
        "last_pull",
        state,
    ):
        logger.info("[shenzhou-scheduler] pulling life context")
        job_pull_life_context()


def _scheduler_loop(interval_seconds: int) -> None:
    import time

    state: dict = {}
    logger.info("[shenzhou-scheduler] started interval=%ss tz=%s", interval_seconds, get_settings().shenzhou_timezone)
    while True:
        try:
            _tick(state)
        except Exception:
            logger.exception("[shenzhou-scheduler] tick failed")
        time.sleep(interval_seconds)


def start_shenzhou_scheduler(*, interval_seconds: int = 30) -> bool:
    global _scheduler_started
    settings = get_settings()
    if not settings.shenzhou_integration_enabled or not settings.shenzhou_scheduler_enabled:
        logger.info("[shenzhou-scheduler] disabled (integration=%s scheduler=%s)",
                    settings.shenzhou_integration_enabled, settings.shenzhou_scheduler_enabled)
        return False

    with _scheduler_lock:
        if _scheduler_started:
            return True
        if settings.shenzhou_world_api_url.strip() and not ping():
            logger.warning(
                "[shenzhou-scheduler] world engine not reachable at %s — scheduler still started",
                settings.shenzhou_world_api_url,
            )
        t = threading.Thread(
            target=_scheduler_loop,
            args=(interval_seconds,),
            name="shenzhou-scheduler",
            daemon=True,
        )
        t.start()
        _scheduler_started = True
        return True


def run_daily_for_user(user_id: str, *, companion_instance_id: str | None = None) -> None:
    del companion_instance_id
    job_sync_user_day(user_id)
