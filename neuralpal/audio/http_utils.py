# -*- coding: utf-8 -*-
"""HTTPS 请求工具（macOS Python 需 certifi 根证书）。"""

from __future__ import annotations

import ssl
from typing import Any
from urllib import request


def ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def urlopen(req: request.Request, *, timeout: float | None = None) -> Any:
    return request.urlopen(req, timeout=timeout, context=ssl_context())
