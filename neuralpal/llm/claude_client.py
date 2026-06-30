from __future__ import annotations

from anthropic import Anthropic

from neuralpal.config import get_settings


def get_anthropic_client() -> Anthropic:
    """Anthropic 官方 SDK 客户端；密钥来自 ANTHROPIC_API_KEY。"""
    key = get_settings().anthropic_api_key
    return Anthropic(api_key=key or None)
