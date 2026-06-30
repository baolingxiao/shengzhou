from __future__ import annotations

import hashlib
from pathlib import Path


class DiskAudioCache:
    """Simple file cache for synthesized audio bytes."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def build_key(self, *parts: str) -> str:
        digest = hashlib.sha256()
        for part in parts:
            digest.update((part or "").encode("utf-8"))
            digest.update(b"\x00")
        return digest.hexdigest()

    def get(self, key: str, suffix: str = ".mp3") -> bytes | None:
        path = self.root / f"{key}{suffix}"
        if not path.is_file():
            return None
        return path.read_bytes()

    def get_path(self, key: str, suffix: str = ".mp3") -> Path | None:
        path = self.root / f"{key}{suffix}"
        return path if path.is_file() else None

    def put(self, key: str, data: bytes, suffix: str = ".mp3") -> Path:
        path = self.root / f"{key}{suffix}"
        path.write_bytes(data)
        return path
