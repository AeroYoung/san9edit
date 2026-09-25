# -*- coding: utf-8 -*-
"""启动入口。"""

import logging

from game.config.logging_setup import setup_logging, install_sys_excepthook
from game.ui.main_window import MainWindow


def main():
    log_path = setup_logging()
    install_sys_excepthook()
    logging.getLogger(__name__).info("应用启动，日志文件：%s", log_path)
    MainWindow().run()


if __name__ == "__main__":
    main()
