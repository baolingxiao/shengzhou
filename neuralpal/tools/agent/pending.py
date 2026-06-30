# -*- coding: utf-8 -*-
"""会话级 pending action 持久化。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from neuralpal.config import get_settings
from neuralpal.tools.agent.models import ActionProposal

logger = logging.getLogger(__name__)


def _state_dir() -> Path:
    s = get_settings()
    root = s.agent_state_dir
    root.mkdir(parents=True, exist_ok=True)
    return root


def _path_for_session(session_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id.strip())[:120]
    safe = safe or "default"
    return _state_dir() / f"{safe}_pending.json"


def load_pending(session_id: str) -> ActionProposal | None:
    path = _path_for_session(session_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        proposal = ActionProposal.from_dict(data)
        if proposal.is_expired():
            clear_pending(session_id)
            return None
        return proposal
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("load_pending failed session=%s: %s", session_id, exc)
        return None


def save_pending(proposal: ActionProposal) -> None:
    path = _path_for_session(proposal.session_id)
    try:
        path.write_text(
            json.dumps(proposal.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        logger.error("save_pending failed: %s", exc)
        raise


def clear_pending(session_id: str) -> None:
    path = _path_for_session(session_id)
    try:
        if path.is_file():
            path.unlink()
    except OSError as exc:
        logger.warning("clear_pending failed session=%s: %s", session_id, exc)
