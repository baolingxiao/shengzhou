"""系统服务：权限、更新。"""

from neuralpal.system.app_update import (
    apply_git_update,
    check_git_update,
    dismiss_update,
    get_app_version_info,
)
from neuralpal.system.permissions import get_permissions_snapshot, open_system_settings

__all__ = [
    "apply_git_update",
    "check_git_update",
    "dismiss_update",
    "get_app_version_info",
    "get_permissions_snapshot",
    "open_system_settings",
]
