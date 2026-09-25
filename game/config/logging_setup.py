# -*- coding: utf-8 -*-
"""日志系统初始化。

设计要点
--------
1. 每次启动一个独立 log 文件：userdata/logs/app_YYYYMMDD_HHMMSS.log
2. 只挂 FileHandler（DEBUG），控制台无输出。
3. 启动时清理旧文件，只保留最近 N 个。
4. 每行日志带 session id 前缀，方便区分多次启动。
5. 提供两个全局异常钩子：
   - install_sys_excepthook()      捕获所有未捕获异常
   - install_tk_excepthook(root)   捕获 tkinter 回调异常（最关键的一处）
"""

import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path

from game.config.constants import LOG_DIR, LOG_ENABLED

# 保留最近多少个 log 文件
_MAX_LOG_FILES = 30

# 当前会话 id（8 位十六进制）
_SESSION_ID = uuid.uuid4().hex[:8]

# 记录初始化后生成的日志文件路径，供退出时打印 / 状态栏提示
_LOG_FILE_PATH: Path | None = None


class _SessionFilter(logging.Filter):
    """给每条 record 注入 session id。"""

    def filter(self, record):
        record.session = _SESSION_ID
        return True


def get_session_id() -> str:
    return _SESSION_ID


def get_log_file_path() -> Path | None:
    return _LOG_FILE_PATH


def setup_logging() -> Path:
    """初始化日志系统。返回本次会话的 log 文件路径。"""
    global _LOG_FILE_PATH

    if not LOG_ENABLED:
        # 编译期一键关闭：禁用所有日志调用，不建目录、不清理旧文件、不挂 handler。
        logging.disable(logging.CRITICAL)
        _LOG_FILE_PATH = None
        return None

    root = logging.getLogger()
    # 重复初始化保护：清空已有 handler
    for h in list(root.handlers):
        root.removeHandler(h)

    root.setLevel(logging.DEBUG)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _cleanup_old_logs(LOG_DIR)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"app_{ts}.log"
    _LOG_FILE_PATH = log_path

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s.%(msecs)03d [%(levelname)-5s] "
        "[%(session)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(fmt)
    handler.addFilter(_SessionFilter())
    root.addHandler(handler)

    logging.getLogger(__name__).info(
        "日志系统就绪：%s  session=%s", log_path, _SESSION_ID
    )
    return log_path


def _cleanup_old_logs(log_dir: Path):
    """删除最旧的 log 文件，只保留最近 _MAX_LOG_FILES 个。"""
    try:
        files = sorted(
            log_dir.glob("app_*.log"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in files[_MAX_LOG_FILES:]:
            try:
                old.unlink()
            except OSError:
                pass
    except Exception:
        # 清理失败不影响启动
        pass


def install_sys_excepthook():
    """安装 sys.excepthook：任何未捕获异常写入日志。"""
    if not LOG_ENABLED:
        return   # 不接管，交回 Python 默认 stderr
    def _hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logging.getLogger("sys.excepthook").critical(
            "未捕获异常", exc_info=(exc_type, exc_value, exc_tb)
        )
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook


def install_tk_excepthook(root):
    """覆盖 Tk.report_callback_exception，捕获 tkinter 回调异常。

    这是 tkinter 项目最容易漏日志的地方：回调里抛异常默认只打到 stderr，
    窗口继续运行但行为异常。这里统一写入日志。
    """
    if not LOG_ENABLED:
        return   # 不接管，交回 Tk 默认 stderr
    def _report(exc_type, exc_value, exc_tb):
        logging.getLogger("tk.callback").error(
            "tkinter 回调异常", exc_info=(exc_type, exc_value, exc_tb)
        )

    root.report_callback_exception = _report
