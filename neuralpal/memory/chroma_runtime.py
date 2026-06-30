# -*- coding: utf-8 -*-
"""Shared Chroma runtime utilities.

Goal:
- Reuse one chromadb client per persist path to avoid noisy
  "An instance of Chroma already exists ... with different settings".
- Keep telemetry disabled by default for cleaner ops logs.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import chromadb
from chromadb.config import Settings

_CLIENTS: Dict[str, chromadb.ClientAPI] = {}


def get_chroma_client(persist_path: str | Path) -> chromadb.ClientAPI:
    key = str(Path(persist_path).resolve())
    if key in _CLIENTS:
        return _CLIENTS[key]

    # Keep behavior stable and quiet in server logs.
    os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
    settings = Settings(anonymized_telemetry=False)
    client = chromadb.PersistentClient(path=key, settings=settings)
    _CLIENTS[key] = client
    return client

