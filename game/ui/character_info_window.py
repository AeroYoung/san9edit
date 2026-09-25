# -*- coding: utf-8 -*-
"""人物情报窗口。

内容：头像 + 五维雷达图 + 关系 + 生平（占位）。

头像路径约定：assets/portrait/{id}-{name}.{ext}
    例如 0651-张南.jpg
不再读取 Character.portrait 字段。

雷达图用 tkinter Canvas 绘制（不依赖 Pillow），
中文轴标签直接写，避免 Pillow 找不到字体文件的问题。
"""

import logging
import math
import tkinter as tk

from game.config import constants as C
from game.config.style import THEME, FONT_SIZES
from game.core.utils import darken_color, lighten_color
from game.ui.window_utils import center_on_parent

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageTk
    _PIL_OK = True
except ImportError:
    _PIL_OK = False
    logger.warning("未安装 Pillow，人物情报窗口无法显示头像")


PORTRAIT_DIR = C.ASSETS_DIR / "portrait"
PORTRAIT_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")

MAX_W = 200
MAX_H = 200

# 窗口宽度固定；高度自适应（内容撑多少算多少，最小 640）
WIN_W = 600
WIN_MIN_H = 640

# 雷达图
RADAR_SIZE = 340                # Canvas 边长
RADAR_CENTER = RADAR_SIZE / 2
RADAR_RADIUS = 130              # 顶点半径
RADAR_GRID_RINGS = 5            # 同心层数（对应 20/40/60/80/100）
RADAR_MAX = 100                 # 轴上限（>100 截断到 100 画）
RADAR_LABEL_GAP = 18            # 顶点到标签的额外间距（像素）
RADAR_NUM_GAP = 14              # 标签到数值的间距（像素）
RADAR_DOT_R = 3                 # 数据顶点小圆半径

# 顺序：正上 → 右上 → 右下 → 左下 → 左上（顺时针）
RADAR_AXES = (
    ("统", "leadership"),
    ("武", "might"),
    ("智", "intelligence"),
    ("政", "politics"),
    ("魅", "charisma"),
)

# 配色
LINK_COLOR = "#1F6FBF"          # 可点姓名的蓝色
BODY_FG = "#333333"
NUM_FG = "#666666"
BIO_FG = "#888888"
MUTED_COLOR = "#999999"         # 灰：占位 / 未命中
NO_FACTION_COLOR = "#7F8C8D"    # 无势力时的雷达填充色
NO_FACTION_EDGE = "#5D6D7E"     # 无势力时的雷达描边色


class CharacterInfoWindow(tk.Toplevel):
    def __init__(self, master, character, world=None, font_family="TkDefaultFont"):
        super().__init__(master)
        self.character = character
        self.world = world
        self.font_family = font_family
        self._photo = None    # ★ 保引用，防 GC
        # 主窗口引用（用于居中基准 / 跳转窗口的 master）
        self._top = master.winfo_toplevel()

        logger.debug("打开人物情报窗口：%s", character.id)
        # 未登场人物的标题追加状态；其余显示（雷达图 / 关系区）不受 appeared 影响
        title = f"{character.display_name()} — 人物情报"
        if not getattr(character, "appeared", True):
            title += "（未登场）"
        self.title(title)
        self.transient(master)
        self.configure(bg=THEME["panel_bg"])
        self.resizable(False, True)

        self._build_ui()
        self._load_portrait()

        # 尺寸确定后再居中（对游戏主窗口居中）
        self.update_idletasks()
        w = WIN_W
        h = max(self.winfo_reqheight(), WIN_MIN_H)
        center_on_parent(self, self._top, w, h)

        try:
            self.grab_set()
        except Exception:
            pass
        self.bind("<Escape>", lambda e: self.destroy())
        self.focus_set()

    # ============================================================
    # UI 组装
    # ============================================================
    def _build_ui(self):
        # 名字
        tk.Label(
            self, text=self.character.display_name(),
            bg=THEME["panel_bg"], fg="#222222",
            font=(self.font_family, FONT_SIZES["panel_title"] + 4, "bold"),
        ).pack(pady=(14, 6))

        # 上区：头像 + 雷达图
        top = tk.Frame(self, bg=THEME["panel_bg"])
        top.pack(padx=16, pady=4, fill="x")
        self._build_portrait(top)
        self._build_radar(top)

        # 分隔线
        tk.Frame(self, bg=THEME["status_sep"], height=1).pack(
            fill="x", padx=16, pady=(10, 0))

        # 关系区
        self._build_relations(self)

        # 分隔线
        tk.Frame(self, bg=THEME["status_sep"], height=1).pack(
            fill="x", padx=16, pady=(10, 0))

        # 生平区
        self._build_bio(self)

    # ------------------------------------------------------------
    def _build_portrait(self, parent):
        frame = tk.Frame(
            parent, bg=THEME["panel_header_bg"],
            width=MAX_W, height=MAX_H,
            highlightthickness=1,
            highlightbackground=THEME["status_sep"],
        )
        frame.pack(side="left", padx=(0, 16))
        frame.pack_propagate(False)

        self._portrait_label = tk.Label(
            frame, bg=THEME["panel_header_bg"],
        )
        self._portrait_label.pack(expand=True, fill="both")

    # ------------------------------------------------------------
    def _build_radar(self, parent):
        canvas = tk.Canvas(
            parent, width=RADAR_SIZE, height=RADAR_SIZE,
            bg=THEME["panel_bg"], highlightthickness=0,
        )
        canvas.pack(side="left")
        self._radar_canvas = canvas

        outer_pts = self._axis_points()

        # 1) 同心网格五边形（5 层）
        for i in range(1, RADAR_GRID_RINGS + 1):
            r = RADAR_RADIUS * i / RADAR_GRID_RINGS
            ring = [
                (RADAR_CENTER + r * math.cos(a),
                 RADAR_CENTER + r * math.sin(a))
                for a in self._axis_angles()
            ]
            flat = [c for p in ring for c in p]
            canvas.create_polygon(
                *flat, fill="", outline=THEME["status_sep"], width=1,
            )

        # 2) 轴线
        for x, y in outer_pts:
            canvas.create_line(
                RADAR_CENTER, RADAR_CENTER, x, y,
                fill=lighten_color(THEME["status_sep"], 0.5),
                width=1,
            )

        # 3) 数据多边形
        self._draw_data_polygon(canvas)

        # 4) 轴标签 + 数值
        for (label, attr), (x, y) in zip(RADAR_AXES, outer_pts):
            dx = x - RADAR_CENTER
            dy = y - RADAR_CENTER
            norm = math.hypot(dx, dy) or 1.0
            lx = x + dx / norm * RADAR_LABEL_GAP
            ly = y + dy / norm * RADAR_LABEL_GAP

            canvas.create_text(
                lx, ly, text=label,
                fill=BODY_FG,
                font=(self.font_family, FONT_SIZES["panel_title"], "bold"),
            )
            value = getattr(self.character, attr, 0) or 0
            canvas.create_text(
                lx, ly + RADAR_NUM_GAP, text=str(value),
                fill=NUM_FG,
                font=(self.font_family, FONT_SIZES["panel_body"]),
            )

    # ------------------------------------------------------------
    def _axis_angles(self):
        """返回 5 个轴的角度（弧度）。从正上方开始，顺时针。"""
        return [-math.pi / 2 + i * (2 * math.pi / 5) for i in range(5)]

    def _axis_points(self):
        """返回 5 个最外层顶点坐标（半径 = RADAR_RADIUS）。"""
        return [
            (RADAR_CENTER + RADAR_RADIUS * math.cos(a),
             RADAR_CENTER + RADAR_RADIUS * math.sin(a))
            for a in self._axis_angles()
        ]

    def _fill_and_edge(self):
        """雷达图数据色：人物所属势力色；无势力 → 主题灰。"""
        fid = getattr(self.character, "faction", None)
        if fid and self.world is not None:
            f = self.world.faction(fid)
            if f is not None and getattr(f, "color", None):
                return f.color, darken_color(f.color, 0.4)
        return NO_FACTION_COLOR, NO_FACTION_EDGE

    def _draw_data_polygon(self, canvas):
        fill_color, edge_color = self._fill_and_edge()

        data_pts = []
        for a, (_, attr) in zip(self._axis_angles(), RADAR_AXES):
            v = getattr(self.character, attr, 0) or 0
            v = max(0, min(RADAR_MAX, v))   # 负值视为 0；>100 截到 100
            r = RADAR_RADIUS * v / RADAR_MAX
            data_pts.append((RADAR_CENTER + r * math.cos(a),
                             RADAR_CENTER + r * math.sin(a)))

        flat = [c for p in data_pts for c in p]
        canvas.create_polygon(
            *flat,
            fill=fill_color, stipple="gray50",
            outline=edge_color, width=2,
        )

        # 数据顶点小圆
        for x, y in data_pts:
            canvas.create_oval(
                x - RADAR_DOT_R, y - RADAR_DOT_R,
                x + RADAR_DOT_R, y + RADAR_DOT_R,
                fill=edge_color, outline="",
            )

    # ------------------------------------------------------------
    def _build_relations(self, parent):
        wrap = tk.Frame(parent, bg=THEME["panel_bg"])
        wrap.pack(fill="x", padx=16, pady=(10, 0))

        tk.Label(
            wrap, text="关系", bg=THEME["panel_bg"], fg="#222222",
            font=(self.font_family, FONT_SIZES["panel_title"], "bold"),
        ).pack(anchor="w")

        body = tk.Frame(wrap, bg=THEME["panel_bg"])
        body.pack(fill="x", pady=(4, 0))

        ch = self.character

        # 第一行：父 / 母 / 配偶（三列等宽）
        row1 = tk.Frame(body, bg=THEME["panel_bg"])
        row1.pack(fill="x", pady=1)
        for i in range(3):
            row1.columnconfigure(i, weight=1, uniform="rel")
        self._relation_cell(row1, 0, "父", ch.father)
        self._relation_cell(row1, 1, "母", ch.mother)
        self._relation_cell(row1, 2, "配偶", ch.spouse)

        # 列表型
        self._relation_list_row(body, "义兄弟", ch.sworn_brothers)
        self._relation_list_row(body, "亲爱", ch.liked)
        self._relation_list_row(body, "厌恶", ch.disliked)

        # 末行：血缘 + 世代
        row2 = tk.Frame(body, bg=THEME["panel_bg"])
        row2.pack(fill="x", pady=1)
        tk.Label(
            row2, text="血缘：", bg=THEME["panel_bg"], fg=BODY_FG,
            font=(self.font_family, FONT_SIZES["panel_body"]),
        ).pack(side="left")
        tk.Label(
            row2, text=(ch.blood or "—"), bg=THEME["panel_bg"], fg=BODY_FG,
            font=(self.font_family, FONT_SIZES["panel_body"]),
        ).pack(side="left")
        tk.Label(
            row2, text="世代：", bg=THEME["panel_bg"], fg=BODY_FG,
            font=(self.font_family, FONT_SIZES["panel_body"]),
        ).pack(side="left", padx=(24, 0))
        tk.Label(
            row2, text=str(ch.generation or 1), bg=THEME["panel_bg"], fg=BODY_FG,
            font=(self.font_family, FONT_SIZES["panel_body"]),
        ).pack(side="left")

    # ------------------------------------------------------------
    def _relation_cell(self, parent, col, label, cid):
        """单值关系单元格（父 / 母 / 配偶）。父是 grid 容器。"""
        cell = tk.Frame(parent, bg=THEME["panel_bg"])
        cell.grid(row=0, column=col, sticky="w")

        tk.Label(
            cell, text=f"{label}：", bg=THEME["panel_bg"], fg=BODY_FG,
            font=(self.font_family, FONT_SIZES["panel_body"]),
        ).pack(side="left")

        if cid:
            name = self._resolve_name(cid)
            if name:
                self._link_label(cell, cid, name)
            else:
                self._muted_label(cell, "—")
        else:
            self._muted_label(cell, "—")

    def _relation_list_row(self, parent, label, ids):
        """列表型关系（义兄弟 / 亲爱 / 厌恶）。"""
        row = tk.Frame(parent, bg=THEME["panel_bg"])
        row.pack(fill="x", pady=1)

        tk.Label(
            row, text=f"{label}：", bg=THEME["panel_bg"], fg=BODY_FG,
            font=(self.font_family, FONT_SIZES["panel_body"]),
        ).pack(side="left")

        ids = ids or []
        if not ids:
            self._muted_label(row, "—")
            return

        first = True
        for cid in ids:
            if first:
                first = False
            else:
                tk.Label(
                    row, text="、", bg=THEME["panel_bg"], fg=BODY_FG,
                    font=(self.font_family, FONT_SIZES["panel_body"]),
                ).pack(side="left")

            name = self._resolve_name(cid)
            if name:
                self._link_label(row, cid, name)
            else:
                self._muted_label(row, "—")

    def _muted_label(self, parent, text):
        tk.Label(
            parent, text=text, bg=THEME["panel_bg"], fg=MUTED_COLOR,
            font=(self.font_family, FONT_SIZES["panel_body"]),
        ).pack(side="left")

    def _link_label(self, parent, cid, name):
        lbl = tk.Label(
            parent, text=name, bg=THEME["panel_bg"], fg=LINK_COLOR,
            font=(self.font_family, FONT_SIZES["panel_body"]),
            cursor="hand2",
        )
        lbl.pack(side="left")
        lbl.bind("<Button-1>", lambda e, c=cid: self._open_character(c))

    def _resolve_name(self, cid):
        """id → 展示名（带表字）。world 缺失 / 查不到 → None。"""
        if not cid or self.world is None:
            return None
        ch = self.world.character(cid)
        if ch is None:
            return None
        return ch.display_name()

    # ------------------------------------------------------------
    def _build_bio(self, parent):
        wrap = tk.Frame(parent, bg=THEME["panel_bg"])
        wrap.pack(fill="x", padx=16, pady=(10, 14))

        tk.Label(
            wrap, text="生平", bg=THEME["panel_bg"], fg="#222222",
            font=(self.font_family, FONT_SIZES["panel_title"], "bold"),
        ).pack(anchor="w")

        tk.Label(
            wrap, text="（生平未收录）",
            bg=THEME["panel_bg"], fg=BIO_FG,
            font=(self.font_family, FONT_SIZES["panel_body"], "italic"),
        ).pack(anchor="w", pady=(4, 0))

    # ------------------------------------------------------------
    def _open_character(self, cid):
        """点击关系人 → 打开新的人物情报窗口（master = 主窗口）。"""
        if self.world is None:
            return
        ch = self.world.character(cid)
        if ch is None:
            return
        logger.debug("人物情报跳转：%s → %s", self.character.id, cid)
        CharacterInfoWindow(
            self._top, ch,
            world=self.world,
            font_family=self.font_family,
        )

    # ============================================================
    # 头像
    # ============================================================
    def _find_portrait_path(self):
        base = f"{self.character.id}-{self.character.name}"
        for ext in PORTRAIT_EXTS:
            p = PORTRAIT_DIR / f"{base}{ext}"
            if p.is_file():
                return p
        return None

    def _load_portrait(self):
        path = self._find_portrait_path()
        logger.debug("人物情报头像：%s → %s", self.character.id, path)
        if path is None:
            self._portrait_label.configure(
                text="（无头像）", fg="#999999",
                font=(self.font_family, FONT_SIZES["panel_body"]),
            )
            return

        if not _PIL_OK:
            self._portrait_label.configure(
                text="未安装 Pillow\n无法显示 JPG", fg="#B03A2E",
                font=(self.font_family, FONT_SIZES["panel_body"]),
            )
            return

        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail((MAX_W, MAX_H), Image.LANCZOS)
            self._photo = ImageTk.PhotoImage(img)
            self._portrait_label.configure(image=self._photo, text="")
        except Exception as e:
            logger.warning("头像加载失败：%s", path, exc_info=True)
            self._portrait_label.configure(
                text=f"（加载失败）\n{e}", fg="#B03A2E",
                font=(self.font_family, FONT_SIZES["panel_body"]),
            )