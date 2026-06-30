from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from neuralpal.config.settings import get_settings
from neuralpal.memory.memory_maintenance import MemoryMaintenanceService
from neuralpal.memory.palace_layout import ensure_palace_layout, path_medium


class _FakeLTSuccess:
    def index_existing_memory_file(self, **_: object) -> str:
        return "vid-ok"


class _FakeLTFail:
    def index_existing_memory_file(self, **_: object) -> str | None:
        return None


class _FailWriteService(MemoryMaintenanceService):
    def _atomic_write_text(self, path: Path, content: str) -> None:  # type: ignore[override]
        if path.name.startswith("daily_summary_"):
            raise OSError("simulated write failure")
        super()._atomic_write_text(path, content)


class MemoryMaintenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "knowledge_palace"
        os.environ["NEURALPAL_KNOWLEDGE_PALACE"] = str(self.root)
        os.environ["NEURALPAL_MEMORY_UNIFY_OBSIDIAN"] = "false"
        os.environ["COMPANION_LIFE_ENABLED"] = "false"
        os.environ.pop("NEURALPAL_OBSIDIAN_VAULT_PATH", None)
        get_settings.cache_clear()
        ensure_palace_layout(self.root)

    def tearDown(self) -> None:
        os.environ.pop("NEURALPAL_KNOWLEDGE_PALACE", None)
        os.environ.pop("NEURALPAL_MEMORY_UNIFY_OBSIDIAN", None)
        os.environ.pop("COMPANION_LIFE_ENABLED", None)
        get_settings.cache_clear()

    def _mk_short_file(self, d: date, name: str = "default.md", content: str = "用户：我要推进项目") -> Path:
        p = self.root / "01_短期记忆" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"# 短期工作记忆\n\n{content}\n助手：收到\n", encoding="utf-8")
        ts = datetime(d.year, d.month, d.day, 12, 0, 0).timestamp()
        os.utime(p, (ts, ts))
        return p

    def test_daily_no_activity_skip(self) -> None:
        svc = MemoryMaintenanceService(root=self.root, long_term_engine=_FakeLTSuccess())
        d = date.today() - timedelta(days=1)
        r = svc.generate_daily_summary(d)
        self.assertEqual(r.status, "skipped_no_activity")
        self.assertFalse((self.root / "02_中期记忆" / f"daily_summary_{d.isoformat()}.md").exists())

    def test_daily_with_activity_generate_to_middle(self) -> None:
        d = date.today() - timedelta(days=1)
        self._mk_short_file(d)
        svc = MemoryMaintenanceService(root=self.root, long_term_engine=_FakeLTSuccess())
        r = svc.generate_daily_summary(d)
        self.assertTrue(r.ok)
        self.assertEqual(r.status, "generated")
        self.assertTrue((self.root / "02_中期记忆" / f"daily_summary_{d.isoformat()}.md").exists())

    def test_daily_existing_no_duplicate(self) -> None:
        d = date.today() - timedelta(days=1)
        out = self.root / "02_中期记忆" / f"daily_summary_{d.isoformat()}.md"
        out.write_text("already", encoding="utf-8")
        svc = MemoryMaintenanceService(root=self.root, long_term_engine=_FakeLTSuccess())
        r = svc.generate_daily_summary(d, force=False)
        self.assertEqual(r.status, "skipped_exists")

    def test_daily_fail_no_short_cleanup(self) -> None:
        d = date.today() - timedelta(days=1)
        sf = self._mk_short_file(d, "keep.md")
        svc = _FailWriteService(root=self.root, long_term_engine=_FakeLTSuccess())
        r = svc.generate_daily_summary(d)
        self.assertFalse(r.ok)
        c = svc.cleanup_short_term_for_date(d)
        self.assertEqual(c.status, "skipped_summary_not_ready")
        self.assertTrue(sf.exists())

    def test_monthly_success_write_long(self) -> None:
        mk = (date.today() - timedelta(days=31)).strftime("%Y-%m")
        dpath = self.root / "02_中期记忆" / f"daily_summary_{mk}-02.md"
        dpath.write_text("# 每日记忆总结\n\n- 用户：喜欢短句", encoding="utf-8")
        svc = MemoryMaintenanceService(root=self.root, long_term_engine=_FakeLTSuccess())
        r = svc.generate_monthly_summary(mk)
        self.assertTrue(r.ok)
        self.assertEqual(r.status, "generated")
        self.assertTrue((self.root / "03_长期记忆" / f"monthly_summary_{mk}.md").exists())

    def test_monthly_cleanup_requires_chroma_success(self) -> None:
        mk = (date.today() - timedelta(days=31)).strftime("%Y-%m")
        dfile = self.root / "02_中期记忆" / f"daily_summary_{mk}-03.md"
        dfile.write_text("daily", encoding="utf-8")
        svc = MemoryMaintenanceService(root=self.root, long_term_engine=_FakeLTFail())
        r = svc.generate_monthly_summary(mk)
        self.assertEqual(r.status, "failed_chroma")
        c = svc.cleanup_middle_term_for_month(mk)
        self.assertEqual(c.status, "skipped_monthly_not_ready")
        self.assertTrue(dfile.exists())

    def test_weekly_success_write_long_and_cleanup_middle(self) -> None:
        d = date(2026, 5, 26)  # ISO week 2026-W22
        wk = "2026-W22"
        p = self.root / "02_中期记忆" / f"daily_summary_{d.isoformat()}.md"
        p.write_text("# 每日记忆总结\n\n- 用户：推进迭代", encoding="utf-8")
        svc = MemoryMaintenanceService(root=self.root, long_term_engine=_FakeLTSuccess())
        r = svc.generate_weekly_summary(wk)
        self.assertTrue(r.ok)
        self.assertEqual(r.status, "generated")
        self.assertTrue((self.root / "03_长期记忆" / f"weekly_summary_{wk}.md").exists())
        c = svc.cleanup_middle_term_for_week(wk)
        self.assertEqual(c.status, "archived")
        self.assertFalse(p.exists())
        self.assertTrue((self.root / "02_中期记忆" / "_archive" / "weekly" / wk / p.name).exists())

    def test_startup_catchup_generates_yesterday_daily(self) -> None:
        now = datetime.now()
        y = (now.date() - timedelta(days=1))
        self._mk_short_file(y)
        svc = MemoryMaintenanceService(root=self.root, long_term_engine=_FakeLTSuccess())
        svc.run_startup_catchup(now=now)
        self.assertTrue((self.root / "02_中期记忆" / f"daily_summary_{y.isoformat()}.md").exists())

    def test_startup_catchup_generates_previous_monthly(self) -> None:
        now = datetime(2026, 5, 1, 10, 0, 0)
        mk = "2026-04"
        p = path_medium(self.root) / "daily_summary_2026-04-29.md"
        p.write_text("用户：推进版本", encoding="utf-8")
        svc = MemoryMaintenanceService(root=self.root, long_term_engine=_FakeLTSuccess())
        svc.run_startup_catchup(now=now)
        self.assertTrue((self.root / "03_长期记忆" / f"monthly_summary_{mk}.md").exists())

    def test_dry_run_does_not_move_or_delete(self) -> None:
        d = date.today() - timedelta(days=1)
        sf = self._mk_short_file(d, "dry.md")
        svc = MemoryMaintenanceService(root=self.root, long_term_engine=_FakeLTSuccess())
        svc.run_daily_maintenance(now=datetime.now(), dry_run=True)
        self.assertTrue(sf.exists())
        self.assertFalse((self.root / "01_短期记忆" / "_archive" / d.isoformat()).exists())

    def test_daily_summary_triggers_companion_life_once(self) -> None:
        d = date.today() - timedelta(days=1)
        self._mk_short_file(d, "default.md")
        svc = MemoryMaintenanceService(root=self.root, long_term_engine=_FakeLTSuccess())
        with patch(
            "neuralpal.companion_life.bridge.resolve_companion_instance_id_for_session",
            return_value="34750dfcf3be",
        ) as mock_resolve:
            with patch(
                "neuralpal.companion_life.scheduler.run_daily_for_user",
            ) as mock_cl:
                svc.generate_daily_summary(d, force=True)
                mock_resolve.assert_called()
                mock_cl.assert_called_once_with("default", companion_instance_id="34750dfcf3be")


if __name__ == "__main__":
    unittest.main()
