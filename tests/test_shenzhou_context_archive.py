from __future__ import annotations

import json
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

from neuralpal.config.settings import get_settings
from neuralpal.shenzhou.context_archive import run_context_archive


def _write_daily(cache_dir: Path, d: date) -> None:
    payload = {
        "date": d.isoformat(),
        "lifeEvents": [
            {
                "id": f"evt-{d.isoformat()}",
                "title": f"{d.isoformat()} 事件",
                "summary": "推进测试与发布",
                "category": "work",
                "importance": 80,
            }
        ],
        "activeThreads": [
            {
                "id": f"thr-{d.isoformat()}",
                "title": "发布主线",
                "summary": "持续推进版本发布",
                "nextStep": "验证线上指标",
            }
        ],
        "shenzhouView": {
            "mentionableEvents": [
                {"id": f"m-{d.isoformat()}", "title": "提醒同步进度", "description": "询问进度"}
            ]
        },
    }
    (cache_dir / f"life_context_{d.isoformat()}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_context_archive_generates_rollups_and_compresses(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        cache_dir = Path(td)
        monkeypatch.setenv("SHENZHOU_CACHE_DIR", str(cache_dir))
        monkeypatch.setenv("SHENZHOU_CONTEXT_ARCHIVE_ENABLED", "true")
        monkeypatch.setenv("SHENZHOU_CONTEXT_KEEP_RAW_DAYS", "7")
        monkeypatch.setenv("SHENZHOU_TIMEZONE", "Asia/Shanghai")
        get_settings.cache_clear()

        now = datetime.fromisoformat("2026-07-10T10:00:00+08:00")
        base = now.date()
        for i in range(45):
            _write_daily(cache_dir, base - timedelta(days=i))

        result = run_context_archive(now=now, backfill=True)
        assert result["ok"] is True

        # 老日文件应进入 gzip 分层
        old_day = base - timedelta(days=20)
        gz = cache_dir / "archive" / "raw" / f"{old_day.year:04d}" / f"life_context_{old_day.isoformat()}.json.gz"
        assert gz.is_file()

        # 周/月/年压缩摘要应生成
        weekly_dir = cache_dir / "archive" / "weekly"
        monthly_dir = cache_dir / "archive" / "monthly"
        yearly_dir = cache_dir / "archive" / "yearly"
        assert any(weekly_dir.glob("weekly_context_*.md"))
        assert any(monthly_dir.glob("monthly_context_*.md"))
        assert any(yearly_dir.glob("yearly_context_*.md"))

        get_settings.cache_clear()
