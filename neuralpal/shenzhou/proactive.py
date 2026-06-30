# -*- coding: utf-8 -*-
"""沈昼世界主动消息引擎：按事件时间窗口主动触达用户。"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from neuralpal.config import get_settings
from neuralpal.shenzhou.client import fetch_life_context

logger = logging.getLogger(__name__)

_STATE_FILE = ".proactive_state.json"
_LOG_FILE = "proactive_log.jsonl"
_WINDOW_KEYS = (
    "scheduledAt",
    "startAt",
    "startTime",
    "dueAt",
    "dueTime",
    "deadlineAt",
    "deadline",
    "time",
    "nextTriggerAt",
    "windowStartAt",
)
_INTENT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "progress_check",
        ("进度", "跟进", "follow up", "check in", "status", "推进", "确认进展", "同步进度"),
    ),
    (
        "invite_collab",
        ("一起", "有空", "约", "协作", "共同", "pair", "co-work", "一起完成"),
    ),
    (
        "message_user",
        ("发消息", "联系用户", "联系一下", "ping user", "ask user", "询问"),
    ),
)

_IN_APP_SENDER: Callable[[str, str, dict[str, Any]], bool] | None = None


def _tz() -> ZoneInfo:
    return ZoneInfo(get_settings().shenzhou_timezone)


def _cache_dir() -> Path:
    p = get_settings().shenzhou_cache_dir
    p.mkdir(parents=True, exist_ok=True)
    return p


def _state_path() -> Path:
    return _cache_dir() / _STATE_FILE


def _log_path() -> Path:
    return _cache_dir() / _LOG_FILE


def register_in_app_sender(sender: Callable[[str, str, dict[str, Any]], bool]) -> None:
    global _IN_APP_SENDER
    _IN_APP_SENDER = sender


def _parse_time(value: Any, *, tz: ZoneInfo) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=tz)
        return value.astimezone(tz)
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 10_000_000_000:
            ts = ts / 1000.0
        try:
            return datetime.fromtimestamp(ts, tz=tz)
        except Exception:
            return None
    s = str(value).strip()
    if not s:
        return None
    if s.isdigit():
        return _parse_time(float(s), tz=tz)
    normalized = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=tz)
        return dt.astimezone(tz)
    except ValueError:
        pass
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        try:
            d = date.fromisoformat(s)
            return datetime(d.year, d.month, d.day, 9, 0, tzinfo=tz)
        except Exception:
            return None
    return None


def _load_state() -> dict[str, Any]:
    p = _state_path()
    default = {
        "last_run_at": "",
        "daily_counts": {},
        "event_last_sent": {},
        "sent_log_keys": [],
    }
    if not p.is_file():
        return default
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return default
        default.update(data)
        return default
    except Exception:
        return default


def _save_state(state: dict[str, Any]) -> None:
    p = _state_path()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def _append_log(payload: dict[str, Any]) -> None:
    p = _log_path()
    line = json.dumps(payload, ensure_ascii=False)
    with p.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _load_today_context(day: date) -> dict[str, Any] | None:
    path = _cache_dir() / f"life_context_{day.isoformat()}.json"
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.debug("invalid life context cache: %s", path, exc_info=True)
    if not get_settings().shenzhou_world_api_url.strip():
        return None
    try:
        ctx = fetch_life_context(day)
    except Exception:
        logger.debug("fetch_life_context failed", exc_info=True)
        return None
    try:
        path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        logger.debug("cache write failed %s", path, exc_info=True)
    return ctx


def _event_candidates(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def add_many(items: Any, source: str) -> None:
        if not isinstance(items, list):
            return
        for x in items:
            if isinstance(x, dict):
                y = dict(x)
                y["_source"] = source
                out.append(y)

    add_many(ctx.get("lifeEvents"), "lifeEvents")
    add_many(ctx.get("shareableEvents"), "shareableEvents")
    add_many(ctx.get("activeThreads"), "activeThreads")
    view = ctx.get("shenzhouView") or {}
    if isinstance(view, dict):
        add_many(view.get("mentionableEvents"), "view.mentionableEvents")
        add_many(view.get("lifeEvents"), "view.lifeEvents")
        add_many(view.get("shareableEvents"), "view.shareableEvents")
        add_many(view.get("activeThreads"), "view.activeThreads")
    return out


def _event_text(event: dict[str, Any]) -> str:
    fields: list[str] = []
    for k in (
        "title",
        "description",
        "summary",
        "nextStep",
        "action",
        "category",
        "type",
        "owner",
        "assignee",
        "assigneeName",
        "participants",
        "labels",
        "note",
    ):
        v = event.get(k)
        if isinstance(v, str):
            fields.append(v)
        elif isinstance(v, list):
            fields.extend(str(x) for x in v if x)
        elif isinstance(v, dict):
            fields.extend(f"{a}:{b}" for a, b in v.items())
    return " | ".join(fields).strip()


def _slug_variants() -> set[str]:
    s = get_settings()
    vals = {
        (s.shenzhou_user_entity_slug or "").strip().lower(),
        (s.shenzhou_user_display_name or "").strip().lower(),
        "dai-jinxin",
        "戴金鑫",
    }
    return {v for v in vals if v}


def _event_related_to_user(event: dict[str, Any], text: str) -> bool:
    keys = _slug_variants()
    low = text.lower()
    if any(k in low for k in keys):
        return True
    for k in (
        "userEntitySlug",
        "userSlug",
        "targetUserSlug",
        "ownerSlug",
        "assigneeSlug",
        "participants",
        "owners",
        "assignees",
        "relatedUsers",
        "target",
        "owner",
        "assignee",
        "npc",
    ):
        v = event.get(k)
        if isinstance(v, str):
            if v.strip().lower() in keys:
                return True
            if any(x in v.strip().lower() for x in keys):
                return True
        elif isinstance(v, list):
            for item in v:
                item_s = str(item).strip().lower()
                if item_s in keys or any(x in item_s for x in keys):
                    return True
        elif isinstance(v, dict):
            for vv in v.values():
                s = str(vv).strip().lower()
                if s in keys or any(x in s for x in keys):
                    return True
    return False


def _event_when(event: dict[str, Any], *, tz: ZoneInfo) -> datetime | None:
    for k in _WINDOW_KEYS:
        dt = _parse_time(event.get(k), tz=tz)
        if dt is not None:
            return dt
    d = _parse_time(event.get("date"), tz=tz)
    if d is not None:
        return d
    return None


def _event_intent(text: str) -> str | None:
    low = text.lower()
    for intent, keys in _INTENT_RULES:
        if any(k in low for k in keys):
            return intent
    return None


def _event_uid(event: dict[str, Any]) -> str:
    raw = str(event.get("id") or "").strip()
    if raw:
        return raw
    t = "|".join(
        str(event.get(k) or "")
        for k in ("title", "summary", "description", "nextStep", "date", "scheduledAt", "_source")
    )
    return hashlib.sha1(t.encode("utf-8")).hexdigest()[:16]


def _is_quiet_hour(hour: int, *, start: int, end: int) -> bool:
    if start == end:
        return False
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def _format_message(event: dict[str, Any], *, intent: str, when: datetime | None) -> str:
    title = str(event.get("title") or "今天这件事").strip() or "今天这件事"
    next_step = str(event.get("nextStep") or "").strip()
    when_text = f"{when.strftime('%H:%M')}左右" if when is not None else "今天"
    if intent == "invite_collab":
        base = f"{when_text}关于「{title}」这个点到了，你这会儿有空一起推进吗？"
    elif intent == "message_user":
        base = f"{when_text}我想跟你同步一下「{title}」，方便聊两分钟吗？"
    else:
        base = f"{when_text}「{title}」到了跟进窗口，你现在方便同步下进度吗？"
    if next_step:
        base += f" 我这边建议下一步先做：{next_step}。"
    return base


def _resolve_channels() -> list[str]:
    raw = (get_settings().shenzhou_proactive_channels or "").strip()
    if not raw:
        return ["in_app"]
    out: list[str] = []
    for part in raw.split(","):
        key = part.strip().lower()
        if key and key not in out:
            out.append(key)
    return out or ["in_app"]


def _send_in_app(message: str, event: dict[str, Any]) -> tuple[bool, str]:
    if _IN_APP_SENDER is None:
        return False, "in_app sender unavailable"
    settings = get_settings()
    session_id = (settings.shenzhou_proactive_session_id or "").strip() or settings.shenzhou_default_session_id
    if not session_id:
        return False, "missing session_id"
    try:
        ok = bool(_IN_APP_SENDER(session_id, message, event))
        return ok, "ok" if ok else "callback returned false"
    except Exception as exc:
        return False, f"in_app error: {type(exc).__name__}"


def _send_telegram(message: str) -> tuple[bool, str]:
    settings = get_settings()
    token = settings.telegram_bot_token.strip()
    chat_id = settings.shenzhou_proactive_telegram_chat_id.strip()
    if not token or not chat_id:
        return False, "telegram not configured"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "disable_web_page_preview": True}
    req = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=10.0) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        data = json.loads(raw) if raw.strip() else {}
        ok = bool(data.get("ok"))
        return ok, "ok" if ok else f"telegram rejected: {raw[:200]}"
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return False, f"telegram http {exc.code}: {detail[:160]}"
    except URLError as exc:
        return False, f"telegram unreachable: {exc}"
    except Exception as exc:
        return False, f"telegram error: {type(exc).__name__}"


def _send_webhook(message: str, event: dict[str, Any]) -> tuple[bool, str]:
    url = get_settings().shenzhou_proactive_webhook_url.strip()
    if not url:
        return False, "webhook not configured"
    payload = {
        "type": "shenzhou_proactive_message",
        "message": message,
        "event": event,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
    req = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=10.0) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            status = getattr(resp, "status", 200)
        if 200 <= int(status) < 300:
            return True, "ok"
        return False, f"webhook status {status}: {body[:120]}"
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return False, f"webhook http {exc.code}: {detail[:160]}"
    except URLError as exc:
        return False, f"webhook unreachable: {exc}"
    except Exception as exc:
        return False, f"webhook error: {type(exc).__name__}"


def _pick_event(
    ctx: dict[str, Any],
    *,
    now_local: datetime,
    state: dict[str, Any],
    force: bool,
) -> tuple[dict[str, Any], str, datetime | None, str, bool] | None:
    settings = get_settings()
    lead = timedelta(minutes=int(settings.shenzhou_proactive_lead_minutes))
    lag = timedelta(minutes=int(settings.shenzhou_proactive_lag_minutes))
    event_last_sent: dict[str, str] = dict(state.get("event_last_sent") or {})
    sent_log_keys: set[str] = set(state.get("sent_log_keys") or [])
    cooldown = timedelta(minutes=int(settings.shenzhou_proactive_event_cooldown_minutes))
    hits: list[tuple[int, float, int, dict[str, Any], str, datetime | None, str, bool]] = []

    for event in _event_candidates(ctx):
        text = _event_text(event)
        user_related = _event_related_to_user(event, text)
        if not user_related and not force:
            continue
        intent = _event_intent(text) or "progress_check"
        uid = _event_uid(event)
        when = _event_when(event, tz=now_local.tzinfo or _tz())
        if when is None and user_related:
            when = now_local
        if when is None and not force:
            continue
        if when is not None and not force and not (when - lead <= now_local <= when + lag):
            continue
        last_raw = event_last_sent.get(uid, "")
        last_sent = _parse_time(last_raw, tz=now_local.tzinfo or _tz()) if last_raw else None
        if last_sent is not None and not force and now_local - last_sent < cooldown:
            continue
        log_key = f"{now_local.date().isoformat()}|{uid}|{intent}"
        if log_key in sent_log_keys and not force:
            continue
        importance = 0
        try:
            importance = int(float(event.get("importance") or event.get("priority") or 0))
        except Exception:
            importance = 0
        related_score = 1 if user_related else 0
        delta_seconds = abs((now_local - when).total_seconds()) if when is not None else 0.0
        hits.append((related_score, importance, -delta_seconds, event, intent, when, uid, user_related))

    if not hits:
        return None
    hits.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    _, _, _, event, intent, when, uid, user_related = hits[0]
    return event, intent, when, uid, user_related


def run_proactive_outreach(
    *,
    now: datetime | None = None,
    force: bool = False,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.shenzhou_integration_enabled:
        return {"ok": False, "status": "disabled_integration"}
    if not settings.shenzhou_proactive_message_enabled and not force:
        return {"ok": False, "status": "disabled"}

    tz = _tz()
    now_local = (now or datetime.now(tz)).astimezone(tz)
    state = _load_state()
    last_run = _parse_time(state.get("last_run_at"), tz=tz)
    interval = timedelta(minutes=int(settings.shenzhou_proactive_check_interval_minutes))
    if last_run is not None and not force and now_local - last_run < interval:
        return {"ok": True, "status": "skipped_interval"}
    if _is_quiet_hour(
        now_local.hour,
        start=int(settings.shenzhou_proactive_quiet_start_hour),
        end=int(settings.shenzhou_proactive_quiet_end_hour),
    ) and not force:
        return {"ok": True, "status": "skipped_quiet_hours"}

    daily_key = now_local.date().isoformat()
    daily_counts: dict[str, int] = dict(state.get("daily_counts") or {})

    ctx = context or _load_today_context(now_local.date())
    if ctx is None:
        return {"ok": False, "status": "no_context"}

    picked = _pick_event(ctx, now_local=now_local, state=state, force=force)
    if picked is None:
        state["last_run_at"] = now_local.isoformat()
        _save_state(state)
        return {"ok": True, "status": "no_candidate"}

    event, intent, when, uid, user_related = picked
    if (
        not force
        and not user_related
        and daily_counts.get(daily_key, 0) >= int(settings.shenzhou_proactive_daily_max)
    ):
        return {"ok": True, "status": "skipped_daily_quota"}
    message = _format_message(event, intent=intent, when=when)
    channels = _resolve_channels()
    deliveries: list[dict[str, Any]] = []
    for ch in channels:
        if ch == "in_app":
            ok, detail = _send_in_app(message, event)
        elif ch == "telegram":
            ok, detail = _send_telegram(message)
        elif ch == "webhook":
            ok, detail = _send_webhook(message, event)
        else:
            ok, detail = False, f"unsupported channel: {ch}"
        deliveries.append({"channel": ch, "ok": ok, "detail": detail})

    delivered = any(d.get("ok") for d in deliveries)
    state["last_run_at"] = now_local.isoformat()
    if delivered:
        daily_counts[daily_key] = int(daily_counts.get(daily_key, 0)) + 1
        state["daily_counts"] = daily_counts
        event_last_sent = dict(state.get("event_last_sent") or {})
        event_last_sent[uid] = now_local.isoformat()
        state["event_last_sent"] = event_last_sent
        sent_log_keys = list(dict.fromkeys(list(state.get("sent_log_keys") or []) + [f"{daily_key}|{uid}|{intent}"]))
        state["sent_log_keys"] = sent_log_keys[-2000:]
    _save_state(state)
    _append_log(
        {
            "at": now_local.isoformat(),
            "delivered": delivered,
            "intent": intent,
            "event_uid": uid,
            "event_title": event.get("title") or "",
            "event_when": when.isoformat() if when else "",
            "user_related": user_related,
            "channels": deliveries,
            "message": message,
        }
    )
    return {
        "ok": delivered,
        "status": "sent" if delivered else "channel_failed",
        "intent": intent,
        "event_uid": uid,
        "event_title": event.get("title") or "",
        "event_when": when.isoformat() if when else None,
        "user_related": user_related,
        "message": message,
        "deliveries": deliveries,
    }


def proactive_status() -> dict[str, Any]:
    s = get_settings()
    return {
        "enabled": s.shenzhou_proactive_message_enabled,
        "channels": _resolve_channels(),
        "daily_max": s.shenzhou_proactive_daily_max,
        "cooldown_minutes": s.shenzhou_proactive_event_cooldown_minutes,
        "lead_minutes": s.shenzhou_proactive_lead_minutes,
        "lag_minutes": s.shenzhou_proactive_lag_minutes,
        "quiet_hours": {
            "start_hour": s.shenzhou_proactive_quiet_start_hour,
            "end_hour": s.shenzhou_proactive_quiet_end_hour,
        },
        "state": _load_state(),
    }
