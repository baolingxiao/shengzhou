# -*- coding: utf-8 -*-
"""从 LangChain ChatModel 提取 provider / model / 参数（用于 Trace）。"""

from __future__ import annotations

from typing import Any

from neuralpal.llm.llm_router import get_active_provider
from neuralpal.trace.sanitize import sanitize_dict


def extract_llm_info(llm: Any) -> tuple[str, str, dict[str, Any]]:
    provider = get_active_provider()
    model = (
        getattr(llm, "model_name", None)
        or getattr(llm, "model", None)
        or getattr(llm, "model_id", None)
        or ""
    )
    params: dict[str, Any] = {}
    for attr in ("temperature", "max_tokens", "top_p", "timeout"):
        if hasattr(llm, attr):
            val = getattr(llm, attr)
            if val is not None:
                params[attr] = val
    return provider, str(model), sanitize_dict(params)
