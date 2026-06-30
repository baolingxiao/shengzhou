# -*- coding: utf-8 -*-
"""贾维斯 · 语音 STT/TTS 服务（复用百事通 neuralpal.audio 模块）。"""

from __future__ import annotations

import asyncio
import base64
import time
from dataclasses import dataclass

from neuralpal.audio.cache import DiskAudioCache
from neuralpal.audio.elevenlabs_adapter import ElevenLabsConfig, ElevenLabsTTSAdapter
from neuralpal.audio.stt_adapter import SttAdapter, SttConfig, normalize_stt_provider
from neuralpal.audio.text_chunker import TextChunker
from neuralpal.audio.voice_trace import voice_trace, voice_trace_error
from neuralpal.audio.wake_detector import (
    build_wake_stt_prompt,
    is_wake_only_text,
    match_wake_phrase,
    parse_wake_phrases,
    strip_wake_prefix,
)
from neuralpal.config import get_settings


@dataclass(frozen=True)
class VoiceStatus:
    stt_available: bool
    stt_provider: str
    stt_model: str
    stt_reason: str
    tts_available: bool
    tts_reason: str
    wake_phrases: tuple[str, ...]
    silence_seconds: float
    min_speech_seconds: float
    wake_timeout_seconds: float
    followup_seconds: float
    wake_max_seconds: float
    wake_stt_max_seconds: float
    wake_silence_seconds: float


@dataclass(frozen=True)
class SttResult:
    text: str
    wake_phrase: str | None = None
    cleaned_text: str = ""
    is_wake_only: bool = False


@dataclass(frozen=True)
class TtsChunk:
    index: int
    audio_base64: str
    mime_type: str = "audio/mpeg"


class VoiceService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._wake_phrases = self._load_wake_phrases()
        self._stt = self._build_stt()
        self._tts: ElevenLabsTTSAdapter | None = None
        self._chunker: TextChunker | None = None
        self._cache: DiskAudioCache | None = None
        self._init_tts()

    def _load_wake_phrases(self) -> tuple[str, ...]:
        raw = (self._settings.voice_wake_phrases or "").replace("，", ",")
        phrases = parse_wake_phrases(raw) if raw.strip() else parse_wake_phrases(["在不", "再不", "仔不"])
        return tuple(phrases or ["在不", "再不", "仔不"])

    def _resolve_stt_api_key(self, provider: str) -> str:
        s = self._settings
        if s.voice_stt_api_key.strip():
            return s.voice_stt_api_key.strip()
        if provider in ("openai", "whisper"):
            return s.openai_api_key.strip()
        if provider in ("elevenlabs", "11labs", "scribe"):
            return s.elevenlabs_api_key.strip()
        return ""

    def _resolve_stt_model(self, provider: str) -> str:
        s = self._settings
        if provider in ("local", "faster_whisper", "local_whisper", "whisper_local"):
            return s.voice_stt_local_model or "base"
        if provider in ("openai", "whisper"):
            return s.voice_stt_model if s.voice_stt_model != "base" else "whisper-1"
        return s.voice_stt_model or "scribe_v2"

    def _build_stt(self) -> SttAdapter:
        s = self._settings
        provider = normalize_stt_provider(s.voice_stt_provider or "local")
        return SttAdapter(
            SttConfig(
                provider=provider,
                api_key=self._resolve_stt_api_key(provider),
                model=self._resolve_stt_model(provider),
                language=s.voice_stt_language,
                timeout_seconds=int(s.voice_stt_timeout_seconds),
                elevenlabs_api_url=s.voice_stt_elevenlabs_api_url,
            )
        )

    def _init_tts(self) -> None:
        s = self._settings
        if not (s.reply_tts_enabled and s.elevenlabs_api_key and s.elevenlabs_voice_id):
            return
        self._chunker = TextChunker(max_chars=s.reply_tts_chunk_chars)
        self._cache = DiskAudioCache(s.reply_tts_cache_dir)
        self._tts = ElevenLabsTTSAdapter(
            ElevenLabsConfig(
                api_key=s.elevenlabs_api_key,
                voice_id=s.elevenlabs_voice_id,
                model_id=s.elevenlabs_model_id,
                api_url=s.elevenlabs_api_url,
                output_format=s.elevenlabs_output_format,
                stability=s.elevenlabs_stability,
                similarity_boost=s.elevenlabs_similarity_boost,
                style=s.elevenlabs_style,
                use_speaker_boost=s.elevenlabs_use_speaker_boost,
                speed=s.elevenlabs_speed,
                timeout_seconds=s.elevenlabs_timeout_seconds,
            )
        )

    def status(self) -> VoiceStatus:
        s = self._settings
        stt_reason = "" if self._stt.available else self._stt.unavailable_reason()
        tts_reason = ""
        if not s.reply_tts_enabled:
            tts_reason = "NEURALPAL_REPLY_TTS_ENABLED=false"
        elif not s.elevenlabs_api_key:
            tts_reason = "缺少 ELEVENLABS_API_KEY"
        elif not s.elevenlabs_voice_id:
            tts_reason = "缺少 ELEVENLABS_VOICE_ID"
        return VoiceStatus(
            stt_available=self._stt.available,
            stt_provider=self._stt.provider,
            stt_model=self._resolve_stt_model(normalize_stt_provider(s.voice_stt_provider or "local")),
            stt_reason=stt_reason,
            tts_available=self._tts is not None,
            tts_reason=tts_reason,
            wake_phrases=self._wake_phrases,
            silence_seconds=float(s.voice_silence_seconds),
            min_speech_seconds=float(s.voice_min_speech_seconds),
            wake_timeout_seconds=float(s.voice_wake_timeout_seconds),
            followup_seconds=float(s.voice_followup_seconds),
            wake_max_seconds=float(s.voice_wake_max_seconds),
            wake_stt_max_seconds=float(s.voice_wake_stt_max_seconds),
            wake_silence_seconds=float(s.voice_wake_silence_seconds),
        )

    def transcribe_wav(self, wav_bytes: bytes, *, purpose: str = "utterance") -> SttResult:
        if not self._stt.available:
            raise RuntimeError(self._stt.unavailable_reason())
        prompt = build_wake_stt_prompt(self._wake_phrases) if purpose == "wake" else ""
        text = self._stt.transcribe_wav(wav_bytes, prompt=prompt).strip()
        if purpose != "wake":
            return SttResult(text=text)

        wake = match_wake_phrase(text, self._wake_phrases)
        cleaned = strip_wake_prefix(text, wake, self._wake_phrases) if wake else ""
        return SttResult(
            text=text,
            wake_phrase=wake,
            cleaned_text=cleaned.strip(),
            is_wake_only=bool(wake and is_wake_only_text(cleaned or text, self._wake_phrases)),
        )

    def synthesize(self, text: str) -> list[TtsChunk]:
        if self._tts is None or self._chunker is None or self._cache is None:
            raise RuntimeError(self.status().tts_reason or "TTS 不可用")
        content = (text or "").strip()
        if not content:
            raise ValueError("TTS 文本为空")

        s = self._settings
        chunks = self._chunker.split(content)
        if not chunks:
            raise ValueError("TTS 分片为空")

        voice_trace("tts.start", f"chars={len(content)} chunks={len(chunks)}")
        out: list[TtsChunk] = []
        tr = None
        try:
            from neuralpal.trace.context import get_trace

            tr = get_trace()
            if tr is not None:
                tr.record_tts_meta(
                    enabled=True,
                    provider="elevenlabs",
                    model=s.elevenlabs_model_id,
                    input_text=content,
                    chunk_texts=chunks,
                )
        except Exception:
            pass

        for index, chunk in enumerate(chunks):
            t0 = time.perf_counter()
            key = self._cache.build_key(
                "reply_tts_elevenlabs",
                s.elevenlabs_model_id,
                s.elevenlabs_voice_id,
                s.elevenlabs_output_format,
                f"{s.elevenlabs_speed:.2f}",
                chunk,
            )
            cached = self._cache.get(key, ".mp3")
            was_cached = cached is not None
            if cached is None:
                cached = self._tts.synthesize(chunk)
                self._cache.put(key, cached, ".mp3")
            req_ms = (time.perf_counter() - t0) * 1000.0
            if tr is not None:
                try:
                    tr.record_tts_chunk_request(
                        index,
                        chunk,
                        req_ms,
                        cached=was_cached,
                    )
                except Exception:
                    pass
            out.append(
                TtsChunk(
                    index=index,
                    audio_base64=base64.b64encode(cached).decode("ascii"),
                )
            )
        voice_trace("tts.ready", f"chunks={len(out)}")
        if tr is not None:
            try:
                tr.save()
            except Exception:
                pass
        return out

    async def transcribe_wav_async(self, wav_bytes: bytes, *, purpose: str = "utterance") -> SttResult:
        return await asyncio.to_thread(self.transcribe_wav, wav_bytes, purpose=purpose)

    async def synthesize_async(self, text: str) -> list[TtsChunk]:
        try:
            return await asyncio.to_thread(self.synthesize, text)
        except Exception as exc:
            voice_trace_error("tts.error", f"{type(exc).__name__}: {exc}")
            raise
