# -*- coding: utf-8 -*-
"""沈昼世界引擎集成。"""

from neuralpal.shenzhou.client import fetch_life_context, ping, run_daily_pipeline, sync_user_day
from neuralpal.shenzhou.context_archive import run_context_archive
from neuralpal.shenzhou.proactive import proactive_status, run_proactive_outreach
from neuralpal.shenzhou.scheduler import start_shenzhou_scheduler

__all__ = [
    "fetch_life_context",
    "ping",
    "proactive_status",
    "run_context_archive",
    "run_daily_pipeline",
    "run_proactive_outreach",
    "sync_user_day",
    "start_shenzhou_scheduler",
]
