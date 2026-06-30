# -*- coding: utf-8 -*-
"""语音转文字：本地 Whisper / OpenAI / ElevenLabs。"""

from __future__ import annotations

import io
import json
import logging
import os
from dataclasses import dataclass
from typing import Literal
from urllib import error, request

from neuralpal.audio.http_utils import urlopen as ssl_urlopen
from neuralpal.audio.local_whisper import (
    local_whisper_available,
    local_whisper_unavailable_reason,
    transcribe_wav_bytes as local_transcribe_wav,
)
from neuralpal.audio.voice_trace import voice_trace, voice_trace_error

logger = logging.getLogger(__name__)

SttProvider = Literal["elevenlabs", "openai", "local"]


def _preview(text: str, limit: int = 80) -> str:
    t = (text or "").strip().replace("\n", " ")
    if len(t) <= limit:
        return t
    return t[: limit - 3] + "..."


def normalize_stt_provider(raw: str) -> SttProvider:
    value = (raw or "local").strip().lower()
    if value in ("local", "faster_whisper", "local_whisper", "whisper_local"):
        return "local"
    if value in ("openai", "whisper"):
        return "openai"
    if value in ("elevenlabs", "11labs", "scribe"):
        return "elevenlabs"
    return "local"


@dataclass(frozen=True)
class SttConfig:
    provider: SttProvider = "local"
    api_key: str = ""
    model: str = "base"
    language: str = "zh"
    timeout_seconds: int = 45
    elevenlabs_api_url: str = "https://api.elevenlabs.io/v1/speech-to-text"
    prompt: str = ""


class SttAdapter:
    def __init__(self, config: SttConfig) -> None:
        self._config = config

    @property
    def provider(self) -> SttProvider:
        return self._config.provider

    @property
    def available(self) -> bool:
        if self._config.provider == "local":
            return local_whisper_available()
        return bool(self._resolve_api_key())

    def _resolve_api_key(self) -> str:
        if self._config.api_key.strip():
            return self._config.api_key.strip()
        if self._config.provider == "elevenlabs":
            env_key = (os.environ.get("ELEVENLABS_API_KEY") or "").strip()
            if env_key:
                return env_key
            try:
                from neuralpal.config import get_settings

                return (get_settings().elevenlabs_api_key or "").strip()
            except Exception:
                return ""
        env_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
        if env_key:
            return env_key
        try:
            from neuralpal.config import get_settings

            return (get_settings().openai_api_key or "").strip()
        except Exception:
            return ""

    def unavailable_reason(self) -> str:
        if self.available:
            return ""
        if self._config.provider == "local":
            return local_whisper_unavailable_reason()
        if self._config.provider == "elevenlabs":
            return "缺少 ELEVENLABS_API_KEY（可在 .env 配置，与 TTS 共用）"
        return "缺少 OPENAI_API_KEY（.env 中配置，用于 Whisper 语音识别）"

    def transcribe_wav(self, wav_bytes: bytes, *, prompt: str | None = None) -> str:
        if not wav_bytes:
            return ""
        stt_prompt = (prompt if prompt is not None else self._config.prompt) or ""
        if self._config.provider == "local":
            return local_transcribe_wav(
                wav_bytes,
                model_size=self._config.model or "base",
                language=self._config.language,
                initial_prompt=stt_prompt,
            )
        if self._config.provider == "elevenlabs":
            return self._transcribe_elevenlabs(wav_bytes)
        return self._transcribe_openai(wav_bytes, prompt=stt_prompt)

    def transcribe_pcm(
        self,
        pcm: bytes,
        *,
        sample_rate: int = 16_000,
        purpose: str = "utterance",
        prompt: str | None = None,
    ) -> str:
        from neuralpal.audio.pcm_utils import pcm_duration_seconds, pcm_to_wav_bytes

        duration = pcm_duration_seconds(pcm, sample_rate)
        voice_trace(
            "stt.request",
            f"purpose={purpose} provider={self._config.provider} "
            f"model={self._config.model} audio={duration:.2f}s",
        )
        try:
            text = self.transcribe_wav(
                pcm_to_wav_bytes(pcm, sample_rate=sample_rate),
                prompt=prompt,
            )
        except Exception as exc:
            voice_trace_error("stt.failed", f"purpose={purpose} err={exc}")
            raise
        voice_trace("stt.ok", f"purpose={purpose} text={_preview(text)}")
        return text

    def _transcribe_elevenlabs(self, wav_bytes: bytes) -> str:
        api_key = self._resolve_api_key()
        if not api_key:
            raise RuntimeError("Missing ELEVENLABS_API_KEY for voice STT")

        boundary = "----NeuralPalVoiceSTTBoundary"
        body_parts: list[bytes] = []

        def add_field(name: str, value: str) -> None:
            body_parts.append(f"--{boundary}\r\n".encode())
            body_parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
            body_parts.append(f"{value}\r\n".encode())

        add_field("model_id", self._config.model or "scribe_v2")
        if self._config.language:
            add_field("language_code", self._config.language)
        body_parts.append(f"--{boundary}\r\n".encode())
        body_parts.append(
            b'Content-Disposition: form-data; name="file"; filename="utterance.wav"\r\n'
        )
        body_parts.append(b"Content-Type: audio/wav\r\n\r\n")
        body_parts.append(wav_bytes)
        body_parts.append(b"\r\n")
        body_parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(body_parts)

        url = self._config.elevenlabs_api_url.rstrip("/")
        req = request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "xi-api-key": api_key,
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Accept": "application/json",
            },
        )
        try:
            with ssl_urlopen(req, timeout=self._config.timeout_seconds) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
        except error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="ignore")
            except Exception:
                detail = ""
            logger.warning("ElevenLabs STT HTTP error status=%s body=%s", exc.code, detail[:400])
            voice_trace_error("stt.http", f"provider=elevenlabs status={exc.code} body={detail[:200]}")
            raise RuntimeError(_format_elevenlabs_stt_error(exc.code, detail)) from exc
        except Exception as exc:
            logger.warning("ElevenLabs STT request failed: %s", exc, exc_info=True)
            voice_trace_error("stt.http", f"provider=elevenlabs err={type(exc).__name__}: {exc}")
            raise RuntimeError("ElevenLabs STT failed") from exc

        text = str(payload.get("text") or payload.get("transcript") or "").strip()
        if not text and isinstance(payload.get("words"), list):
            text = "".join(str(w.get("text", "")) for w in payload["words"]).strip()
        return text

    def _transcribe_openai(self, wav_bytes: bytes, *, prompt: str = "") -> str:
        api_key = self._resolve_api_key()
        if not api_key:
            raise RuntimeError("Missing OPENAI_API_KEY for voice STT")

        from openai import OpenAI

        client = OpenAI(api_key=api_key, timeout=self._config.timeout_seconds)
        file_obj = io.BytesIO(wav_bytes)
        file_obj.name = "utterance.wav"
        model = self._config.model or "whisper-1"
        kwargs: dict = {
            "model": model,
            "file": file_obj,
            "language": self._config.language or None,
        }
        if prompt.strip():
            kwargs["prompt"] = prompt.strip()
        try:
            result = client.audio.transcriptions.create(**kwargs)
        except Exception as exc:
            logger.warning("OpenAI STT request failed: %s", exc, exc_info=True)
            raise RuntimeError(_format_openai_stt_error(exc)) from exc
        return (getattr(result, "text", "") or "").strip()


def _format_elevenlabs_stt_error(status: int, detail: str) -> str:
    body = (detail or "").lower()
    if status == 401 and "speech_to_text" in body:
        return (
            "ElevenLabs API Key 缺少 speech_to_text 权限（Scribe 语音识别）。"
            "请改用 NEURALPAL_VOICE_STT_PROVIDER=local（本地免费）或 openai。"
        )
    if status == 401:
        return "ElevenLabs STT 鉴权失败（HTTP 401），请检查 ELEVENLABS_API_KEY。"
    return f"ElevenLabs STT failed: HTTP {status}"


def _format_openai_stt_error(exc: Exception) -> str:
    msg = str(exc).lower()
    if "insufficient_quota" in msg or "exceeded your current quota" in msg:
        return (
            "OpenAI 账户配额/余额不足，Whisper 不可用。"
            "请充值 OpenAI，或在 .env 设置 NEURALPAL_VOICE_STT_PROVIDER=local 使用本地识别。"
        )
    if "invalid_api_key" in msg or "incorrect api key" in msg:
        return "OpenAI API Key 无效，请检查 .env 中的 OPENAI_API_KEY。"
    return f"OpenAI STT 失败：{exc}"
