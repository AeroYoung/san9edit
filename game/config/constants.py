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

APP_TITLE = "暗耻三国志"
WINDOW_SIZE = "1440x900"
MIN_WINDOW_SIZE = (1024, 640)

# 初始游戏状态
INITIAL_YEAR = 208
INITIAL_MONTH = 1
INITIAL_XUN = 1                 # 1=上旬 2=中旬 3=下旬
INITIAL_FACTION = "刘备"
INITIAL_PRESTIGE = 1000
INITIAL_GOLD = 5000
INITIAL_FOOD = 20000