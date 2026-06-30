# -*- coding: utf-8 -*-
"""语音对话链路追踪：统一前缀 [voice]，便于终端排查。"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

_TRACE_LOGGER = "neuralpal.voice"


def is_voice_trace_enabled() -> bool:
    raw = (os.environ.get("NEURALPAL_VOICE_DIALOG_DEBUG") or "true").strip().lower()
    return raw in ("1", "true", "yes", "on")


def voice_trace(step: str, detail: str = "", *, level: int = logging.INFO) -> None:
    if not is_voice_trace_enabled():
        return
    msg = f"[voice] {step}"
    if detail:
        msg += f" | {detail}"
    logging.getLogger(_TRACE_LOGGER).log(level, msg)


def voice_trace_error(step: str, detail: str = "") -> None:
    voice_trace(step, detail, level=logging.ERROR)


def voice_trace_warn(step: str, detail: str = "") -> None:
    voice_trace(step, detail, level=logging.WARNING)


def mask_secret(value: str, *, visible: int = 4) -> str:
    text = (value or "").strip()
    if not text:
        return "(empty)"
    if len(text) <= visible * 2:
        return "*" * len(text)
    return f"{text[:visible]}...{text[-visible:]}"


class VoiceFrameStats:
    """周期性汇报麦克风是否有帧进入（避免每帧刷屏）。"""

    def __init__(self, interval_seconds: float = 3.0) -> None:
        self._interval = interval_seconds
        self._last_report = 0.0
        self._frames = 0
        self._state = "off"

    def set_state(self, state: str) -> None:
        self._state = state

    def tick(self, frame: bytes, *, rms: float | None = None) -> None:
        self._frames += 1
        now = time.monotonic()
        if now - self._last_report < self._interval:
            return
        detail = f"state={self._state} frames+={self._frames}"
        if rms is not None:
            detail += f" last_rms={rms:.0f}"
        voice_trace("mic.frames", detail)
        self._frames = 0
        self._last_report = now
