# -*- coding: utf-8 -*-
"""战斗模块单独运行入口。

启动方式（两种等价）：
    python -m battle              # 从项目根
    python battle/__main__.py     # 任意 cwd

启动顺序：路径自举 → 日志初始化 → 系统异常钩子 → `app.run()`（pygame 初始化 + 主循环）。
"""

import logging
import sys
from pathlib import Path

_FALLBACK_FORMAT = (
    "%(asctime)s.%(msecs)03d [%(levelname)-5s] [battle] %(name)s: %(message)s"
)

def _bootstrap_path():
    """把项目根（`shared/` 与 `battle/` 的父目录）加入 sys.path。

    `python -m battle` 从项目根启动时根已在 sys.path 上；用脚本方式启动
    （`python battle/__main__.py`）时 `sys.path[0]` 是 `battle/`，
    必须自己补上，否则 `shared` 与 `battle` 都 import 不到。
    """
    root = str(Path(__file__).resolve().parent.parent)
    if root not in sys.path:
        sys.path.insert(0, root)


def _init_logging():
    """接入 shared 日志系统；不可用时降级为标准 logging（不静默吞异常）。

    返回本次会话的日志文件路径；降级时返回 None。
    """
    try:
        from shared.logging_setup import setup_logging, install_sys_excepthook
    except Exception:
        logging.basicConfig(
            level=logging.DEBUG,
            format=_FALLBACK_FORMAT,
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        logging.getLogger("battle.__main__").warning(
            "shared.logging_setup 不可 import，降级为标准 logging", exc_info=True
        )
        return None
    log_path = setup_logging()
    install_sys_excepthook()
    return log_path


def main() -> int:
    _bootstrap_path()
    log_path = _init_logging()
    logging.getLogger("battle.__main__").info("battle 启动，日志文件：%s", log_path)
    from battle.app import run
    return run()


if __name__ == "__main__":
    sys.exit(main())
