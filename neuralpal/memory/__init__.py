"""
neuralpal.memory 包。

``memory_system`` 会反向依赖 ``llm_router``，海马体编排相关符号采用延迟加载（``__getattr__``）。
"""

from __future__ import annotations

import importlib
from typing import Any, Final

from neuralpal.memory.memory_maintenance import MemoryMaintenanceService
from neuralpal.memory.rules_layer import RulesLayer
from neuralpal.memory.transient import TransientBuffer

__all__ = [
    "RulesLayer",
    "TransientBuffer",
    "MemoryMaintenanceService",
    "NeuralPalMemoryPalaceOrchestrator",
    "MemoryChatTurnResult",
    "LongTermMemoryEngine",
    "ensure_knowledge_palace_layout",
    "sync_rules_backup_to_palace",
]

_LAZY_EXPORTS: Final[dict[str, tuple[str, str]]] = {
    "LongTermMemoryEngine": ("neuralpal.memory.memory_system", "LongTermMemoryEngine"),
    "MemoryChatTurnResult": ("neuralpal.memory.memory_system", "MemoryChatTurnResult"),
    "NeuralPalMemoryPalaceOrchestrator": (
        "neuralpal.memory.memory_system",
        "NeuralPalMemoryPalaceOrchestrator",
    ),
    "ensure_knowledge_palace_layout": (
        "neuralpal.memory.memory_system",
        "ensure_knowledge_palace_layout",
    ),
    "sync_rules_backup_to_palace": (
        "neuralpal.memory.memory_system",
        "sync_rules_backup_to_palace",
    ),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_EXPORTS:
        mod_path, attr = _LAZY_EXPORTS[name]
        mod = importlib.import_module(mod_path)
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__))
