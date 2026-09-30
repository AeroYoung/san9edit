# -*- coding: utf-8 -*-
"""人物情报窗口 / 编辑人物窗口。

两个角色由 session 是否有值决定：
    session 有值（MODE_EDIT）→ 标题「XXX — 编辑人物」，头部字段可编辑 + 外官区
    session 为 None（MODE_GAME）→ 标题「XXX — 人物情报」，纯只读展示

内容：基础（头像 + 字段）/ 五维雷达图 / 归属 / 外官 / 关系 / 生平；
编辑模式最底部：保存 / 取消 按钮。

头像路径约定：assets/portrait/{id}-{name}.{ext}
雷达图用 tkinter Canvas 绘制（不依赖 Pillow）。
"""

import logging
import math
import tkinter as tk
from tkinter import simpledialog, ttk

from game.config import constants as C
from game.config.style import THEME, FONT_SIZES
from game.core.faction_color import faction_display_color
from game.core.utils import darken_color, lighten_color
from game.ui.widgets.searchable_combo import SearchableCombobox
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

WIN_W = 600
WIN_MIN_H = 640
SCROLL_H = WIN_MIN_H - 80

RADAR_SIZE = 340
RADAR_CENTER = RADAR_SIZE / 2
RADAR_RADIUS = 130
RADAR_GRID_RINGS = 5
RADAR_MAX = 100
RADAR_LABEL_GAP = 18
RADAR_NUM_GAP = 14
RADAR_DOT_R = 3

SEX_CHOICES = ("男", "女")

RADAR_AXES = (
    ("统", "leadership"),
    ("武", "might"),
    ("智", "intelligence"),
    ("政", "politics"),
    ("魅", "charisma"),
)

LINK_COLOR = "#1F6FBF"
BODY_FG = "#333333"
NUM_FG = "#666666"
BIO_FG = "#888888"
MUTED_COLOR = "#999999"
NO_FACTION_COLOR = "#7F8C8D"
NO_FACTION_EDGE = "#5D6D7E"


class CharacterInfoWindow(tk.Toplevel):
    def __init__(self, master, character, world=None,
                 font_family="TkDefaultFont", session=None, on_saved=None):
        super().__init__(master)
        self.character = character
        self.world = world
        self.font_family = font_family
        self.session = session
        self.on_saved = on_saved
        self._edit_vars = {}
        self._stats = {attr: int(getattr(character, attr, 0) or 0)
                       for _label, attr in RADAR_AXES}
        self._radar_canvas = None
        self._scroll_canvas = None
        self._photo = None
        self._fitting = False
        self._top = master.winfo_toplevel()

        logger.debug("打开人物窗口：%s（可编辑=%s）",
                     character.id, session is not None)

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
        host = self._build_scroll_host()

        if self.session is not None:
            self._build_editor(host)
        else:
            job = (self.character.job_label(self.world)
                   if self.world is not None else "")
            if job:
                tk.Label(
                    host,
                    text="官职：" + job,
                    bg=THEME["panel_bg"], fg=BODY_FG,
                    font=(self.font_family, FONT_SIZES["panel_body"]),
                ).pack(pady=(6, 6))

        # 关系区
        tk.Frame(host, bg=THEME["status_sep"], height=1).pack(
            fill="x", padx=16, pady=(10, 0))
        self._build_relations(host)

        # 生平区
        tk.Frame(host, bg=THEME["status_sep"], height=1).pack(
            fill="x", padx=16, pady=(10, 0))
        self._build_bio(host)

        # 编辑模式：保存 / 取消 + 状态消息
        if self.session is not None:
            footer = tk.Frame(host, bg=THEME["panel_bg"])
            footer.pack(fill="x", padx=16, pady=(12, 4))
            tk.Button(footer, text="保存", width=10,
                      command=self._save).pack(side="left")
            tk.Button(footer, text="取消", width=10,
                      command=self.destroy).pack(side="left", padx=(8, 0))

            self._edit_msg = tk.Label(
                host, text="", bg=THEME["panel_bg"], fg="#555555",
                anchor="w", justify="left", wraplength=WIN_W - 48,
                font=(self.font_family, FONT_SIZES["panel_body"]))
            self._edit_msg.pack(fill="x", padx=16, pady=(0, 14))

    def _build_scroll_host(self):
        """内容放进 Canvas：竖 / 横滚动条按内容 vs 视口大小自动出现。"""
        outer = tk.Frame(self, bg=THEME["panel_bg"])
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, width=WIN_W - 18, height=SCROLL_H,
                           bg=THEME["panel_bg"], highlightthickness=0)
        bar_y = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        bar_x = ttk.Scrollbar(outer, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=bar_y.set, xscrollcommand=bar_x.set)

        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        canvas.grid(row=0, column=0, sticky="nsew")
        bar_y.grid(row=0, column=1, sticky="ns")
        bar_x.grid(row=1, column=0, sticky="ew")
        bar_y.grid_remove()
        bar_x.grid_remove()

        host = tk.Frame(canvas, bg=THEME["panel_bg"])
        window = canvas.create_window((0, 0), window=host, anchor="nw")

        def _sync(_evt=None):
            if self._fitting:
                return
            self._fitting = True
            try:
                host.update_idletasks()
                nh = host.winfo_reqheight()
                nw = host.winfo_reqwidth()
                cw = canvas.winfo_width()
                ch = canvas.winfo_height()
                if cw <= 1 or ch <= 1:
                    return
                canvas.itemconfigure(window, width=max(cw, nw))
                if nh > ch:
                    bar_y.grid()
                else:
                    bar_y.grid_remove()
                if nw > cw:
                    bar_x.grid()
                else:
                    bar_x.grid_remove()
                canvas.configure(scrollregion=canvas.bbox("all"))
            finally:
                self._fitting = False

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
    # 编辑区
    # ------------------------------------------------------------
    def _build_editor(self, parent):
        from game.ui.widgets.collapsible import CollapsibleSection

        ch = self.character
        wrap = tk.Frame(parent, bg=THEME["panel_bg"])
        wrap.pack(fill="x", padx=16, pady=(2, 0))

        def section(title, expanded=True):
            sec = CollapsibleSection(wrap, title, expanded=expanded,
                                     font_family=self.font_family)
            sec.pack(fill="x", pady=(2, 0))
            return sec.body

        # ---------------- 基础（左头像 + 右字段） ----------------
        basic = section("基础")
        basic.columnconfigure(1, weight=1)

        left = tk.Frame(basic, bg=THEME["panel_bg"])
        left.grid(row=0, column=0, sticky="nw", padx=(0, 16))
        self._build_portrait(left)

        right = tk.Frame(basic, bg=THEME["panel_bg"])
        right.grid(row=0, column=1, sticky="new")
        right.columnconfigure(1, weight=1)

        def add_row(row_idx, label, widget):
            tk.Label(right, text=label, bg=THEME["panel_bg"], fg=BODY_FG,
                     anchor="e",
                     font=(self.font_family, FONT_SIZES["panel_body"])
                     ).grid(row=row_idx, column=0, sticky="e",
                            padx=(0, 8), pady=3)
            widget.grid(row=row_idx, column=1, sticky="w", pady=3)

        self._name_var = tk.StringVar(value=str(ch.name or ""))
        self._edit_vars["name"] = self._name_var
        add_row(0, "姓名", tk.Entry(right, textvariable=self._name_var, width=12))

        self._family_var = tk.StringVar(value=str(ch.family_name or ""))
        self._edit_vars["family_name"] = self._family_var
        add_row(1, "字", tk.Entry(right, textvariable=self._family_var, width=12))

        # 官职（只读派生：武官 + 外官，连接词按 rank 决定；见 Character.job_label）
        # 只读 Text（非 Entry / Label）→ 可换行 + 可拖选 + Ctrl+C 复制（§8.3 第 59 条）
        job_value = ch.job_label(self.world)
        _CHARS_PER_LINE = 24
        _lines = max(1, (len(job_value) + _CHARS_PER_LINE - 1) // _CHARS_PER_LINE)
        self._job_text = tk.Text(
            right, width=1, height=_lines, wrap="char",
            bg=THEME["panel_bg"], fg=BODY_FG, bd=0,
            highlightthickness=0, padx=0, pady=0,
            font=(self.font_family, FONT_SIZES["panel_body"]),
            cursor="xterm",
        )
        self._job_text.insert("1.0", job_value)
        self._job_text.configure(state="disabled")
        tk.Label(right, text="官职", bg=THEME["panel_bg"], fg=BODY_FG,
                 anchor="e",
                 font=(self.font_family, FONT_SIZES["panel_body"])
                 ).grid(row=2, column=0, sticky="ne", padx=(0, 8), pady=3)
        self._job_text.grid(row=2, column=1, sticky="ew", pady=3)
        ch_sex = ch.sex if ch.sex in SEX_CHOICES else SEX_CHOICES[0]
        self._sex_var = tk.StringVar(value=ch_sex)
        self._edit_vars["sex"] = self._sex_var
        sex_box = ttk.Combobox(right, textvariable=self._sex_var,
                               state="readonly", values=list(SEX_CHOICES),
                               width=8)
        add_row(3, "性别", sex_box)
        self._appeared_var = tk.BooleanVar(value=bool(ch.appeared))
        appeared_box = tk.Checkbutton(
            right, text="已登场", variable=self._appeared_var,
            bg=THEME["panel_bg"], fg=BODY_FG,
            activebackground=THEME["panel_bg"],
            font=(self.font_family, FONT_SIZES["panel_body"]))
        add_row(4, "登场", appeared_box)

        # 出生年（可编辑）
        self._birth_var = tk.StringVar(
            value="" if ch.birth_year is None else str(ch.birth_year))
        self._edit_vars["birth_year"] = self._birth_var
        add_row(5, "出生年", tk.Entry(right, textvariable=self._birth_var,
                                       width=12))

        # 年龄（只读，与出生年联动：剧本年份 − 出生年）
        self._age_var = tk.StringVar(value="—")
        add_row(6, "年龄", tk.Label(
            right, textvariable=self._age_var,
            bg=THEME["panel_bg"], fg=BODY_FG,
            font=(self.font_family, FONT_SIZES["panel_body"])))

        def _refresh_age(*_a):
            raw = self._birth_var.get().strip()
            try:
                by = int(raw)
            except ValueError:
                self._age_var.set("—")
                return
            cur = getattr(self.world, "year", None)
            if cur is None:
                self._age_var.set("—")
                return
            age = cur - by
            self._age_var.set(str(age) if age >= 0 else "—")
        self._birth_var.trace_add("write", _refresh_age)
        _refresh_age()

        # 兵力上限（只读，与统率联动：改五维里的「统」即时重算）
        self._soldiers_cap_var = tk.StringVar(value="—")
        add_row(7, "兵力上限", tk.Label(
            right, textvariable=self._soldiers_cap_var,
            bg=THEME["panel_bg"], fg=BODY_FG,
            font=(self.font_family, FONT_SIZES["panel_body"])))
        self._refresh_soldiers_cap()

        # ---------------- 五维（雷达图居中） ----------------
        stats = section("五维")
        tk.Label(stats, text="（点击轴标签修改该维数值）",
                 bg=THEME["panel_bg"], fg=MUTED_COLOR, anchor="center",
                 font=(self.font_family, FONT_SIZES["panel_body"] - 1)
                 ).pack(fill="x")
        radar_box = tk.Frame(stats, bg=THEME["panel_bg"])
        radar_box.pack(anchor="center")
        self._build_radar(radar_box)

        # ---------------- 归属（势力 + 按钮一行） ----------------
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
        self._faction_combo = SearchableCombobox(
            row, [label for _v, label in options],
            textvariable=self._faction_var, width=14)
        self._faction_combo.pack(side="left", padx=(6, 12))
        self._edit_vars["faction"] = self._faction_var

        self._node_id = ch.node
        self._location_id = ch.location
        self._node_btn = tk.Button(
            row, text=self._node_text(), anchor="w",
            font=(self.font_family, FONT_SIZES["panel_body"]),
            command=self._pick_node)
        self._node_btn.pack(side="left", fill="x", expand=True)

        # ---------------- 官职（左武官 / 右外官） ----------------
        job = section("官职")
        job.columnconfigure(0, weight=1, uniform="jobcol")
        job.columnconfigure(1, weight=2, uniform="jobcol")

        # 左栏：武官
        left_job = tk.Frame(job, bg=THEME["panel_bg"])
        left_job.grid(row=0, column=0, sticky="new", padx=(0, 12))
        tk.Label(left_job, text="武官", bg=THEME["panel_bg"], fg=BODY_FG,
                 anchor="w",
                 font=(self.font_family, FONT_SIZES["panel_body"], "bold")
                 ).pack(anchor="w")
        self._build_military_title(left_job)

        # 右栏：外官
        right_job = tk.Frame(job, bg=THEME["panel_bg"])
        right_job.grid(row=0, column=1, sticky="new")
        tk.Label(right_job, text=self._official_title(),
                 bg=THEME["panel_bg"], fg=BODY_FG, anchor="w",
                 font=(self.font_family, FONT_SIZES["panel_body"], "bold")
                 ).pack(anchor="w")
        self._official_body = tk.Frame(right_job, bg=THEME["panel_bg"])
        self._official_body.pack(fill="x")
        self._refresh_officials()
        self._official_edit_btn = tk.Button(
            right_job, text="编辑外官", width=10,
            command=self._edit_officials)
        self._official_edit_btn.pack(anchor="w", pady=(4, 0))
        # 在野（无势力）→ 无实控区域，外官编辑入口禁用（需求 4-C）
        if not ch.faction:
            self._official_edit_btn.configure(state="disabled")


    def _official_title(self):
        count = len(self.world.officials_of_character(self.character.id))
        return "外官（%d）" % count

    def _refresh_officials(self):
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
        for item in items:
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

    # ------------------------------------------------------------
    # 武官（官职组左栏）
    # ------------------------------------------------------------
    def _military_label_for(self, title):
        """官名 → 下拉 label（'位阶 官名'）。None / 空 → '（无）'。"""
        if not title:
            return "（无）"
        from game.core import military_title as mt
        r = mt.rank_of(title)
        return f"{r} {title}" if r is not None else title

    def _military_title_options(self):
        """下拉选项：'（无）' + 全部武官，label = '位阶 官名'。

        本势力内已被占用的官名（rank < UNIQUE_MAX_RANK）加「（已占用）」后缀。
        """
        from game.core import military_title as mt
        ch = self.character
        opts = ["（无）"]
        for title in mt.all_titles():
            label = self._military_label_for(title)
            occupied = (
                ch.faction
                and mt.is_unique(title)
                and not mt.is_title_free(self.world, title, ch.faction,
                                         exclude_cid=ch.id)
            )
            if occupied:
                label += "（已占用）"
            opts.append(label)
        return opts

    def _parse_military_label(self, label):
        """下拉 label → 官名。'（无）' / 空 → None。"""
        if not label or label == "（无）":
            return None
        text = label.replace("（已占用）", "").strip()
        # '位阶 官名' → 取空格后的部分；否则原样
        parts = text.split(" ", 1)
        return parts[1] if len(parts) == 2 else text

    def _build_military_title(self, parent):
        """武官下拉：可搜索 + 带位阶 + 已占用标后缀。"""
        self._mil_var = tk.StringVar(
            value=self._military_label_for(self.character.military_title))
        self._mil_combo = SearchableCombobox(
            parent, self._military_title_options(),
            textvariable=self._mil_var, width=22)
        self._mil_combo.pack(anchor="w", fill="x")
        # 提示行（保留占位，将来若切到方案 B 可用）
        self._mil_warn = tk.Label(
            parent, text="", bg=THEME["panel_bg"], fg="#B03A2E",
            anchor="w", justify="left", wraplength=200,
            font=(self.font_family, FONT_SIZES["panel_body"] - 1))
        self._mil_warn.pack(anchor="w", pady=(2, 0))

    def _edit_officials(self):
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
            self._refresh_job()
            self._edit_msg.configure(text="外官已保存", fg="#1E7A3C")

    def _collect_changes(self):
        ch = self.world.character(self.character.id)
        old, new = {}, {}

        for key in ("name", "family_name", "sex"):
            value = self._edit_vars[key].get().strip()
            if getattr(ch, key) != value:
                old[key] = getattr(ch, key)
                new[key] = value
        for _label, attr in RADAR_AXES:
            value = max(0, min(100, int(self._stats.get(attr, 0) or 0)))
            if getattr(ch, attr) != value:
                old[attr] = getattr(ch, attr)
                new[attr] = value
        appeared = bool(self._appeared_var.get())
        if bool(ch.appeared) != appeared:
            old["appeared"] = bool(ch.appeared)
            new["appeared"] = appeared

        # 出生年：空字符串 → 不提交；非数字 → 抛 ValueError 由 _save 显示
        raw_birth = self._birth_var.get().strip()
        if raw_birth:
            try:
                birth_new = int(raw_birth)
            except ValueError:
                raise ValueError("出生年：请输入整数")
            if getattr(ch, "birth_year", None) != birth_new:
                old["birth_year"] = getattr(ch, "birth_year", None)
                new["birth_year"] = birth_new

        # 武官下拉：先规范化，再反解析为官名
        try:
            self._mil_combo.normalize()
        except tk.TclError:
            pass
        new_title = self._parse_military_label(self._mil_var.get())
        if (ch.military_title or None) != new_title:
            old["military_title"] = ch.military_title
            new["military_title"] = new_title


        # 势力下拉先规范化（防脏值）
        try:
            self._faction_combo.normalize()
        except tk.TclError:
            pass
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

        # 武官唯一性校验（需求 5-B：允许选中，保存时拒绝）
        if "military_title" in new:
            new_title = new["military_title"]
            if new_title and ch.faction:
                from game.core import military_title as mt
                if not mt.is_title_free(self.world, new_title, ch.faction,
                                        exclude_cid=ch.id):
                    self._edit_msg.configure(
                        text=f"武官「{new_title}」已被本势力其他人占用，无法保存",
                        fg="#B03A2E")
                    return

        self.session.execute(CharacterEditCommand(ch.id, old, new))
        if callable(self.on_saved):
            self.on_saved()
        warning = ("（该人物当前担任外官将保留，"
                   "请在据点情报窗口确认冲突）" if "faction" in new else "")
        self._edit_msg.configure(text="已保存" + warning, fg="#1E7A3C")
        # 武官变化 → 同步刷新「官职」只读行
        self._refresh_job()

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
        canvas = self._radar_canvas
        if canvas is None:
            return
        canvas.delete("all")
        outer_pts = self._axis_points()

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

        for x, y in outer_pts:
            canvas.create_line(
                RADAR_CENTER, RADAR_CENTER, x, y,
                fill=lighten_color(THEME["status_sep"], 0.5),
                width=1,
            )

        self._draw_data_polygon(canvas)

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
        if attr == "leadership":
            self._refresh_soldiers_cap()

    def _refresh_soldiers_cap(self):
        """兵力上限是统率的派生值（见 config/rules.py），此处只读展示。"""
        cap = type(self.character).compute_soldiers_cap(
            self._stats.get("leadership", 0),
            getattr(self.character, "military_title", None),
        )
        self._soldiers_cap_var.set(str(cap))

    def _refresh_job(self):
        """外官保存后重刷官职行文本 + 高度。"""
        if not hasattr(self, "_job_text"):
            return
        t = self._job_text
        t.configure(state="normal")
        t.delete("1.0", "end")
        t.insert("1.0", self.character.job_label(self.world))
        t.configure(state="disabled")
        # 按新文本重算行数
        _CHARS_PER_LINE = 24
        n = len(t.get("1.0", "end-1c"))
        t.configure(height=max(1, (n + _CHARS_PER_LINE - 1) // _CHARS_PER_LINE))

    def _axis_angles(self):
        return [-math.pi / 2 + i * (2 * math.pi / 5) for i in range(5)]

    def _axis_points(self):
        return [
            (RADAR_CENTER + RADAR_RADIUS * math.cos(a),
             RADAR_CENTER + RADAR_RADIUS * math.sin(a))
            for a in self._axis_angles()
        ]

    def _fill_and_edge(self):
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
            v = max(0, min(RADAR_MAX, v))
            r = RADAR_RADIUS * v / RADAR_MAX
            data_pts.append((RADAR_CENTER + r * math.cos(a),
                             RADAR_CENTER + r * math.sin(a)))

        flat = [c for p in data_pts for c in p]
        canvas.create_polygon(
            *flat,
            fill=fill_color, stipple="gray50",
            outline=edge_color, width=2,
        )

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

        row1 = tk.Frame(body, bg=THEME["panel_bg"])
        row1.pack(fill="x", pady=1)
        for i in range(3):
            row1.columnconfigure(i, weight=1, uniform="rel")
        self._relation_cell(row1, 0, "父", ch.father)
        self._relation_cell(row1, 1, "母", ch.mother)
        self._relation_cell(row1, 2, "配偶", ch.spouse)

        self._relation_list_row(body, "义兄弟", ch.sworn_brothers)
        self._relation_list_row(body, "亲爱", ch.liked)
        self._relation_list_row(body, "厌恶", ch.disliked)

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

    def _relation_cell(self, parent, col, label, cid):
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