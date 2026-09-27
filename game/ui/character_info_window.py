# -*- coding: utf-8 -*-
"""人物情报窗口 / 编辑人物窗口。

两个角色由 APP_MODE 决定（这里的判据是 `session is None`，模式判断只在 MainWindow）：
    session 有值（MODE_EDIT）→ 标题「XXX — 编辑人物」，头部字段可编辑 + 外官区
    session 为 None（MODE_GAME）→ 标题「XXX — 人物情报」，纯只读展示

内容：头像 + 五维雷达图 + 关系 + 生平（占位）；
编辑模式追加：姓名 / 字 / 性别 / 五维 / 登场 / 势力 / 所属 / 所在 + 外官。

头像路径约定：assets/portrait/{id}-{name}.{ext}
    例如 0651-张南.jpg
不再读取 Character.portrait 字段。

雷达图用 tkinter Canvas 绘制（不依赖 Pillow），
中文轴标签直接写，避免 Pillow 找不到字体文件的问题。
"""

import logging
import math
import tkinter as tk
from tkinter import simpledialog, ttk

from game.config import constants as C
from game.config.style import THEME, FONT_SIZES
from game.core.faction_color import faction_display_color
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
SCROLL_H = WIN_MIN_H - 80       # 滚动区固定高度，超出内容走纵向滚动条（§3.10）

# 雷达图
RADAR_SIZE = 340                # Canvas 边长
RADAR_CENTER = RADAR_SIZE / 2
RADAR_RADIUS = 130              # 顶点半径
RADAR_GRID_RINGS = 5            # 同心层数（对应 20/40/60/80/100）
RADAR_MAX = 100                 # 轴上限（>100 截断到 100 画）
RADAR_LABEL_GAP = 18            # 顶点到标签的额外间距（像素）
RADAR_NUM_GAP = 14              # 标签到数值的间距（像素）
RADAR_DOT_R = 3                 # 数据顶点小圆半径

# 性别下拉（需求 §3.10：男 / 女，默认男）
SEX_CHOICES = ("男", "女")

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
    def __init__(self, master, character, world=None, font_family="TkDefaultFont",
                 session=None, on_saved=None):
        super().__init__(master)
        self.character = character
        self.world = world
        self.font_family = font_family
        self.session = session            # None = 只读（MODE_GAME）
        self.on_saved = on_saved          # 保存后回调（面板刷新）
        self._edit_vars = {}              # 编辑控件变量
        # 五维的编辑值（雷达图轴标签点改用；移除独立输入框后不再走 Entry）
        self._stats = {attr: int(getattr(character, attr, 0) or 0)
                       for _label, attr in RADAR_AXES}
        self._radar_canvas = None
        self._scroll_canvas = None
        self._photo = None    # ★ 保引用，防 GC
        # 主窗口引用（用于居中基准 / 跳转窗口的 master）
        self._top = master.winfo_toplevel()

        logger.debug("打开人物窗口：%s（可编辑=%s）",
                     character.id, session is not None)
        # 未登场人物的标题追加状态；其余显示（雷达图 / 关系区）不受 appeared 影响
        if session is not None:
            title = f"{character.display_name()} — 编辑人物"
        else:
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
        # ★ 纵向滚动容器（需求 §3.10：内容超长时可滚动）
        host = self._build_scroll_host()

        # 名字
        tk.Label(
            host, text=self.character.display_name(),
            bg=THEME["panel_bg"], fg="#222222",
            font=(self.font_family, FONT_SIZES["panel_title"] + 4, "bold"),
        ).pack(pady=(14, 2))

        # 编辑模式：头部字段可编辑（MODE_GAME 下不建这些控件）
        if self.session is not None:
            self._build_editor(host)

        # 官职（只读模式在此显示；编辑模式并进「外官」分组）
        officials = (self.world.officials_of_character(self.character.id)
                     if (self.session is None and self.world is not None)
                     else [])
        if officials:
            tk.Label(
                host,
                text="官职：" + "、".join(o.get("name", "") for o in officials),
                bg=THEME["panel_bg"], fg=BODY_FG,
                font=(self.font_family, FONT_SIZES["panel_body"]),
            ).pack(pady=(0, 6))

        # 上区：头像（编辑模式下雷达图并进「五维」分组）
        top = tk.Frame(host, bg=THEME["panel_bg"])
        top.pack(padx=16, pady=4, fill="x")
        self._build_portrait(top)
        if self.session is None:
            self._build_radar(top)

        # 分隔线
        tk.Frame(host, bg=THEME["status_sep"], height=1).pack(
            fill="x", padx=16, pady=(10, 0))

        # 关系区（编辑模式：可折叠分组，默认展开）
        self._build_relations(host)

        # 分隔线
        tk.Frame(host, bg=THEME["status_sep"], height=1).pack(
            fill="x", padx=16, pady=(10, 0))

        # 生平区（编辑模式：可折叠分组，默认展开）
        self._build_bio(host)

    def _build_scroll_host(self):
        """把内容装进 Canvas + 纵向滚动条，返回内容 Frame（host）。

        滚轮绑在主窗口上：Tk 的 bindtags 会把子控件的滚轮事件冒泡到 toplevel，
        这样指针停在任意子控件上都能滚。
        """
        outer = tk.Frame(self, bg=THEME["panel_bg"])
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, width=WIN_W - 18, height=SCROLL_H,
                           bg=THEME["panel_bg"], highlightthickness=0)
        bar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set)
        canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")

        host = tk.Frame(canvas, bg=THEME["panel_bg"])
        window = canvas.create_window((0, 0), window=host, anchor="nw")

        def _sync(_evt=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            width = canvas.winfo_width()
            if width > 1:
                canvas.itemconfigure(window, width=width)

        host.bind("<Configure>", _sync)
        canvas.bind("<Configure>", _sync)
        self._scroll_canvas = canvas
        self.bind("<MouseWheel>", self._on_wheel)
        return host

    def _on_wheel(self, event):
        if self._scroll_canvas is None:
            return
        self._scroll_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    # ------------------------------------------------------------
    # 编辑区（仅 MODE_EDIT；MODE_GAME 下不构建）
    # ------------------------------------------------------------
    def _build_editor(self, parent):
        """编辑区：按「基础 / 五维 / 归属 / 外官」分组展示与编辑。

        用 CollapsibleSection（设置窗口同款）做分组，每组可折叠；
        控件都在同一弹窗里，保存时统一收集变化（只提交真正变化的字段）。
        """
        from game.ui.widgets.collapsible import CollapsibleSection

        ch = self.character
        wrap = tk.Frame(parent, bg=THEME["panel_bg"])
        wrap.pack(fill="x", padx=16, pady=(2, 0))

        def section(title, expanded=True):
            """建一个可折叠分组并 pack 进容器，返回内容区。

            ★ CollapsibleSection 自己不会 pack，忘了这一步整个分组不可见。
            """
            sec = CollapsibleSection(wrap, title, expanded=expanded,
                                     font_family=self.font_family)
            sec.pack(fill="x", pady=(2, 0))
            return sec.body

        # ---------------- 基础（横向一行） ----------------
        basic = section("基础")
        row = tk.Frame(basic, bg=THEME["panel_bg"])
        row.pack(fill="x")

        def cell(label, key, value, width=8):
            tk.Label(row, text=label, bg=THEME["panel_bg"], fg=BODY_FG,
                     font=(self.font_family, FONT_SIZES["panel_body"])
                     ).pack(side="left")
            var = tk.StringVar(value=str(value))
            tk.Entry(row, textvariable=var, width=width).pack(
                side="left", padx=(4, 12))
            self._edit_vars[key] = var

        cell("姓名", "name", ch.name, width=9)
        cell("字", "family_name", ch.family_name, width=6)
        tk.Label(row, text="性别", bg=THEME["panel_bg"], fg=BODY_FG,
                 font=(self.font_family, FONT_SIZES["panel_body"])
                 ).pack(side="left")
        ch_sex = ch.sex if ch.sex in SEX_CHOICES else SEX_CHOICES[0]
        self._sex_var = tk.StringVar(value=ch_sex)
        ttk.Combobox(row, textvariable=self._sex_var, state="readonly",
                     values=list(SEX_CHOICES), width=3).pack(
            side="left", padx=(4, 12))
        self._edit_vars["sex"] = self._sex_var
        self._appeared_var = tk.BooleanVar(value=bool(ch.appeared))
        tk.Checkbutton(row, text="已登场", variable=self._appeared_var,
                       bg=THEME["panel_bg"], fg=BODY_FG,
                       activebackground=THEME["panel_bg"],
                       font=(self.font_family, FONT_SIZES["panel_body"])
                       ).pack(side="left")

        # ---------------- 五维（雷达图 + 轴标签，可点改） ----------------
        stats = section("五维")
        tk.Label(stats, text="（点击轴标签修改该维数值）",
                 bg=THEME["panel_bg"], fg=MUTED_COLOR, anchor="w",
                 font=(self.font_family, FONT_SIZES["panel_body"] - 1)
                 ).pack(fill="x")
        radar_box = tk.Frame(stats, bg=THEME["panel_bg"])
        radar_box.pack(anchor="w")
        self._build_radar(radar_box)

        # ---------------- 归属 ----------------
        belong = section("归属")
        options = [(None, "在野")] + [(f.id, f.name) for f in
                                      sorted(self.world.factions.values(),
                                             key=lambda f: f.name)]
        self._faction_by_label = {label: v for v, label in options}
        current = next((label for v, label in options if v == ch.faction), "在野")
        self._faction_var = tk.StringVar(value=current)

        row = tk.Frame(belong, bg=THEME["panel_bg"])
        row.pack(fill="x")
        tk.Label(row, text="势力", bg=THEME["panel_bg"], fg=BODY_FG,
                 font=(self.font_family, FONT_SIZES["panel_body"])
                 ).pack(side="left")
        ttk.Combobox(row, textvariable=self._faction_var, state="readonly",
                     values=[label for _v, label in options], width=12
                     ).pack(side="left", padx=(6, 0))
        self._edit_vars["faction"] = self._faction_var

        # 所属 / 所在：复用「移动到据点」的据点单选弹窗（可搜索 / 排序）
        self._node_id = ch.node
        self._location_id = ch.location
        self._node_btn = tk.Button(
            belong, text=self._node_text(), anchor="w",
            font=(self.font_family, FONT_SIZES["panel_body"]),
            command=self._pick_node)
        self._node_btn.pack(fill="x", pady=(6, 0))

        # ---------------- 外官 ----------------
        self._official_body = section(self._official_title())
        self._refresh_officials()
        tk.Button(self._official_body, text="编辑外官", width=10,
                  command=self._edit_officials).pack(anchor="w", pady=(4, 0))

        # ---------------- 保存 ----------------
        footer = tk.Frame(wrap, bg=THEME["panel_bg"])
        footer.pack(fill="x", pady=(8, 0))
        tk.Button(footer, text="保存", width=10,
                  command=self._save).pack(side="left")
        self._edit_msg = tk.Label(
            wrap, text="", bg=THEME["panel_bg"], fg="#555555", anchor="w",
            justify="left", wraplength=WIN_W - 48,
            font=(self.font_family, FONT_SIZES["panel_body"]))
        self._edit_msg.pack(fill="x", pady=(4, 0))

    def _official_title(self):
        count = len(self.world.officials_of_character(self.character.id))
        return "外官（%d）" % count

    def _refresh_officials(self):
        """外官分组内容：一人可多职，按行政区 id 排序逐行列出。"""
        for w in self._official_body.winfo_children():
            if isinstance(w, tk.Label):
                w.destroy()
        items = self.world.officials_of_character(self.character.id)
        if not items:
            tk.Label(self._official_body, text="（无）", bg=THEME["panel_bg"],
                     fg=MUTED_COLOR, anchor="w",
                     font=(self.font_family, FONT_SIZES["panel_body"])
                     ).pack(fill="x")
            return
        for i, item in enumerate(items):
            tk.Label(self._official_body,
                     text="%s　%s" % (item.get("name", ""),
                                      item["region_id"]),
                     bg=THEME["panel_bg"], fg=BODY_FG, anchor="w",
                     font=(self.font_family, FONT_SIZES["panel_body"])
                     ).pack(fill="x")


    def _node_text(self):
        world = self.world
        node = world.node(self._node_id) if world is not None else None
        loc = world.node(self._location_id) if world is not None else None
        return "所属：%s ｜ 所在：%s（点击选择）" % (
            node.name if node is not None else "—",
            loc.name if loc is not None else "—")

    def _pick_node(self):
        from game.ui.dialogs.move_to_node import pick_node
        node_id = pick_node(self, self.world, "选择所属 / 所在据点")
        if node_id:
            self._node_id = node_id
            self._location_id = node_id
            self._node_btn.configure(text=self._node_text())

    def _edit_officials(self):
        """外官区：走 official_edit 共用流程（增 / 改 / 删在自己那层弹窗里）。

        open_dialog 必须**等弹窗关闭**再返回，否则 edit_officials 读到的
        dlg.ok 还是 False，命令根本不会执行（弹窗看着"点了保存却没生效"）。
        """
        from game.ui.dialogs.official_edit import edit_officials

        ch = self.world.character(self.character.id)
        if ch is None:
            return

        def _open(dlg_factory):
            dlg = dlg_factory()
            self.wait_window(dlg)
            return dlg

        if edit_officials(self, self.world, ch, self.session, _open):
            if callable(self.on_saved):
                self.on_saved()
            self._refresh_officials()
            self._edit_msg.configure(text="外官已保存", fg="#1E7A3C")

    def _collect_changes(self):
        """编辑区里真正变化的字段 → (old, new)；整数非法时抛 ValueError。"""
        ch = self.world.character(self.character.id)
        old, new = {}, {}

        for key in ("name", "family_name", "sex"):
            value = self._edit_vars[key].get().strip()
            if getattr(ch, key) != value:
                old[key] = getattr(ch, key)
                new[key] = value
        # 五维：值来自雷达图轴标签的输入框（self._stats），不再有独立输入框
        for _label, attr in RADAR_AXES:
            value = max(0, min(100, int(self._stats.get(attr, 0) or 0)))
            if getattr(ch, attr) != value:
                old[attr] = getattr(ch, attr)
                new[attr] = value
        appeared = bool(self._appeared_var.get())
        if bool(ch.appeared) != appeared:
            old["appeared"] = bool(ch.appeared)
            new["appeared"] = appeared
        faction = self._faction_by_label.get(self._faction_var.get())
        if ch.faction != faction:
            old["faction"] = ch.faction
            new["faction"] = faction
        if ch.node != self._node_id:
            old["node"] = ch.node
            new["node"] = self._node_id
        if ch.location != self._location_id:
            old["location"] = ch.location
            new["location"] = self._location_id
        return old, new

    def _save(self):
        """君主阻断 → CharacterEditCommand → 刷新（改 World 只走 Command）。"""
        from game.core.edit_commands import CharacterEditCommand
        ch = self.world.character(self.character.id)
        is_ruler = ch.faction is not None and ch.faction == ch.id
        try:
            old, new = self._collect_changes()
        except ValueError as e:
            self._edit_msg.configure(text=str(e), fg="#B03A2E")
            return
        if not new:
            self._edit_msg.configure(text="没有改动", fg="#555555")
            return
        if is_ruler and new.get("appeared") is False:
            self._edit_msg.configure(text="君主必须保持登场", fg="#B03A2E")
            return
        if is_ruler and "faction" in new and new["faction"] != ch.id:
            self._edit_msg.configure(text="君主需先解散势力", fg="#B03A2E")
            return

        self.session.execute(CharacterEditCommand(ch.id, old, new))
        if callable(self.on_saved):
            self.on_saved()
        warning = ("（该人物当前担任外官将保留，"
                   "请在据点情报窗口确认冲突）" if "faction" in new else "")
        self._edit_msg.configure(text="已保存" + warning, fg="#1E7A3C")

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
        self._redraw_radar()

    def _redraw_radar(self):
        """整块重画（轴标签点改数值后也走这里）。

        Canvas 尺寸固定、坐标全用 RADAR_* 常量（§8.3 第 29 条），
        delete("all") 后重画是最省事也最不会画残的写法。
        """
        canvas = self._radar_canvas
        if canvas is None:
            return
        canvas.delete("all")
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

        # 4) 轴标签 + 数值（编辑模式：标签可点，弹输入框改该维）
        editable = self.session is not None
        for (label, attr), (x, y) in zip(RADAR_AXES, outer_pts):
            dx = x - RADAR_CENTER
            dy = y - RADAR_CENTER
            norm = math.hypot(dx, dy) or 1.0
            lx = x + dx / norm * RADAR_LABEL_GAP
            ly = y + dy / norm * RADAR_LABEL_GAP

            tag = "axis_%s" % attr
            canvas.create_text(
                lx, ly, text=label,
                fill=LINK_COLOR if editable else BODY_FG,
                font=(self.font_family, FONT_SIZES["panel_title"], "bold"),
                tags=(tag,),
            )
            canvas.create_text(
                lx, ly + RADAR_NUM_GAP, text=str(self._stats.get(attr, 0)),
                fill=NUM_FG,
                font=(self.font_family, FONT_SIZES["panel_body"]),
            )
            if editable:
                canvas.tag_bind(tag, "<Button-1>",
                                lambda e, a=attr: self._edit_stat(a))
                canvas.tag_bind(tag, "<Enter>",
                                lambda e, c=canvas: c.configure(cursor="hand2"))
                canvas.tag_bind(tag, "<Leave>",
                                lambda e, c=canvas: c.configure(cursor=""))

    def _edit_stat(self, attr):
        """点击轴标签 → 输入框改该维数值（0–100）。

        ★ 只改内存里的 self._stats，不写 World —— 保存时统一提交 Command。
        """
        if self.session is None:
            return
        label = next(lb for lb, a in RADAR_AXES if a == attr)
        value = simpledialog.askinteger(
            "修改五维", f"{label}（0–100）：", parent=self,
            initialvalue=self._stats.get(attr, 0), minvalue=0, maxvalue=100)
        if value is None:
            return
        self._stats[attr] = int(value)
        self._redraw_radar()

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
        """雷达图数据色：人物所属势力的**派生显示色**（§3.4）；无势力 → 主题灰。"""
        fid = getattr(self.character, "faction", None)
        if fid and self.world is not None:
            f = self.world.faction(fid)
            if f is not None:
                color = faction_display_color(f, self.world.factions)
                return color, darken_color(color, 0.4)
        return NO_FACTION_COLOR, NO_FACTION_EDGE

    def _draw_data_polygon(self, canvas):
        fill_color, edge_color = self._fill_and_edge()

        data_pts = []
        for a, (_, attr) in zip(self._axis_angles(), RADAR_AXES):
            v = self._stats.get(attr, 0) or 0
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
        body = self._group_body(wrap, "关系")
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
        body = self._group_body(wrap, "生平")

        tk.Label(
            body, text="（生平未收录）",
            bg=THEME["panel_bg"], fg=BIO_FG,
            font=(self.font_family, FONT_SIZES["panel_body"], "italic"),
        ).pack(anchor="w", pady=(2, 0))

    def _group_body(self, wrap, title):
        """关系 / 生平的外壳：编辑模式下是可折叠分组（默认展开，§3.10），
        只读模式保持原来的「标题 + 正文」平铺。返回正文容器。"""
        if self.session is not None:
            from game.ui.widgets.collapsible import CollapsibleSection

            section = CollapsibleSection(wrap, title, expanded=True,
                                         font_family=self.font_family)
            section.pack(fill="x")
            return section.body

        tk.Label(
            wrap, text=title, bg=THEME["panel_bg"], fg="#222222",
            font=(self.font_family, FONT_SIZES["panel_title"], "bold"),
        ).pack(anchor="w")
        body = tk.Frame(wrap, bg=THEME["panel_bg"])
        body.pack(fill="x", pady=(4, 0))
        return body

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
            session=self.session,
            on_saved=self.on_saved,
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