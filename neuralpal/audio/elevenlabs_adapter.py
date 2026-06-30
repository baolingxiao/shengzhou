from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from urllib import error, parse, request

from neuralpal.audio.http_utils import urlopen as ssl_urlopen


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ElevenLabsConfig:
    api_key: str
    voice_id: str
    model_id: str = "eleven_multilingual_v2"
    api_url: str = "https://api.elevenlabs.io/v1/text-to-speech"
    output_format: str = "mp3_44100_128"
    stability: float = 0.35
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True
    speed: float = 1.15
    timeout_seconds: int = 35


class ElevenLabsTTSAdapter:
    """Minimal ElevenLabs TTS HTTP client."""

    def __init__(self, config: ElevenLabsConfig) -> None:
        self._config = config

    def synthesize(self, transcript: str) -> bytes:
        text = (transcript or "").strip()
        if not text:
            raise ValueError("Transcript is empty")
        cfg = self._config
        if not cfg.api_key:
            raise RuntimeError("Missing ElevenLabs API key")
        if not cfg.voice_id:
            raise RuntimeError("Missing ElevenLabs voice id")

        query = parse.urlencode({"output_format": cfg.output_format})
        url = f"{cfg.api_url.rstrip('/')}/{cfg.voice_id}?{query}"
        payload = {
            "text": text,
            "model_id": cfg.model_id,
            "voice_settings": {
                "stability": cfg.stability,
                "similarity_boost": cfg.similarity_boost,
                "style": cfg.style,
                "use_speaker_boost": cfg.use_speaker_boost,
                "speed": cfg.speed,
            },
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "xi-api-key": cfg.api_key,
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
            },
        )
        try:
            with ssl_urlopen(req, timeout=cfg.timeout_seconds) as resp:
                return resp.read()
        except error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="ignore")
            except Exception:
                detail = ""
            logger.warning("ElevenLabs HTTP error status=%s body=%s", exc.code, detail[:400])
            raise RuntimeError(f"ElevenLabs request failed: HTTP {exc.code}") from exc
        except Exception as exc:
            logger.warning("ElevenLabs request failed: %s", exc, exc_info=True)
            if "CERTIFICATE_VERIFY_FAILED" in str(exc):
                raise RuntimeError(
                    "ElevenLabs HTTPS 证书校验失败。"
                    "请确认已安装 certifi（pip install certifi）并重启后端。"
                ) from exc
            raise RuntimeError("ElevenLabs request failed") from exc
