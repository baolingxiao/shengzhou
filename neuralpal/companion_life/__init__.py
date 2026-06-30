# -*- coding: utf-8 -*-
"""数字伴侣生活引擎 Companion Life Engine。"""

from neuralpal.companion_life.companion_life_service import (
    CompanionLifeService,
    get_companion_life_service,
)
from neuralpal.companion_life.config import is_companion_life_enabled

__all__ = [
    "CompanionLifeService",
    "get_companion_life_service",
    "is_companion_life_enabled",
]
