# -*- coding: utf-8 -*-
"""上下班 / 加班调度测试。"""

from __future__ import annotations

import pytest

from neuralpal.schedule.task_detect import (
    is_overtime_consent,
    is_overtime_decline,
    is_task_request,
)
from neuralpal.schedule.work_mode import is_within_work_hours


def test_task_vs_chat_detection():
    assert is_task_request("帮我调查一下这个产品的销量")
    assert is_task_request("查一下 iPhone 16 价格")
    assert not is_task_request("你是谁")
    assert not is_task_request("在吗")


def test_overtime_consent():
    assert is_overtime_consent("那就麻烦你加个班啦")
    assert is_overtime_consent("行，加班吧")
    assert is_overtime_decline("算了不用加班")


def test_work_hours_weekday_window():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("Asia/Shanghai")
    mon_noon = datetime(2026, 6, 22, 12, 0, tzinfo=tz)
    mon_night = datetime(2026, 6, 22, 19, 0, tzinfo=tz)
    sat_noon = datetime(2026, 6, 20, 12, 0, tzinfo=tz)

    assert is_within_work_hours(now=mon_noon)
    assert not is_within_work_hours(now=mon_night)
    assert not is_within_work_hours(now=sat_noon)
