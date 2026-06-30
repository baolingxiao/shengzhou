# -*- coding: utf-8 -*-
"""PySide6 麦克风采集，按固定帧长输出 PCM。"""

from __future__ import annotations

import logging
from typing import Callable

from PySide6 import QtCore, QtMultimedia

from neuralpal.audio.pcm_utils import FRAME_BYTES, SAMPLE_RATE
from neuralpal.audio.voice_trace import voice_trace, voice_trace_error, voice_trace_warn

logger = logging.getLogger(__name__)


class MicCapture(QtCore.QObject):
    frame_ready = QtCore.Signal(bytes)
    error = QtCore.Signal(str)

    def __init__(
        self,
        *,
        sample_rate: int = SAMPLE_RATE,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._sample_rate = sample_rate
        self._audio_source: QtMultimedia.QAudioSource | None = None
        self._io_device: QtCore.QIODevice | None = None
        self._pending = bytearray()
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active

    def start(self) -> bool:
        if self._active:
            return True
        device = self._default_input_device()
        if device is None:
            voice_trace_error("mic.start", "未找到可用麦克风")
            self.error.emit("未找到可用麦克风，请检查系统权限与设备。")
            return False
        fmt = QtMultimedia.QAudioFormat()
        fmt.setSampleRate(self._sample_rate)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QtMultimedia.QAudioFormat.Int16)
        try:
            self._audio_source = QtMultimedia.QAudioSource(device, fmt, self)
            self._io_device = self._audio_source.start()
            if self._io_device is None:
                voice_trace_error("mic.start", "QAudioSource.start 返回空")
                self.error.emit("麦克风启动失败。")
                self._teardown()
                return False
            self._io_device.readyRead.connect(self._on_ready_read)
            self._active = True
            voice_trace("mic.start", f"device={device.description()} rate={self._sample_rate}")
            return True
        except Exception as exc:
            logger.exception("MicCapture start failed")
            voice_trace_error("mic.start", type(exc).__name__)
            self.error.emit(f"麦克风启动失败：{type(exc).__name__}")
            self._teardown()
            return False

    def stop(self) -> None:
        if self._active:
            voice_trace("mic.stop", "采集已停止")
        self._teardown()

    def _default_input_device(self) -> QtMultimedia.QAudioDevice | None:
        try:
            dev = QtMultimedia.QMediaDevices.defaultAudioInput()
            if dev is not None and not dev.isNull():
                return dev
        except Exception:
            logger.debug("defaultAudioInput failed", exc_info=True)
        return None

    def _on_ready_read(self) -> None:
        if self._io_device is None:
            return
        chunk = bytes(self._io_device.readAll())
        if not chunk:
            return
        self._pending.extend(chunk)
        while len(self._pending) >= FRAME_BYTES:
            frame = bytes(self._pending[:FRAME_BYTES])
            del self._pending[:FRAME_BYTES]
            self.frame_ready.emit(frame)

    def _teardown(self) -> None:
        self._active = False
        self._pending.clear()
        if self._io_device is not None:
            try:
                self._io_device.readyRead.disconnect(self._on_ready_read)
            except Exception:
                pass
        if self._audio_source is not None:
            try:
                self._audio_source.stop()
            except Exception:
                pass
        self._io_device = None
        self._audio_source = None
