# -*- coding: utf-8 -*-
"""日志系统初始化（主游戏侧兼容薄壳）。

实现已迁到项目根 `shared/logging_setup.py`（跨模块单一定义源）。
本模块只做**显式** re-export，保持既有 import 路径可用，行为不变。
"""

from shared.logging_setup import (
    get_session_id,
    get_log_file_path,
    setup_logging,
    install_sys_excepthook,
    install_tk_excepthook,
)

__all__ = [
    "get_session_id",
    "get_log_file_path",
    "setup_logging",
    "install_sys_excepthook",
    "install_tk_excepthook",
]
