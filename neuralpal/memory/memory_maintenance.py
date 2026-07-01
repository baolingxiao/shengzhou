from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from neuralpal.memory.palace_layout import (
    path_long,
    path_medium,
    path_short,
    publish_palace_file,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MaintenanceResult:
    ok: bool
    status: str
    path: Optional[Path] = None
    message: str = ""


class MemoryMaintenanceService:
    """日结/月结/清理维护服务（不打断 chat_turn 主链）。"""

    _scheduler_lock = threading.Lock()
    _scheduler_thread: Optional[threading.Thread] = None
    _stop_event = threading.Event()

    def __init__(
        self,
        *,
        root: Path,
        long_term_engine: Any | None = None,
        verbose: bool = False,
    ) -> None:
        self._root = Path(root).resolve()
        self._short_dir = path_short(self._root)
        self._middle_dir = path_medium(self._root)
        self._long_dir = path_long(self._root)
        self._state_path = self._root / ".memory_maintenance_state.json"
        self._lt = long_term_engine
        self.verbose = verbose

    # ---------- state ----------
    def _default_state(self) -> dict[str, Any]:
        return {
            "daily_generated": [],
            "short_term_archived": [],
            "weekly_generated": [],
            "weekly_chroma_indexed": [],
            "middle_term_weekly_archived": [],
            "monthly_generated": [],
            "monthly_chroma_indexed": [],
            "middle_term_archived": [],
            "yearly_generated": [],
            "yearly_chroma_indexed": [],
            "long_term_yearly_archived": [],
            "last_daily_maintenance_date": "",
            "last_weekly_maintenance_week": "",
            "last_monthly_maintenance_month": "",
            "last_yearly_maintenance_year": "",
        }

    def _load_state(self) -> dict[str, Any]:
        if not self._state_path.is_file():
            return self._default_state()
        try:
            data = json.loads(self._state_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return self._default_state()
            out = self._default_state()
            out.update(data)
            return out
        except Exception as exc:
            logger.warning("memory maintenance state load failed: %s", exc)
            return self._default_state()

    def _atomic_write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)

    def _save_state(self, state: dict[str, Any], *, dry_run: bool) -> None:
        if dry_run:
            return
        content = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)
        self._atomic_write_text(self._state_path, content)
        publish_palace_file(self._state_path)

    # ---------- helpers ----------
    def _date_key(self, d: date) -> str:
        return d.isoformat()

    def _month_key(self, month: str | date) -> str:
        if isinstance(month, date):
            return month.strftime("%Y-%m")
        return month

    def _week_key(self, week: str | date) -> str:
        if isinstance(week, date):
            iso = week.isocalendar()
            return f"{iso.year}-W{iso.week:02d}"
        return week

    def _daily_summary_path(self, d: date) -> Path:
        return self._middle_dir / f"daily_summary_{self._date_key(d)}.md"

    def _weekly_summary_path(self, week_key: str) -> Path:
        return self._long_dir / f"weekly_summary_{week_key}.md"

    def _monthly_summary_path(self, month_key: str) -> Path:
        return self._long_dir / f"monthly_summary_{month_key}.md"

    def _yearly_summary_path(self, year_key: str) -> Path:
        return self._long_dir / f"yearly_summary_{year_key}.md"

    def _iter_short_files_for_date(self, d: date) -> list[Path]:
        if not self._short_dir.is_dir():
            return []
        out: list[Path] = []
        for p in self._short_dir.glob("*.md"):
            if not p.is_file():
                continue
            try:
                mdt = datetime.fromtimestamp(p.stat().st_mtime).date()
            except OSError:
                continue
            if mdt == d:
                out.append(p)
        return sorted(out)

    def _extract_sections(self, texts: list[str], *, monthly: bool = False) -> dict[str, list[str]]:
        joined = "\n".join(texts)
        lines = [ln.strip() for ln in joined.splitlines() if ln.strip()]
        users = [ln[3:].strip() for ln in lines if ln.startswith("用户：")]
        assistants = [ln[3:].strip() for ln in lines if ln.startswith("助手：")]

        def pick(src: list[str], n: int) -> list[str]:
            seen: set[str] = set()
            out: list[str] = []
            for s in src:
                t = s[:90].strip()
                if not t or t in seen:
                    continue
                out.append(t)
                seen.add(t)
                if len(out) >= n:
                    break
            return out

        topics = pick(users + assistants, 6)
        needs = pick([u for u in users if any(k in u for k in ("要", "希望", "请", "需要", "想"))], 5)
        prefs = pick([u for u in users if any(k in u for k in ("喜欢", "偏好", "习惯", "不喜欢"))], 5)
        project = pick([u for u in users + assistants if any(k in u for k in ("项目", "版本", "测试", "发布", "改"))], 5)
        follow = pick([u for u in users if any(k in u for k in ("明天", "下次", "待", "跟进", "之后"))], 5)
        temp = pick([u for u in users if any(k in u for k in ("今天", "刚才", "临时", "随口", "吐槽"))], 5)

        if monthly:
            return {
                "stable_prefs": prefs or ["-"],
                "project_progress": project or ["-"],
                "long_term_goal_changes": follow or ["-"],
                "important_entities": topics or ["-"],
                "facts_to_remember": needs or ["-"],
                "not_recommended": temp or ["-"],
            }
        return {
            "topics": topics or ["-"],
            "needs": needs or ["-"],
            "prefs": prefs or ["-"],
            "project": project or ["-"],
            "follow": follow or ["-"],
            "temp": temp or ["-"],
        }

    def _render_daily_summary(self, d: date, texts: list[str]) -> str:
        sec = self._extract_sections(texts, monthly=False)
        return (
            f"# 每日记忆总结 {d.isoformat()}\n\n"
            "## 今日主要对话主题\n"
            + "\n".join(f"- {x}" for x in sec["topics"])
            + "\n\n## 用户明确表达的需求\n"
            + "\n".join(f"- {x}" for x in sec["needs"])
            + "\n\n## 用户偏好/习惯变化\n"
            + "\n".join(f"- {x}" for x in sec["prefs"])
            + "\n\n## 项目进展\n"
            + "\n".join(f"- {x}" for x in sec["project"])
            + "\n\n## 待跟进事项\n"
            + "\n".join(f"- {x}" for x in sec["follow"])
            + "\n\n## 不应写入长期记忆的临时内容\n"
            + "\n".join(f"- {x}" for x in sec["temp"])
            + "\n"
        )

    def _render_monthly_summary(self, month_key: str, texts: list[str]) -> str:
        sec = self._extract_sections(texts, monthly=True)
        return (
            f"# 月度记忆总结 {month_key}\n\n"
            "## 本月长期稳定偏好\n"
            + "\n".join(f"- {x}" for x in sec["stable_prefs"])
            + "\n\n## 本月重要项目进展\n"
            + "\n".join(f"- {x}" for x in sec["project_progress"])
            + "\n\n## 用户长期目标变化\n"
            + "\n".join(f"- {x}" for x in sec["long_term_goal_changes"])
            + "\n\n## 重要人物/项目/系统信息\n"
            + "\n".join(f"- {x}" for x in sec["important_entities"])
            + "\n\n## 需要未来持续记住的事实\n"
            + "\n".join(f"- {x}" for x in sec["facts_to_remember"])
            + "\n\n## 不建议长期保存的短期情绪或临时事件\n"
            + "\n".join(f"- {x}" for x in sec["not_recommended"])
            + "\n"
        )

    def _render_weekly_summary(self, week_key: str, texts: list[str]) -> str:
        sec = self._extract_sections(texts, monthly=True)
        return (
            f"# 每周记忆总结 {week_key}\n\n"
            "## 本周长期稳定偏好\n"
            + "\n".join(f"- {x}" for x in sec["stable_prefs"])
            + "\n\n## 本周重要项目进展\n"
            + "\n".join(f"- {x}" for x in sec["project_progress"])
            + "\n\n## 用户长期目标变化\n"
            + "\n".join(f"- {x}" for x in sec["long_term_goal_changes"])
            + "\n\n## 重要人物/项目/系统信息\n"
            + "\n".join(f"- {x}" for x in sec["important_entities"])
            + "\n\n## 需要未来持续记住的事实\n"
            + "\n".join(f"- {x}" for x in sec["facts_to_remember"])
            + "\n\n## 不建议长期保存的短期情绪或临时事件\n"
            + "\n".join(f"- {x}" for x in sec["not_recommended"])
            + "\n"
        )

    def _render_yearly_summary(self, year_key: str, texts: list[str]) -> str:
        sec = self._extract_sections(texts, monthly=True)
        return (
            f"# 年度记忆总结 {year_key}\n\n"
            "## 年度稳定偏好\n"
            + "\n".join(f"- {x}" for x in sec["stable_prefs"])
            + "\n\n## 年度项目主线进展\n"
            + "\n".join(f"- {x}" for x in sec["project_progress"])
            + "\n\n## 长期目标演化\n"
            + "\n".join(f"- {x}" for x in sec["long_term_goal_changes"])
            + "\n\n## 年度关键实体与关系\n"
            + "\n".join(f"- {x}" for x in sec["important_entities"])
            + "\n\n## 需要跨年保留的事实\n"
            + "\n".join(f"- {x}" for x in sec["facts_to_remember"])
            + "\n\n## 应持续剔除的短时信息\n"
            + "\n".join(f"- {x}" for x in sec["not_recommended"])
            + "\n"
        )

    # ---------- daily ----------
    def has_short_term_activity(self, d: date) -> bool:
        files = self._iter_short_files_for_date(d)
        has = len(files) > 0
        logger.info("[maintenance] daily %s short-term activity=%s files=%d", d.isoformat(), has, len(files))
        return has

    def generate_daily_summary(self, d: date, *, force: bool = False, dry_run: bool = False) -> MaintenanceResult:
        state = self._load_state()
        dk = self._date_key(d)
        out = self._daily_summary_path(d)
        if out.exists() and not force:
            logger.info("[maintenance] daily %s skipped (exists)", dk)
            return MaintenanceResult(True, "skipped_exists", out)
        files = self._iter_short_files_for_date(d)
        if not files:
            logger.info("[maintenance] daily %s skipped (no activity)", dk)
            return MaintenanceResult(True, "skipped_no_activity", out)
        texts: list[str] = []
        for p in files:
            try:
                texts.append(p.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
        if not "".join(texts).strip():
            logger.info("[maintenance] daily %s skipped (empty content)", dk)
            return MaintenanceResult(True, "skipped_no_activity", out)

        body = self._render_daily_summary(d, texts)
        if not dry_run:
            try:
                self._atomic_write_text(out, body)
                publish_palace_file(out)
                if dk not in state["daily_generated"]:
                    state["daily_generated"].append(dk)
                self._save_state(state, dry_run=False)
            except Exception as exc:
                logger.exception("[maintenance] daily %s generate failed: %s", dk, exc)
                return MaintenanceResult(False, "failed_write", out, str(exc))
        logger.info("[maintenance] daily %s generated path=%s dry_run=%s", dk, out, dry_run)
        if not dry_run:
            try:
                from neuralpal.topic_radar.scheduler import run_daily_for_user

                for p in files:
                    user_id = p.stem.replace(".md", "") or "default"
                    run_daily_for_user(user_id)
            except Exception:
                logger.debug("[maintenance] topic radar hook skipped", exc_info=True)
            try:
                from neuralpal.companion_life.bridge import (
                    resolve_companion_instance_id_for_session,
                )
                from neuralpal.companion_life.scheduler import run_daily_for_user as run_companion_life

                seen_users: set[str] = set()
                for p in files:
                    user_id = p.stem.replace(".md", "") or "default"
                    if user_id in seen_users:
                        continue
                    seen_users.add(user_id)
                    companion_instance_id = resolve_companion_instance_id_for_session(
                        user_id
                    )
                    if not companion_instance_id:
                        logger.debug(
                            "[maintenance] companion_life skip user=%s (no instance)",
                            user_id,
                        )
                        continue
                    run_companion_life(
                        user_id, companion_instance_id=companion_instance_id
                    )
            except Exception:
                logger.warning("[maintenance] companion_life hook failed", exc_info=True)
        return MaintenanceResult(True, "generated", out)

    def cleanup_short_term_for_date(self, d: date, *, dry_run: bool = False) -> MaintenanceResult:
        state = self._load_state()
        dk = self._date_key(d)
        out = self._daily_summary_path(d)
        if not out.exists() or dk not in state.get("daily_generated", []):
            logger.info("[maintenance] short cleanup %s skipped (summary not ready)", dk)
            return MaintenanceResult(True, "skipped_summary_not_ready")

        files = self._iter_short_files_for_date(d)
        if not files:
            logger.info("[maintenance] short cleanup %s skipped (no files)", dk)
            return MaintenanceResult(True, "skipped_no_files")

        archive_dir = self._short_dir / "_archive" / dk
        moved = 0
        for p in files:
            dst = archive_dir / p.name
            if dry_run:
                moved += 1
                continue
            archive_dir.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                dst = archive_dir / f"{p.stem}_{int(time.time())}{p.suffix}"
            p.replace(dst)
            publish_palace_file(dst)
            moved += 1

        if not dry_run:
            if dk not in state["short_term_archived"]:
                state["short_term_archived"].append(dk)
            self._save_state(state, dry_run=False)
        logger.info("[maintenance] short cleanup %s moved=%d dry_run=%s", dk, moved, dry_run)
        return MaintenanceResult(True, "archived", archive_dir, message=f"moved={moved}")

    # ---------- monthly ----------
    def _iter_middle_daily_files_for_week(self, week_key: str) -> list[Path]:
        if not self._middle_dir.is_dir():
            return []
        out: list[Path] = []
        for p in self._middle_dir.glob("daily_summary_*.md"):
            if not p.is_file():
                continue
            stem = p.stem
            if not stem.startswith("daily_summary_"):
                continue
            dpart = stem.replace("daily_summary_", "", 1)
            try:
                dd = datetime.strptime(dpart, "%Y-%m-%d").date()
            except ValueError:
                continue
            iso = dd.isocalendar()
            k = f"{iso.year}-W{iso.week:02d}"
            if k == week_key:
                out.append(p)
        return sorted(out)

    def generate_weekly_summary(
        self,
        week: str,
        *,
        force: bool = False,
        dry_run: bool = False,
    ) -> MaintenanceResult:
        wk = self._week_key(week)
        state = self._load_state()
        out = self._weekly_summary_path(wk)

        if out.exists() and not force and wk in state.get("weekly_generated", []):
            logger.info("[maintenance] weekly %s skipped (exists)", wk)
            return MaintenanceResult(True, "skipped_exists", out)

        daily_files = self._iter_middle_daily_files_for_week(wk)
        if not daily_files:
            logger.info("[maintenance] weekly %s skipped (no daily summaries)", wk)
            return MaintenanceResult(True, "skipped_no_daily")

        texts: list[str] = []
        for p in daily_files:
            try:
                texts.append(p.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
        if not "".join(texts).strip():
            logger.info("[maintenance] weekly %s skipped (empty daily content)", wk)
            return MaintenanceResult(True, "skipped_no_daily")

        body = self._render_weekly_summary(wk, texts)
        if not dry_run:
            try:
                self._atomic_write_text(out, body)
                publish_palace_file(out)
            except Exception as exc:
                logger.exception("[maintenance] weekly %s write failed: %s", wk, exc)
                return MaintenanceResult(False, "failed_write", out, str(exc))

        chroma_ok = self._index_monthly_to_chroma(
            month_key=wk,
            text=body,
            file_path=out,
            dry_run=dry_run,
        )
        if not chroma_ok:
            logger.warning("[maintenance] weekly %s generated but chroma not indexed", wk)
            return MaintenanceResult(False, "failed_chroma", out, "weekly file exists but chroma failed")

        if not dry_run:
            if wk not in state["weekly_generated"]:
                state["weekly_generated"].append(wk)
            if wk not in state["weekly_chroma_indexed"]:
                state["weekly_chroma_indexed"].append(wk)
            self._save_state(state, dry_run=False)
        logger.info("[maintenance] weekly %s generated path=%s dry_run=%s", wk, out, dry_run)
        return MaintenanceResult(True, "generated", out)

    def cleanup_middle_term_for_week(self, week: str, *, dry_run: bool = False) -> MaintenanceResult:
        wk = self._week_key(week)
        state = self._load_state()
        out = self._weekly_summary_path(wk)
        if not out.exists() or wk not in state.get("weekly_chroma_indexed", []):
            logger.info("[maintenance] middle weekly cleanup %s skipped (weekly/chroma not ready)", wk)
            return MaintenanceResult(True, "skipped_weekly_not_ready")

        files = self._iter_middle_daily_files_for_week(wk)
        if not files:
            logger.info("[maintenance] middle weekly cleanup %s skipped (no daily files)", wk)
            return MaintenanceResult(True, "skipped_no_files")

        archive_dir = self._middle_dir / "_archive" / "weekly" / wk
        moved = 0
        for p in files:
            dst = archive_dir / p.name
            if dry_run:
                moved += 1
                continue
            archive_dir.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                dst = archive_dir / f"{p.stem}_{int(time.time())}{p.suffix}"
            p.replace(dst)
            publish_palace_file(dst)
            moved += 1

        if not dry_run:
            if wk not in state["middle_term_weekly_archived"]:
                state["middle_term_weekly_archived"].append(wk)
            self._save_state(state, dry_run=False)
        logger.info("[maintenance] middle weekly cleanup %s moved=%d dry_run=%s", wk, moved, dry_run)
        return MaintenanceResult(True, "archived", archive_dir, f"moved={moved}")

    def has_middle_term_summaries(self, month: str) -> bool:
        prefix = f"daily_summary_{month}-"
        if not self._middle_dir.is_dir():
            return False
        for p in self._middle_dir.glob(f"{prefix}*.md"):
            if p.is_file():
                return True
        return False

    def _iter_middle_daily_files_for_month(self, month: str) -> list[Path]:
        if not self._middle_dir.is_dir():
            return []
        return sorted([p for p in self._middle_dir.glob(f"daily_summary_{month}-*.md") if p.is_file()])

    def _index_monthly_to_chroma(self, *, month_key: str, text: str, file_path: Path, dry_run: bool) -> bool:
        if dry_run:
            return True
        if self._lt is None:
            logger.warning("[maintenance] monthly %s chroma skipped (lt engine missing)", month_key)
            return False
        try:
            if hasattr(self._lt, "index_existing_memory_file"):
                vid = self._lt.index_existing_memory_file(
                    text=text,
                    file_path=file_path,
                    memory_type="语义",
                    importance=8,
                )
                return bool(vid)
            # fallback: keep compatibility with older engine
            if hasattr(self._lt, "add_memory"):
                vid = self._lt.add_memory(
                    text=text,
                    subdir="03_长期记忆/项目知识",
                    memory_type="语义",
                    importance=8,
                    extra_note=f"【来源】月度总结文件：{file_path}",
                )
                return bool(vid)
        except Exception as exc:
            logger.exception("[maintenance] monthly %s chroma index failed: %s", month_key, exc)
            return False
        return False

    def generate_monthly_summary(
        self,
        month: str,
        *,
        force: bool = False,
        dry_run: bool = False,
    ) -> MaintenanceResult:
        mk = self._month_key(month)
        state = self._load_state()
        out = self._monthly_summary_path(mk)

        if out.exists() and not force and mk in state.get("monthly_generated", []):
            logger.info("[maintenance] monthly %s skipped (exists)", mk)
            return MaintenanceResult(True, "skipped_exists", out)

        daily_files = self._iter_middle_daily_files_for_month(mk)
        if not daily_files:
            logger.info("[maintenance] monthly %s skipped (no daily summaries)", mk)
            return MaintenanceResult(True, "skipped_no_daily")

        texts: list[str] = []
        for p in daily_files:
            try:
                texts.append(p.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
        if not "".join(texts).strip():
            logger.info("[maintenance] monthly %s skipped (empty daily content)", mk)
            return MaintenanceResult(True, "skipped_no_daily")

        body = self._render_monthly_summary(mk, texts)
        if not dry_run:
            try:
                self._atomic_write_text(out, body)
                publish_palace_file(out)
            except Exception as exc:
                logger.exception("[maintenance] monthly %s write failed: %s", mk, exc)
                return MaintenanceResult(False, "failed_write", out, str(exc))
        chroma_ok = self._index_monthly_to_chroma(month_key=mk, text=body, file_path=out, dry_run=dry_run)
        if not chroma_ok:
            logger.warning("[maintenance] monthly %s generated but chroma not indexed", mk)
            return MaintenanceResult(False, "failed_chroma", out, "monthly file exists but chroma failed")

        if not dry_run:
            if mk not in state["monthly_generated"]:
                state["monthly_generated"].append(mk)
            if mk not in state["monthly_chroma_indexed"]:
                state["monthly_chroma_indexed"].append(mk)
            self._save_state(state, dry_run=False)
        logger.info("[maintenance] monthly %s generated path=%s dry_run=%s", mk, out, dry_run)
        return MaintenanceResult(True, "generated", out)

    def cleanup_middle_term_for_month(self, month: str, *, dry_run: bool = False) -> MaintenanceResult:
        mk = self._month_key(month)
        state = self._load_state()
        out = self._monthly_summary_path(mk)
        if not out.exists() or mk not in state.get("monthly_chroma_indexed", []):
            logger.info("[maintenance] middle cleanup %s skipped (monthly/chroma not ready)", mk)
            return MaintenanceResult(True, "skipped_monthly_not_ready")

        files = self._iter_middle_daily_files_for_month(mk)
        if not files:
            logger.info("[maintenance] middle cleanup %s skipped (no daily files)", mk)
            return MaintenanceResult(True, "skipped_no_files")

        archive_dir = self._middle_dir / "_archive" / mk
        moved = 0
        for p in files:
            dst = archive_dir / p.name
            if dry_run:
                moved += 1
                continue
            archive_dir.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                dst = archive_dir / f"{p.stem}_{int(time.time())}{p.suffix}"
            p.replace(dst)
            publish_palace_file(dst)
            moved += 1

        if not dry_run:
            if mk not in state["middle_term_archived"]:
                state["middle_term_archived"].append(mk)
            self._save_state(state, dry_run=False)
        logger.info("[maintenance] middle cleanup %s moved=%d dry_run=%s", mk, moved, dry_run)
        return MaintenanceResult(True, "archived", archive_dir, f"moved={moved}")

    def _iter_long_monthly_files_for_year(self, year_key: str) -> list[Path]:
        if not self._long_dir.is_dir():
            return []
        return sorted([p for p in self._long_dir.glob(f"monthly_summary_{year_key}-*.md") if p.is_file()])

    def _iter_long_weekly_files_for_year(self, year_key: str) -> list[Path]:
        if not self._long_dir.is_dir():
            return []
        return sorted([p for p in self._long_dir.glob(f"weekly_summary_{year_key}-W*.md") if p.is_file()])

    def generate_yearly_summary(
        self,
        year: str,
        *,
        force: bool = False,
        dry_run: bool = False,
    ) -> MaintenanceResult:
        yk = str(year).strip()
        state = self._load_state()
        out = self._yearly_summary_path(yk)

        if out.exists() and not force and yk in state.get("yearly_generated", []):
            logger.info("[maintenance] yearly %s skipped (exists)", yk)
            return MaintenanceResult(True, "skipped_exists", out)

        monthly_files = self._iter_long_monthly_files_for_year(yk)
        if not monthly_files:
            logger.info("[maintenance] yearly %s skipped (no monthly summaries)", yk)
            return MaintenanceResult(True, "skipped_no_monthly")

        texts: list[str] = []
        for p in monthly_files:
            try:
                texts.append(p.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
        if not "".join(texts).strip():
            logger.info("[maintenance] yearly %s skipped (empty monthly content)", yk)
            return MaintenanceResult(True, "skipped_no_monthly")

        body = self._render_yearly_summary(yk, texts)
        if not dry_run:
            try:
                self._atomic_write_text(out, body)
                publish_palace_file(out)
            except Exception as exc:
                logger.exception("[maintenance] yearly %s write failed: %s", yk, exc)
                return MaintenanceResult(False, "failed_write", out, str(exc))

        chroma_ok = self._index_monthly_to_chroma(
            month_key=yk,
            text=body,
            file_path=out,
            dry_run=dry_run,
        )
        if not chroma_ok:
            logger.warning("[maintenance] yearly %s generated but chroma not indexed", yk)
            return MaintenanceResult(False, "failed_chroma", out, "yearly file exists but chroma failed")

        if not dry_run:
            if yk not in state["yearly_generated"]:
                state["yearly_generated"].append(yk)
            if yk not in state["yearly_chroma_indexed"]:
                state["yearly_chroma_indexed"].append(yk)
            self._save_state(state, dry_run=False)
        logger.info("[maintenance] yearly %s generated path=%s dry_run=%s", yk, out, dry_run)
        return MaintenanceResult(True, "generated", out)

    def cleanup_long_term_for_year(self, year: str, *, dry_run: bool = False) -> MaintenanceResult:
        yk = str(year).strip()
        state = self._load_state()
        out = self._yearly_summary_path(yk)
        if not out.exists() or yk not in state.get("yearly_chroma_indexed", []):
            logger.info("[maintenance] long cleanup %s skipped (yearly/chroma not ready)", yk)
            return MaintenanceResult(True, "skipped_yearly_not_ready")

        monthly_files = self._iter_long_monthly_files_for_year(yk)
        weekly_files = self._iter_long_weekly_files_for_year(yk)
        files = monthly_files + weekly_files
        if not files:
            logger.info("[maintenance] long cleanup %s skipped (no monthly/weekly files)", yk)
            return MaintenanceResult(True, "skipped_no_files")

        archive_dir = self._long_dir / "_archive" / "yearly" / yk
        moved = 0
        for p in files:
            dst = archive_dir / p.name
            if dry_run:
                moved += 1
                continue
            archive_dir.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                dst = archive_dir / f"{p.stem}_{int(time.time())}{p.suffix}"
            p.replace(dst)
            publish_palace_file(dst)
            moved += 1

        if not dry_run:
            if yk not in state["long_term_yearly_archived"]:
                state["long_term_yearly_archived"].append(yk)
            self._save_state(state, dry_run=False)
        logger.info("[maintenance] long cleanup %s moved=%d dry_run=%s", yk, moved, dry_run)
        return MaintenanceResult(True, "archived", archive_dir, f"moved={moved}")

    # ---------- runners ----------
    def run_daily_maintenance(self, *, now: datetime | None = None, dry_run: bool = False) -> dict[str, Any]:
        from neuralpal.config import get_settings

        if get_settings().memory_tiered_pipeline_only:
            from neuralpal.memory.memory_ids import backfill_memory_ids

            n = int(backfill_memory_ids(self._root))
            return {"mode": "tiered", "backfill_ids": n}
        n = now or datetime.now()
        target = (n.date() - timedelta(days=1))
        gen = self.generate_daily_summary(target, force=False, dry_run=dry_run)
        cln = self.cleanup_short_term_for_date(target, dry_run=dry_run)
        state = self._load_state()
        if not dry_run:
            state["last_daily_maintenance_date"] = n.date().isoformat()
            self._save_state(state, dry_run=False)
        return {"date": target.isoformat(), "generate": gen.status, "cleanup": cln.status}

    def run_monthly_maintenance(self, *, now: datetime | None = None, dry_run: bool = False) -> dict[str, Any]:
        from neuralpal.config import get_settings

        if get_settings().memory_tiered_pipeline_only:
            from neuralpal.memory.memory_tiered_maintenance import run_tiered_monthly

            return run_tiered_monthly(self, now=now, dry_run=dry_run)
        n = now or datetime.now()
        first_this_month = date(n.year, n.month, 1)
        prev_month_last_day = first_this_month - timedelta(days=1)
        mk = prev_month_last_day.strftime("%Y-%m")
        gen = self.generate_monthly_summary(mk, force=False, dry_run=dry_run)
        cln = self.cleanup_middle_term_for_month(mk, dry_run=dry_run)
        state = self._load_state()
        if not dry_run:
            state["last_monthly_maintenance_month"] = mk
            self._save_state(state, dry_run=False)
        return {"month": mk, "generate": gen.status, "cleanup": cln.status}

    def run_weekly_maintenance(self, *, now: datetime | None = None, dry_run: bool = False) -> dict[str, Any]:
        from neuralpal.config import get_settings

        if get_settings().memory_tiered_pipeline_only:
            from neuralpal.memory.memory_tiered_maintenance import run_tiered_weekly

            return run_tiered_weekly(self, now=now, dry_run=dry_run)
        n = now or datetime.now()
        target = n.date() - timedelta(days=7)
        iso = target.isocalendar()
        wk = f"{iso.year}-W{iso.week:02d}"
        gen = self.generate_weekly_summary(wk, force=False, dry_run=dry_run)
        cln = self.cleanup_middle_term_for_week(wk, dry_run=dry_run)
        state = self._load_state()
        if not dry_run:
            state["last_weekly_maintenance_week"] = wk
            self._save_state(state, dry_run=False)
        return {"week": wk, "generate": gen.status, "cleanup": cln.status}

    def run_yearly_maintenance(self, *, now: datetime | None = None, dry_run: bool = False) -> dict[str, Any]:
        n = now or datetime.now()
        yk = str(n.year - 1)
        gen = self.generate_yearly_summary(yk, force=False, dry_run=dry_run)
        cln = self.cleanup_long_term_for_year(yk, dry_run=dry_run)
        state = self._load_state()
        if not dry_run:
            state["last_yearly_maintenance_year"] = yk
            self._save_state(state, dry_run=False)
        return {"year": yk, "generate": gen.status, "cleanup": cln.status}

    def run_startup_catchup(self, *, now: datetime | None = None, dry_run: bool = False) -> dict[str, Any]:
        n = now or datetime.now()
        daily = self.run_daily_maintenance(now=n, dry_run=dry_run)
        weekly = self.run_weekly_maintenance(now=n, dry_run=dry_run)
        monthly = self.run_monthly_maintenance(now=n, dry_run=dry_run)
        yearly = self.run_yearly_maintenance(now=n, dry_run=dry_run)
        return {"daily": daily, "weekly": weekly, "monthly": monthly, "yearly": yearly}

    # ---------- background scheduler ----------
    @classmethod
    def stop_background_scheduler(cls) -> None:
        with cls._scheduler_lock:
            cls._stop_event.set()
            cls._scheduler_thread = None

    def start_background_scheduler(self, *, interval_seconds: int = 600, dry_run: bool = False) -> bool:
        if interval_seconds < 60:
            interval_seconds = 60
        with self.__class__._scheduler_lock:
            t = self.__class__._scheduler_thread
            if t is not None and t.is_alive():
                return False
            self.__class__._stop_event.clear()

            def _worker() -> None:
                logger.info("[maintenance] background scheduler started interval=%ss", interval_seconds)
                while not self.__class__._stop_event.is_set():
                    try:
                        now = datetime.now()
                        self.run_daily_maintenance(now=now, dry_run=dry_run)
                        self.run_weekly_maintenance(now=now, dry_run=dry_run)
                        self.run_monthly_maintenance(now=now, dry_run=dry_run)
                        self.run_yearly_maintenance(now=now, dry_run=dry_run)
                    except Exception:
                        logger.exception("[maintenance] background scheduler tick failed")
                    self.__class__._stop_event.wait(interval_seconds)
                logger.info("[maintenance] background scheduler stopped")

            t = threading.Thread(target=_worker, daemon=True, name="memory-maintenance")
            t.start()
            self.__class__._scheduler_thread = t
            return True
