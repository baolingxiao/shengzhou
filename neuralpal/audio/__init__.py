from .cache import DiskAudioCache
from .elevenlabs_adapter import ElevenLabsConfig, ElevenLabsTTSAdapter
from .stt_adapter import SttAdapter, SttConfig
from .text_chunker import TextChunker

__all__ = [
    "ElevenLabsConfig",
    "ElevenLabsTTSAdapter",
    "DiskAudioCache",
    "TextChunker",
    "MicCapture",
    "SttAdapter",
    "SttConfig",
    "VoiceDialogConfig",
    "VoiceDialogController",
]


def __getattr__(name: str):
    if name == "MicCapture":
        from .mic_capture import MicCapture

        return MicCapture
    if name in ("VoiceDialogConfig", "VoiceDialogController"):
        from .voice_dialog_controller import VoiceDialogConfig, VoiceDialogController

        if name == "VoiceDialogConfig":
            return VoiceDialogConfig
        return VoiceDialogController
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
