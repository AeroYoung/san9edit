# -*- coding: utf-8 -*-
"""常量与路径。

PROJECT_ROOT 通过 __file__ 定位，从任何目录启动都能找到 assets/。
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
DEFAULT_MAP_PATH = ASSETS_DIR / "map.geojson"
DEFAULT_WATER_PATH = ASSETS_DIR / "water.geojson"
DEFAULT_ROADS_PATH = ASSETS_DIR / "roads.geojson"
DEFAULT_CHARACTERS_PATH = ASSETS_DIR / "characters.json"      # ★ 新增

# 剧本目录（与 assets/ 并列）
SCENARIOS_DIR = PROJECT_ROOT / "scenarios"
DEFAULT_SCENARIO_PATH = SCENARIOS_DIR / "default.json"

APP_TITLE = "暗耻三国志"
WINDOW_SIZE = "1440x900"
MIN_WINDOW_SIZE = (1024, 640)

# ============================================================
# 应用模式
# ============================================================
MODE_EDIT = "edit"     # 剧本编辑模式
MODE_GAME = "game"     # 游戏模式（本轮不实现）
APP_MODE = MODE_EDIT   # 全局开关：编译期切换

# ============================================================
# 日志
# ============================================================
LOG_DIR = PROJECT_ROOT / "userdata" / "logs"
LOG_ENABLED = True   # False = 一键关闭全部日志（不建目录、不写文件、不装异常钩子）