# -*- coding: utf-8 -*-
from __future__ import annotations

import time

from neuralpal.audio.pcm_utils import FRAME_BYTES, pcm_duration_seconds, pcm_to_wav_bytes
from neuralpal.audio.vad import SilenceEndpointDetector, VadConfig
from neuralpal.audio.wake_detector import match_wake_phrase, normalize_wake_text, strip_wake_prefix


def _silence_frame() -> bytes:
    return b"\x00" * FRAME_BYTES


def _speech_like_frame(amplitude: int = 4000) -> bytes:
    samples = []
    for i in range(FRAME_BYTES // 2):
        v = amplitude if (i // 80) % 2 == 0 else -amplitude
        samples.append(int.to_bytes(v, 2, "little", signed=True))
    return b"".join(samples)


def test_normalize_wake_text() -> None:
    assert normalize_wake_text("  在不！ ") == "在不"


def test_match_wake_phrase() -> None:
    phrases = ["在不", "再不", "仔不"]
    assert match_wake_phrase("嗯，在不", phrases) == "在不"
    assert match_wake_phrase("仔不在吗", phrases) == "仔不"
    assert match_wake_phrase("再補再補", phrases) == "再不"
    assert match_wake_phrase("再来一波", phrases) is None
    assert match_wake_phrase("你好呀", phrases) is None


def test_build_wake_stt_prompt() -> None:
    from neuralpal.audio.wake_detector import build_wake_stt_prompt

    assert build_wake_stt_prompt(["在不", "再不"]) == "在不。再不。"


def test_strip_wake_prefix() -> None:
    phrases = ["在不", "再不", "仔不"]
    assert strip_wake_prefix("在不你好", "在不", phrases) == "你好"
    assert strip_wake_prefix("再補今天天气", "再不", phrases) == "今天天气"
    assert strip_wake_prefix("再不。仔不。", "再不", phrases) == ""


def test_is_wake_only_text() -> None:
    from neuralpal.audio.wake_detector import is_wake_only_text

    phrases = ["在不", "再不", "仔不"]
    assert is_wake_only_text("仔不。", phrases)
    assert is_wake_only_text("再不", phrases)
    assert not is_wake_only_text("今天天气怎么样", phrases)


def test_stt_adapter_elevenlabs_available(monkeypatch) -> None:
    from neuralpal.audio.stt_adapter import SttAdapter, SttConfig

    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    adapter = SttAdapter(SttConfig(provider="elevenlabs"))
    assert not adapter.available
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    assert adapter.available


def test_stt_adapter_openai_available(monkeypatch) -> None:
    from neuralpal.audio.stt_adapter import SttAdapter, SttConfig

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    adapter = SttAdapter(SttConfig(provider="openai"))
    assert not adapter.available
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    assert adapter.available


def test_pcm_to_wav_roundtrip_header() -> None:
    pcm = _silence_frame() * 10
    wav = pcm_to_wav_bytes(pcm)
    assert wav[:4] == b"RIFF"
    assert pcm_duration_seconds(pcm) > 0.2


def test_vad_utterance_end_after_speech_and_silence() -> None:
    vad = SilenceEndpointDetector(
        VadConfig(silence_seconds=0.12, min_speech_seconds=0.06, aggressiveness=0)
    )
    ended = False
    for _ in range(8):
        if vad.feed(_speech_like_frame()) == "utterance_end":
            ended = True
    assert not ended
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline and not ended:
        if vad.feed(_silence_frame()) == "utterance_end":
            ended = True
        time.sleep(0.03)
    assert ended
