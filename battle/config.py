# -*- coding: utf-8 -*-
"""战斗模块结构配置常量（窗口 / tick / 路径 / 颜色）。

- 路径一律以 `battle/` 为基准由 `__file__` 反推，**不用 cwd**。
- 数值平衡参数不在本模块，见 `balance.py`。
"""

from pathlib import Path

# battle/config.py → battle/
BATTLE_ROOT = Path(__file__).resolve().parent

# ============================================================
# 窗口
# ============================================================
WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 1300
WINDOW_TITLE = "兵棋作战"

# ============================================================
# 帧率与 tick
# ============================================================
FPS = 60            # 渲染帧率
TICK_MS = 100       # 每 tick 毫秒（步骤01 只写常量，不驱动模拟）
SPEED_PRESETS = {1: 100, 2: 50, 4: 25}   # 速度档位（步骤01 只写常量）

# ============================================================
# 地图与六宫格
# ============================================================
HEX_SIZE = 28       # 外接圆半径（像素）；地图 JSON 有值时以 JSON 为准
MAP_PATH = BATTLE_ROOT / "assets" / "maps" / "default.json"
FONT_PATH = BATTLE_ROOT / "assets" / "fonts" / "NotoSansSC-Regular.otf"  # 步骤01 只写常量，不加载

# 缩放上限：单格边长（外接圆半径）到 200 像素
ZOOM_MAX_HEX_EDGE_PX = 200.0
# 滚轮单格缩放倍率
ZOOM_STEP = 1.1

# ---- 静态层绘制策略 ----
# 视口外扩缓存：静态层 Surface 四周各多画这么多像素，平移在此范围内不重建
CACHE_MARGIN_PX = 256
# 视口内格数超过此值时，降级为「整块填充 + 地图外框」（不再逐格描线）
# 取值依据：20000 格对应的格距约 13 px —— 再小下去格线已糊成一片；
# 切换点的一次性重建实测约 103 ms，之后整段最远缩放均降为 O(1)。
SOLID_FILL_CELL_LIMIT = 20000

# ============================================================
# 颜色（RGB）
# ============================================================
COLOR_BG = (20, 22, 26)             # 窗口背景
COLOR_VIEWPORT_MARGIN = (38, 42, 48)  # 视口内、地图包围盒之外的底色
COLOR_HEX_FILL = (222, 226, 214)    # 六宫格填充
COLOR_HEX_LINE = (110, 118, 106)    # 六宫格描边

# ============================================================
# 阵营与兵棋符号
# ============================================================
PLAYER_SIDE = "red"                 # 玩家方；框选 / 选中只对它生效
SIDE_COLOR = {                      # 阵营框色
    "red": (196, 60, 60),
    "blue": (60, 96, 196),
}
SYMBOL_LINE_WIDTH = 2               # 符号描边线宽（屏幕像素，不随 zoom 变）
SYMBOL_FILL_ALPHA = 220             # 实心区填充 alpha（0–255）
SYMBOL_FONT_SIZE_MIN = 11           # 兵种小字字号下限（远侧）
SYMBOL_FONT_SIZE_MAX = 16           # 兵种小字字号上限（近侧）
SYMBOL_TROOP_FONT_MIN = 10          # 兵力数字字号下限
SYMBOL_TROOP_FONT_MAX = 14          # 兵力数字字号上限
LOD_FAR_MAX_PX = 12                 # 格边长 < 此值 → 远 LOD
LOD_NEAR_MIN_PX = 28                # 格边长 ≥ 此值 → 近 LOD；居中 = 中 LOD

# 初始缩放：让屏幕上的格边长正好落在 LOD_NEAR_MIN_PX 上 —— 开局即「近」LOD，
# 符号下方直接看得到兵力数字。水平进阶 = 1.5 × HEX_SIZE × zoom，
# 故取 LOD_NEAR_MIN_PX × 1.5；改 LOD_NEAR_MIN_PX 时初始缩放自动跟随。
INITIAL_HEX_STEP_PX = 1.5 * LOD_NEAR_MIN_PX
LOD_FAR_COLOR = SIDE_COLOR          # 远 LOD 小色块取阵营色
LOD_FAR_SIZE_PX = 6                 # 远 LOD 小色块边长（屏幕像素）
SELECT_HIGHLIGHT_COLOR = (255, 220, 60)   # 选中高亮描边
SELECT_HIGHLIGHT_WIDTH = 3
SELECT_BOX_COLOR = (255, 220, 60, 80)     # 框选虚线框填充（半透明）

# ============================================================
# UI 字号（★ 全部 UI 字号只在这里定义，调用方从 config 取，不写字面量）
# ============================================================
FONT_SIZE_PANEL_TAB = 16        # 面板 Tab 标题
FONT_SIZE_PANEL_HEADER = 16     # 面板表头
FONT_SIZE_PANEL_CELL = 16       # 面板单元格 / 组头
FONT_SIZE_UNIT_INFO = 16        # 部队情报组（标签 + 值同号）
FONT_SIZE_CONSOLE = 18          # 控制台按钮与文字
FONT_SIZE_MINIMAP = 14          # 小地图标注

# ============================================================
# 右侧面板组
# ============================================================
PANEL_WIDTH = 420
PANEL_MARGIN = 20
PANEL_BG_COLOR = (28, 32, 40, 220)        # 面板底板（RGBA 半透明）
PANEL_BORDER_COLOR = (90, 100, 120)
PANEL_CORNER_RADIUS = 8
PANEL_TAB_HEIGHT = 36
PANEL_TAB_TITLES = ("我方部队", "敌方部队", "面板3", "面板4")
PANEL_TAB_SIDES = ("red", "blue", None, None)   # 与 PANEL_TAB_TITLES 一一对应
PANEL_ROW_ALT_BG = (36, 41, 51)           # 隔行 / 选中行底色
PANEL_ROW_HOVER_BG = (52, 60, 74)         # 悬停行底色
PANEL_ROW_SELECTED_BG = (64, 58, 32)      # 选中行底色（偏金，配合选中描边色）

# 部队情报组（面板内容区下 1/4）
UNIT_INFO_HEIGHT_RATIO = 0.25
UNIT_INFO_MIN_HEIGHT = 160
# 字段顺序表：(标签, 取值 key)。★ Unit 增删字段时必须同步更新这里。
UNIT_INFO_FIELDS = (
    ("编号", "id"),
    ("阵营", "side"),
    ("兵种", "name"),
    ("坐标", "offset"),
    ("兵力", "troops"),
    ("士气", "morale"),
    ("体力", "stamina"),
    ("状态", "status"),
    ("当前命令", "command"),
)

# ============================================================
# 底部控制台
# ============================================================
CONSOLE_HEIGHT = 120
CONSOLE_MARGIN = 20
CONSOLE_BG_COLOR = PANEL_BG_COLOR
CONSOLE_PLAY_BTN_SIZE = (160, 80)         # 进行 / 暂停按钮（宽, 高）
CONSOLE_PLAY_BG = (46, 132, 74)           # 进行（绿）
CONSOLE_PLAY_HOVER_BG = (58, 158, 90)
CONSOLE_PAUSE_BG = (158, 54, 54)          # 暂停（红）
CONSOLE_PAUSE_HOVER_BG = (186, 70, 70)
CONSOLE_CMD_BTN_SIZE = (96, 44)           # 命令按钮（宽, 高）
CONSOLE_CMD_BTN_GAP = 8                   # 命令按钮间距
CONSOLE_CMD_ROWS = 2                      # 命令按钮组行数
CONSOLE_CMD_LABELS = ("移动", "攻击", "待命", "撤退", "停止")

# ============================================================
# 小地图（宽度不设常量，由高度 × cols / rows 现算）
# ============================================================
MINIMAP_HEIGHT = 140
MINIMAP_MARGIN = 8                  # 与控制台之间的水平间隙
MINIMAP_BG_COLOR = (18, 20, 24, 235)
MINIMAP_BORDER_COLOR = (90, 100, 120)
MINIMAP_MAP_FILL = (52, 58, 68)
MINIMAP_MAP_LINE = (110, 118, 128)
MINIMAP_VIEWPORT_LINE = (255, 220, 60)
MINIMAP_UNIT_RADIUS = 1
MINIMAP_PAD = 6                     # 地图范围距小地图内边缘的留白

# ============================================================
# 窗口图标（几何绘制，不读外部文件）
# ============================================================
APP_ICON_SIZE = 32
APP_ICON_BG = (28, 32, 40)
APP_ICON_FG = (255, 220, 60)

UI_FONT_PATH = FONT_PATH            # 面板 / 控制台 / 小地图字体

UNIT_DATA_PATHS = {                 # 双方部队数据（以 battle/ 为基准反推）
    "red": BATTLE_ROOT / "data" / "side_red.json",
    "blue": BATTLE_ROOT / "data" / "side_blue.json",
}

# ============================================================
# 其他
# ============================================================
RANDOM_SEED = None  # 供后续战斗复现使用
DEBUG = False       # 调试总开关
