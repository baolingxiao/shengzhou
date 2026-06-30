from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path

from neuralpal.config.settings import get_settings
from neuralpal.shenzhou.proactive import register_in_app_sender, run_proactive_outreach


def _write_ctx(cache_dir: Path, day: str) -> None:
    payload = {
        "date": day,
        "lifeEvents": [
            {
                "id": "evt-progress-1",
                "title": "项目联调进度同步",
                "summary": "需要和用户同步进度并确认下一步",
                "nextStep": "一起完成回归测试",
                "scheduledAt": f"{day}T10:30:00+08:00",
                "importance": 90,
                "userEntitySlug": "dai-jinxin",
            }
        ],
        "activeThreads": [],
        "shareableEvents": [],
        "shenzhouView": {"mentionableEvents": []},
    }
    (cache_dir / f"life_context_{day}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_proactive_outreach_sends_in_app_and_respects_cooldown(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        cache_dir = Path(td)
        monkeypatch.setenv("SHENZHOU_CACHE_DIR", str(cache_dir))
        monkeypatch.setenv("SHENZHOU_PROACTIVE_MESSAGE_ENABLED", "true")
        monkeypatch.setenv("SHENZHOU_PROACTIVE_CHANNELS", "in_app")
        monkeypatch.setenv("SHENZHOU_PROACTIVE_CHECK_INTERVAL_MINUTES", "1")
        monkeypatch.setenv("SHENZHOU_PROACTIVE_EVENT_COOLDOWN_MINUTES", "240")
        monkeypatch.setenv("SHENZHOU_PROACTIVE_DAILY_MAX", "5")
        monkeypatch.setenv("SHENZHOU_PROACTIVE_QUIET_START_HOUR", "23")
        monkeypatch.setenv("SHENZHOU_PROACTIVE_QUIET_END_HOUR", "7")
        monkeypatch.setenv("SHENZHOU_TIMEZONE", "Asia/Shanghai")
        get_settings.cache_clear()

        day = "2026-06-30"
        _write_ctx(cache_dir, day)
        calls: list[tuple[str, str]] = []

        def sender(session_id: str, text: str, event: dict[str, object]) -> bool:
            del event
            calls.append((session_id, text))
            return True

        register_in_app_sender(sender)

        now = datetime.fromisoformat("2026-06-30T10:20:00+08:00")
        result1 = run_proactive_outreach(now=now)
        assert result1["status"] == "sent"
        assert calls, "in_app sender should be called"

        # 同一事件冷却期内不应再次发送
        result2 = run_proactive_outreach(now=now.replace(minute=25), force=False)
        assert result2["status"] in {"skipped_interval", "no_candidate"}

        get_settings.cache_clear()


def test_proactive_user_related_event_without_intent_keywords(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        cache_dir = Path(td)
        monkeypatch.setenv("SHENZHOU_CACHE_DIR", str(cache_dir))
        monkeypatch.setenv("SHENZHOU_PROACTIVE_MESSAGE_ENABLED", "true")
        monkeypatch.setenv("SHENZHOU_PROACTIVE_CHANNELS", "in_app")
        monkeypatch.setenv("SHENZHOU_PROACTIVE_CHECK_INTERVAL_MINUTES", "1")
        monkeypatch.setenv("SHENZHOU_PROACTIVE_EVENT_COOLDOWN_MINUTES", "60")
        monkeypatch.setenv("SHENZHOU_PROACTIVE_DAILY_MAX", "1")
        monkeypatch.setenv("SHENZHOU_TIMEZONE", "Asia/Shanghai")
        get_settings.cache_clear()

        day = "2026-06-30"
        payload = {
            "date": day,
            "lifeEvents": [
                {
                    "id": "evt-user-only",
                    "title": "董事会材料确认",
                    "summary": "晚上确认材料版本",
                    "scheduledAt": f"{day}T20:00:00+08:00",
                    "importance": 88,
                    "participants": ["dai-jinxin", "shen-zhou"],
                }
            ],
        }
        (cache_dir / f"life_context_{day}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        calls: list[str] = []

        def sender(session_id: str, text: str, event: dict[str, object]) -> bool:
            del session_id, event
            calls.append(text)
            return True

        register_in_app_sender(sender)
        now = datetime.fromisoformat("2026-06-30T19:20:00+08:00")
        result = run_proactive_outreach(now=now)
        assert result["status"] == "sent"
        assert result["user_related"] is True
        assert calls

        get_settings.cache_clear()
