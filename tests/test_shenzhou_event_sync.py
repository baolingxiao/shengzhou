from __future__ import annotations

import json
import tempfile
from datetime import date, timedelta
from pathlib import Path

from neuralpal.config.settings import get_settings
from neuralpal.shenzhou.event_sync import build_event_sync_digest


def _write_ctx(cache_dir: Path, day: date, *, titles: list[str]) -> None:
    payload = {
        "date": day.isoformat(),
        "lifeEvents": [{"id": f"id-{day}-{i}", "title": t, "summary": t} for i, t in enumerate(titles)],
        "activeThreads": [],
        "shenzhouView": {"mentionableEvents": []},
    }
    (cache_dir / f"life_context_{day.isoformat()}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_build_event_sync_digest_detects_new_and_resolved(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        cache_dir = Path(td)
        monkeypatch.setenv("SHENZHOU_CACHE_DIR", str(cache_dir))
        get_settings.cache_clear()

        day = date(2026, 6, 30)
        _write_ctx(cache_dir, day - timedelta(days=1), titles=["预算审核", "模型采购"])
        _write_ctx(cache_dir, day, titles=["预算审核", "发布演练"])

        digest = build_event_sync_digest(
            day,
            messages=[
                {"role": "user", "content": "预算审核这条我今天已经完成了"},
                {"role": "assistant", "content": "收到"},
                {"role": "user", "content": "我新建了一个发布回归新任务"},
            ],
        )
        assert digest["new_event_count"] >= 1
        assert digest["resolved_event_count"] >= 1
        assert digest["chat_done_signals"]
        assert digest["chat_new_signals"]
        assert "事件同步摘要" in digest["summary_text"]

        get_settings.cache_clear()
