# -*- coding: utf-8 -*-
"""PCM 工具：帧切分、WAV 封装、时长估算。"""

from __future__ import annotations

import io
import wave
from typing import Iterable

SAMPLE_RATE = 16_000
FRAME_MS = 30
BYTES_PER_SAMPLE = 2
FRAME_BYTES = SAMPLE_RATE * BYTES_PER_SAMPLE * FRAME_MS // 1000


def iter_fixed_frames(pcm: bytes, frame_bytes: int = FRAME_BYTES) -> Iterable[bytes]:
    for i in range(0, len(pcm) - len(pcm) % frame_bytes, frame_bytes):
        yield pcm[i : i + frame_bytes]


def pcm_duration_seconds(pcm: bytes, sample_rate: int = SAMPLE_RATE) -> float:
    if not pcm:
        return 0.0
    return len(pcm) / float(sample_rate * BYTES_PER_SAMPLE)


def pcm_tail(pcm: bytes, max_seconds: float, sample_rate: int = SAMPLE_RATE) -> bytes:
    """保留 PCM 末尾若干秒（唤醒词通常出现在最近一段语音）。"""
    if not pcm or max_seconds <= 0:
        return pcm
    max_bytes = int(max_seconds * sample_rate * BYTES_PER_SAMPLE)
    if len(pcm) <= max_bytes:
        return pcm
    return pcm[-max_bytes:]


def pcm_trim_leading_silence(
    pcm: bytes,
    *,
    sample_rate: int = SAMPLE_RATE,
    frame_bytes: int = FRAME_BYTES,
    rms_threshold: float = 350.0,
) -> bytes:
    """去掉开头静音，避免长段空白干扰 STT。"""
    if not pcm:
        return pcm
    start = 0
    for i in range(0, len(pcm) - len(pcm) % frame_bytes, frame_bytes):
        frame = pcm[i : i + frame_bytes]
        if pcm_frame_rms(frame) >= rms_threshold:
            start = i
            break
    return pcm[start:] if start else pcm


def pcm_to_wav_bytes(pcm: bytes, sample_rate: int = SAMPLE_RATE) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(BYTES_PER_SAMPLE)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def pcm_frame_rms(frame: bytes) -> float:
    if len(frame) < 2:
        return 0.0
    total = 0
    count = len(frame) // 2
    for i in range(0, len(frame), 2):
        sample = int.from_bytes(frame[i : i + 2], "little", signed=True)
        total += sample * sample
    if count <= 0:
        return 0.0
    return float((total / count) ** 0.5)
