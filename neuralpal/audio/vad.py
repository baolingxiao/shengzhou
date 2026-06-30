# -*- coding: utf-8 -*-
"""语音活动检测与静音端点判定。"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Literal

from neuralpal.audio.pcm_utils import FRAME_BYTES

logger = logging.getLogger(__name__)

VadEvent = Literal["speech", "silence", "utterance_end"]


@dataclass
class VadConfig:
    silence_seconds: float = 1.2
    min_speech_seconds: float = 0.4
    sample_rate: int = 16_000
    frame_ms: int = 30
    aggressiveness: int = 2


class SilenceEndpointDetector:
    """基于 webrtcvad 的「说完一句话」检测。"""

    def __init__(self, config: VadConfig | None = None) -> None:
        self._config = config or VadConfig()
        self._has_speech = False
        self._last_speech_at = 0.0
        self._speech_started_at = 0.0
        self._vad = self._build_vad()

    def _build_vad(self):
        try:
            import webrtcvad

            vad = webrtcvad.Vad()
            vad.set_mode(max(0, min(3, int(self._config.aggressiveness))))
            return vad
        except Exception:
            logger.warning("webrtcvad unavailable, falling back to energy VAD", exc_info=True)
            return None

    def reset(self) -> None:
        self._has_speech = False
        self._last_speech_at = 0.0
        self._speech_started_at = 0.0

    def feed(self, frame: bytes) -> VadEvent:
        if len(frame) != FRAME_BYTES:
            return "silence"

        now = time.monotonic()
        is_speech = self._is_speech_frame(frame)
        if is_speech:
            if not self._has_speech:
                self._speech_started_at = now
            self._has_speech = True
            self._last_speech_at = now
            return "speech"

        if not self._has_speech:
            return "silence"

        silence_elapsed = now - self._last_speech_at
        if silence_elapsed < self._config.silence_seconds:
            return "silence"

        speech_seconds = max(0.0, self._last_speech_at - self._speech_started_at)
        if speech_seconds < self._config.min_speech_seconds:
            self.reset()
            return "silence"

        self.reset()
        return "utterance_end"

    def _is_speech_frame(self, frame: bytes) -> bool:
        if self._vad is not None:
            try:
                return bool(self._vad.is_speech(frame, self._config.sample_rate))
            except Exception:
                pass
        return self._energy_is_speech(frame)

    @staticmethod
    def _energy_is_speech(frame: bytes) -> bool:
        if len(frame) < 2:
            return False
        total = 0
        count = len(frame) // 2
        for i in range(0, len(frame), 2):
            sample = int.from_bytes(frame[i : i + 2], "little", signed=True)
            total += sample * sample
        if count <= 0:
            return False
        rms = (total / count) ** 0.5
        return rms >= 450.0
