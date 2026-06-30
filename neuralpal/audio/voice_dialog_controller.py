# -*- coding: utf-8 -*-
"""语音对话状态机：唤醒词 → 静音切段 → STT → 回复。"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Literal

from PySide6 import QtCore

from neuralpal.audio.mic_capture import MicCapture
from neuralpal.audio.pcm_utils import pcm_duration_seconds, pcm_tail, pcm_trim_leading_silence
from neuralpal.audio.stt_adapter import SttAdapter, SttConfig, normalize_stt_provider
from neuralpal.audio.vad import SilenceEndpointDetector, VadConfig
from neuralpal.audio.voice_trace import VoiceFrameStats, voice_trace, voice_trace_error, voice_trace_warn
from neuralpal.audio.wake_detector import (
    build_wake_stt_prompt,
    is_wake_only_text,
    match_wake_phrase,
    parse_wake_phrases,
    strip_wake_prefix,
)

VoiceState = Literal["off", "armed", "followup", "capturing", "processing", "speaking"]

LISTEN_PROMPT = "我在听，请说。"


@dataclass(frozen=True)
class VoiceDialogConfig:
    wake_phrases: tuple[str, ...] = ("在不", "再不", "仔不")
    silence_seconds: float = 1.2
    min_speech_seconds: float = 0.4
    wake_timeout_seconds: float = 8.0
    followup_seconds: float = 30.0
    wake_max_seconds: float = 2.5
    wake_stt_max_seconds: float = 4.0
    wake_silence_seconds: float = 0.7
    sample_rate: int = 16_000
    stt_api_key: str = ""
    stt_provider: str = "elevenlabs"
    stt_model: str = "scribe_v2"
    stt_language: str = "zh"
    stt_timeout_seconds: int = 45
    stt_elevenlabs_api_url: str = "https://api.elevenlabs.io/v1/speech-to-text"


class VoiceDialogController(QtCore.QObject):
    state_changed = QtCore.Signal(str)
    status_hint = QtCore.Signal(str)
    listen_prompt = QtCore.Signal()
    user_transcript = QtCore.Signal(str)
    need_reply = QtCore.Signal(str)
    error = QtCore.Signal(str)
    _wake_stt_result = QtCore.Signal(str)
    _wake_stt_error = QtCore.Signal(str)
    _capture_stt_result = QtCore.Signal(str)
    _capture_stt_error = QtCore.Signal(str)

    def __init__(
        self,
        config: VoiceDialogConfig,
        *,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._wake_phrases = parse_wake_phrases(config.wake_phrases)
        self._wake_stt_prompt = build_wake_stt_prompt(self._wake_phrases)
        self._state: VoiceState = "off"
        self._mic = MicCapture(sample_rate=config.sample_rate, parent=self)
        self._mic.frame_ready.connect(self._on_frame)
        self._mic.error.connect(self.error.emit)
        self._stt = SttAdapter(
            SttConfig(
                provider=normalize_stt_provider(config.stt_provider),
                api_key=config.stt_api_key,
                model=config.stt_model,
                language=config.stt_language,
                timeout_seconds=config.stt_timeout_seconds,
                elevenlabs_api_url=config.stt_elevenlabs_api_url,
            )
        )
        vad_cfg = VadConfig(
            silence_seconds=config.silence_seconds,
            min_speech_seconds=config.min_speech_seconds,
            sample_rate=config.sample_rate,
        )
        armed_vad_cfg = VadConfig(
            silence_seconds=config.wake_silence_seconds,
            min_speech_seconds=min(config.min_speech_seconds, 0.25),
            sample_rate=config.sample_rate,
            aggressiveness=2,
        )
        self._armed_vad = SilenceEndpointDetector(armed_vad_cfg)
        self._capture_vad = SilenceEndpointDetector(vad_cfg)
        self._armed_buffer = bytearray()
        self._capture_buffer = bytearray()
        self._awaiting_question = False
        self._followup_until = 0.0
        self._awaiting_deadline = 0.0
        self._followup_timer = QtCore.QTimer(self)
        self._followup_timer.setSingleShot(True)
        self._followup_timer.timeout.connect(self._on_followup_timeout)
        self._await_timer = QtCore.QTimer(self)
        self._await_timer.setSingleShot(True)
        self._await_timer.timeout.connect(self._on_await_question_timeout)
        self._stt_lock = threading.Lock()
        self._wake_stt_result.connect(self._handle_wake_stt_result)
        self._wake_stt_error.connect(self._handle_wake_stt_error)
        self._capture_stt_result.connect(self._handle_capture_stt_result)
        self._capture_stt_error.connect(self._handle_capture_stt_error)
        self._frame_stats = VoiceFrameStats(interval_seconds=3.0)
        self._mic_ignore_logged = False
        self._playback_hold = False
        self._armed_buffer_max_bytes = int(
            config.wake_stt_max_seconds * config.sample_rate * 2
        )

    @property
    def state(self) -> VoiceState:
        return self._state

    @property
    def available(self) -> bool:
        return self._stt.available

    @property
    def unavailable_reason(self) -> str:
        return self._stt.unavailable_reason()

    def start(self) -> bool:
        voice_trace(
            "session.start",
            f"provider={self._stt.provider} model={self._config.stt_model} "
            f"wake={','.join(self._wake_phrases[:3])}",
        )
        if not self._stt.available:
            reason = self._stt.unavailable_reason()
            voice_trace_error("session.start", reason)
            self.error.emit(f"语音对话不可用：{reason}")
            return False
        if not self._mic.start():
            voice_trace_error("session.start", "麦克风启动失败")
            return False
        self._reset_buffers()
        self._mic_ignore_logged = False
        self._set_state("armed")
        self._emit_status_for_state()
        voice_trace("session.ready", "等待唤醒词")
        return True

    def stop(self) -> None:
        voice_trace("session.stop", f"state={self._state}")
        self._followup_timer.stop()
        self._await_timer.stop()
        self._mic.stop()
        self._reset_buffers()
        self._set_state("off")
        self.status_hint.emit("")

    def notify_processing_started(self) -> None:
        if self._state in ("capturing", "followup", "armed"):
            self._set_state("processing")
            self.status_hint.emit("想想…")
            voice_trace("pipeline", "LLM 思考中（麦克风暂停）")

    def notify_speaking_started(self) -> None:
        if self._state == "processing":
            self._set_state("speaking")
            self.status_hint.emit("说话中…")
            voice_trace("pipeline", "TTS 播放中（麦克风暂停）")

    def notify_speaking_finished(self) -> None:
        if self._state != "speaking":
            return
        voice_trace("pipeline", "TTS 播放结束，进入免唤醒窗口")
        self._enter_followup()

    def notify_external_playback_started(self) -> None:
        if self._state not in ("armed", "followup"):
            return
        self._playback_hold = True
        self._armed_buffer.clear()
        self._armed_vad.reset()
        self._reset_capture_buffers()
        voice_trace("mic.paused", "外部 TTS 播放中（丢弃缓冲）")

    def notify_external_playback_finished(self) -> None:
        if not self._playback_hold:
            return
        self._playback_hold = False
        self._reset_buffers()
        voice_trace("mic.resume", "外部 TTS 结束，继续监听")
        if self._state == "armed":
            self._emit_status_for_state()
        elif self._state == "followup":
            self.status_hint.emit("继续说吧（免唤醒）")

    def _emit_listen_prompt(self, *, speak: bool) -> None:
        self.status_hint.emit(LISTEN_PROMPT)
        if speak:
            self.listen_prompt.emit()

    def notify_chat_failed(self) -> None:
        voice_trace_warn("pipeline", f"chat.failed state={self._state}")
        if self._state == "processing":
            self._enter_followup()

    @QtCore.Slot(bytes)
    def _on_frame(self, frame: bytes) -> None:
        from neuralpal.audio.pcm_utils import pcm_frame_rms

        if self._state in ("off", "processing", "speaking"):
            if not self._mic_ignore_logged:
                voice_trace("mic.paused", f"state={self._state}（播放/思考时不采集）")
                self._mic_ignore_logged = True
            return
        if self._playback_hold:
            return
        self._mic_ignore_logged = False
        self._frame_stats.set_state(self._state)
        self._frame_stats.tick(frame, rms=pcm_frame_rms(frame))

        if self._state == "followup":
            self._capture_buffer.extend(frame)
            if self._capture_vad.feed(frame) == "utterance_end":
                voice_trace("vad.end", "mode=followup")
                self._finalize_capture()
            return

        if self._state == "armed":
            if self._awaiting_question:
                self._capture_buffer.extend(frame)
                if self._capture_vad.feed(frame) == "utterance_end":
                    voice_trace("vad.end", "mode=question")
                    self._finalize_capture()
                return

            self._armed_buffer.extend(frame)
            if len(self._armed_buffer) > self._armed_buffer_max_bytes:
                del self._armed_buffer[: -self._armed_buffer_max_bytes]
            if self._armed_vad.feed(frame) == "utterance_end":
                pcm = bytes(self._armed_buffer)
                self._armed_buffer.clear()
                self._armed_vad.reset()
                duration = pcm_duration_seconds(pcm, self._config.sample_rate)
                voice_trace("vad.end", f"mode=wake audio={duration:.2f}s")
                if duration > self._config.wake_max_seconds:
                    voice_trace(
                        "wake.long",
                        f"片段 {duration:.2f}s > 建议 {self._config.wake_max_seconds}s，仍尝试识别",
                    )
                self._check_wake_async(self._prepare_wake_pcm(pcm))

    def _prepare_wake_pcm(self, pcm: bytes) -> bytes:
        trimmed = pcm_trim_leading_silence(pcm, sample_rate=self._config.sample_rate)
        tail = pcm_tail(trimmed, self._config.wake_stt_max_seconds, self._config.sample_rate)
        duration = pcm_duration_seconds(pcm, self._config.sample_rate)
        tail_duration = pcm_duration_seconds(tail, self._config.sample_rate)
        if duration > tail_duration + 0.05:
            voice_trace_warn(
                "wake.trim",
                f"STT 截取末尾 {tail_duration:.2f}s（原 {duration:.2f}s）",
            )
        return tail

    def _check_wake_async(self, pcm: bytes) -> None:
        if not pcm:
            return
        self.status_hint.emit("识别唤醒词…")
        voice_trace("wake.check", f"audio={pcm_duration_seconds(pcm, self._config.sample_rate):.2f}s")

        def worker() -> None:
            with self._stt_lock:
                try:
                    text = self._stt.transcribe_pcm(
                        pcm,
                        sample_rate=self._config.sample_rate,
                        purpose="wake",
                        prompt=self._wake_stt_prompt,
                    )
                except Exception as exc:
                    self._wake_stt_error.emit(str(exc))
                    return
            self._wake_stt_result.emit(text or "")

        threading.Thread(target=worker, daemon=True).start()

    @QtCore.Slot(str)
    def _handle_wake_stt_error(self, message: str) -> None:
        if self._state != "armed":
            return
        voice_trace_error("wake.stt", message)
        self.error.emit(message if len(message) > 20 else f"唤醒词识别失败：{message}")
        self._emit_status_for_state()

    @QtCore.Slot(str)
    def _handle_wake_stt_result(self, text: str) -> None:
        if self._state != "armed":
            return
        wake = match_wake_phrase(text, self._wake_phrases)
        voice_trace("wake.result", f"raw={text!r} matched={wake!r}")
        if wake is None:
            voice_trace_warn("wake.miss", "未匹配唤醒词，继续监听")
            self._emit_status_for_state()
            return
        cleaned = strip_wake_prefix(text, wake, self._wake_phrases)
        self._awaiting_question = True
        self._awaiting_deadline = time.monotonic() + self._config.wake_timeout_seconds
        self._await_timer.start(int(self._config.wake_timeout_seconds * 1000))
        self._reset_capture_buffers()
        self._emit_listen_prompt(speak=True)
        voice_trace("wake.ok", f"phrase={wake} followup_text={cleaned!r}")
        if cleaned and not is_wake_only_text(cleaned, self._wake_phrases):
            self._submit_transcript(cleaned)

    def _finalize_capture(self) -> None:
        pcm = bytes(self._capture_buffer)
        self._reset_capture_buffers()
        duration = pcm_duration_seconds(pcm, self._config.sample_rate)
        if duration < self._config.min_speech_seconds:
            voice_trace_warn("capture.short", f"audio={duration:.2f}s < min={self._config.min_speech_seconds}s")
            if self._awaiting_question:
                self._emit_listen_prompt(speak=False)
            else:
                self._emit_status_for_state()
            return
        self._await_timer.stop()
        self._awaiting_question = False
        self._set_state("processing")
        self.status_hint.emit("识别中…")
        voice_trace("capture.ok", f"audio={duration:.2f}s，开始 STT")

        def worker() -> None:
            with self._stt_lock:
                try:
                    text = self._stt.transcribe_pcm(
                        pcm,
                        sample_rate=self._config.sample_rate,
                        purpose="utterance",
                    )
                except Exception as exc:
                    self._capture_stt_error.emit(str(exc))
                    return
            self._capture_stt_result.emit(text or "")

        threading.Thread(target=worker, daemon=True).start()

    @QtCore.Slot(str)
    def _handle_capture_stt_error(self, message: str) -> None:
        voice_trace_error("utterance.stt", message)
        self.error.emit(f"语音识别失败：{message}")
        self._enter_followup()

    @QtCore.Slot(str)
    def _handle_capture_stt_result(self, text: str) -> None:
        transcript = (text or "").strip()
        if not transcript:
            voice_trace_warn("utterance.empty", "STT 返回空文本")
            self._enter_followup()
            return
        self._submit_transcript(transcript)

    def _submit_transcript(self, transcript: str) -> None:
        text = transcript.strip()
        if not text:
            voice_trace_warn("chat.empty", "提交空 transcript")
            self._enter_followup()
            return
        voice_trace("chat.submit", f"text={text!r}")
        self.user_transcript.emit(text)
        self.need_reply.emit(text)
        self.notify_processing_started()

    def _enter_followup(self) -> None:
        self._awaiting_question = False
        self._await_timer.stop()
        self._reset_buffers()
        self._followup_until = time.monotonic() + self._config.followup_seconds
        self._followup_timer.start(int(self._config.followup_seconds * 1000))
        self._set_state("followup")
        self.status_hint.emit("继续说吧（免唤醒）")
        voice_trace("followup.enter", f"seconds={self._config.followup_seconds}")

    def _on_followup_timeout(self) -> None:
        if self._state != "followup":
            return
        voice_trace("followup.timeout", "回到等待唤醒词")
        self._set_state("armed")
        self._emit_status_for_state()

    def _on_await_question_timeout(self) -> None:
        if not self._awaiting_question or self._state != "armed":
            return
        voice_trace_warn("question.timeout", "唤醒后超时未说话")
        self._awaiting_question = False
        self._reset_capture_buffers()
        self._emit_status_for_state()

    def _emit_status_for_state(self) -> None:
        if self._state == "armed":
            if self._awaiting_question:
                self._emit_listen_prompt(speak=False)
                return
            sample = "、".join(self._wake_phrases[:2]) or "在不"
            self.status_hint.emit(f"说「{sample}」开始对话")
        elif self._state == "followup":
            self.status_hint.emit("继续说吧（免唤醒）")
        elif self._state == "off":
            self.status_hint.emit("")

    def _reset_capture_buffers(self) -> None:
        self._capture_buffer.clear()
        self._capture_vad.reset()

    def _reset_buffers(self) -> None:
        self._armed_buffer.clear()
        self._armed_vad.reset()
        self._reset_capture_buffers()

    def _set_state(self, state: VoiceState) -> None:
        if self._state == state:
            return
        prev = self._state
        self._state = state
        self._frame_stats.set_state(state)
        self.state_changed.emit(state)
        voice_trace("state", f"{prev} -> {state}")

