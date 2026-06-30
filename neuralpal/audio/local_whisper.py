# -*- coding: utf-8 -*-
"""本地 Whisper STT（faster-whisper，无需 API Key）。"""

from __future__ import annotations

import logging
import os
import tempfile
import threading
from typing import Any

from neuralpal.audio.voice_trace import voice_trace, voice_trace_error

logger = logging.getLogger(__name__)

_model_lock = threading.Lock()
_model: Any = None
_model_name = ""


def local_whisper_available() -> bool:
    try:
        import faster_whisper  # noqa: F401

        return True
    except ImportError:
        return False


def local_whisper_unavailable_reason() -> str:
    if local_whisper_available():
        return ""
    return "未安装 faster-whisper，请运行: pip install faster-whisper"


def _load_model(model_size: str) -> Any:
    global _model, _model_name
    from faster_whisper import WhisperModel

    if _model is not None and _model_name == model_size:
        return _model
    voice_trace("stt.local.load", f"model={model_size} device=cpu compute=int8")
    _model = WhisperModel(model_size, device="cpu", compute_type="int8")
    _model_name = model_size
    voice_trace("stt.local.ready", f"model={model_size}")
    return _model


def transcribe_wav_bytes(
    wav_bytes: bytes,
    *,
    model_size: str = "base",
    language: str = "zh",
    initial_prompt: str = "",
) -> str:
    if not wav_bytes:
        return ""
    if not local_whisper_available():
        raise RuntimeError(local_whisper_unavailable_reason())

    with _model_lock:
        model = _load_model(model_size or "base")

    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_bytes)
            tmp_path = tmp.name
        segments, _info = model.transcribe(
            tmp_path,
            language=(language or None),
            beam_size=1,
            vad_filter=True,
            initial_prompt=(initial_prompt.strip() or None),
        )
        text = "".join(segment.text for segment in segments).strip()
        return text
    except Exception as exc:
        logger.warning("Local Whisper STT failed: %s", exc, exc_info=True)
        voice_trace_error("stt.local", str(exc))
        raise RuntimeError(f"本地 Whisper 识别失败：{type(exc).__name__}") from exc
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
