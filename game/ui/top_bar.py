# -*- coding: utf-8 -*-
"""顶部栏：融合信息栏与菜单栏。

左：信息项（可点击弹出详情窗）
右：菜单按钮（下拉子菜单）+ 醒目的「进行」按钮

菜单动作通过 on_action(action) 上报，与具体业务解耦。
"""

import tkinter as tk

from game.config.style import THEME, FONT_SIZES
from game.ui.window_utils import center_on_parent

_REFRESH_INTERVAL_MS = 200


class TopBar(tk.Frame):
    def __init__(self, master, game_state, font_family, on_action=None):
        super().__init__(master, bg=THEME["info_bg"], height=38)
        self.pack_propagate(False)

        self.game_state = game_state
        self.font_family = font_family
        self.on_action = on_action or (lambda a, **kw: None)

        self.items = {}       # key -> (label, value_var)
        self._popups = {}     # key -> Toplevel
        self._menus = []      # 持有菜单引用，防止被 GC
        # ★ 编辑类菜单项登记表：[(menu, index)]，按 APP_MODE 一键全禁/全启
        self._edit_entries = []
        self._edit_enabled = True

        self._build_left_info()
        self._build_right_menus()
        self._start_refresh()

    # ==========================================================
    # 左侧：信息项
    # ==========================================================
    def _build_left_info(self):
        left = tk.Frame(self, bg=THEME["info_bg"])
        left.pack(side="left", fill="y", padx=6)

        items = self.game_state.get_display_items()
        for idx, (key, label_text, value_text) in enumerate(items):
            if idx > 0:
                tk.Frame(left, bg=THEME["info_sep"], width=1).pack(
                    side="left", fill="y", pady=8, padx=2
                )

            cell = tk.Frame(left, bg=THEME["info_bg"], cursor="hand2")
            cell.pack(side="left", padx=8, pady=4)

            name_lbl = tk.Label(
                cell, text=label_text + "：",
                bg=THEME["info_bg"], fg="#95A5A6",
                font=(self.font_family, FONT_SIZES["info_bar"]),
            )
            name_lbl.pack(side="left")

            value_var = tk.StringVar(value=value_text)
            value_lbl = tk.Label(
                cell, textvariable=value_var,
                bg=THEME["info_bg"], fg=THEME["info_fg"],
                font=(self.font_family, FONT_SIZES["info_bar"], "bold"),
            )
            value_lbl.pack(side="left")

            for w in (cell, name_lbl, value_lbl):
                w.bind("<Enter>", lambda e, c=cell: self._hover(c, True))
                w.bind("<Leave>", lambda e, c=cell: self._hover(c, False))
                w.bind("<Button-1>",
                       lambda e, k=key, t=label_text: self._open_info_window(k, t))

            self.items[key] = (value_lbl, value_var)

    def _hover(self, cell, entering):
        color = THEME["info_hover_bg"] if entering else THEME["info_bg"]
        cell.configure(bg=color)
        for child in cell.winfo_children():
            child.configure(bg=color)

    def _open_info_window(self, key, title):
        win = self._popups.get(key)
        if win is not None and win.winfo_exists():
            win.lift()
            win.focus_set()
            return

        win = tk.Toplevel(self)
        win.title(f"【{title}】")
        win.transient(self.winfo_toplevel())

        # 相对主窗口居中
        width, height = 620, 460
        parent = self.winfo_toplevel()
        center_on_parent(win, parent, width, height)

        win.protocol("WM_DELETE_WINDOW",
                     lambda k=key: self._close_info_window(k))

        content = tk.Frame(win, bg=THEME["panel_bg"], padx=12, pady=12)
        content.pack(fill="both", expand=True)
        tk.Label(content, text=f"这里将显示「{title}」的详细内容",
                 bg=THEME["panel_bg"], fg="#888888").pack(anchor="nw")

        self._popups[key] = win

    def _close_info_window(self, key):
        win = self._popups.pop(key, None)
        if win is not None and win.winfo_exists():
            win.destroy()

    # ==========================================================
    # 右侧：菜单按钮 + 进行按钮
    # ==========================================================
    def _build_right_menus(self):
        right = tk.Frame(self, bg=THEME["info_bg"])
        right.pack(side="right", padx=8, pady=4)

        menu_specs = [
            ("文件", self._build_file_menu),
            ("编辑", self._build_edit_menu),
            ("游戏", self._build_game_menu),
            ("势力", self._build_faction_menu),
            ("命令", self._build_order_menu),
            ("查看", self._build_view_menu),
            ("帮助", self._build_help_menu),
        ]
        for text, builder in menu_specs:
            self._make_menu_button(right, text, builder)

        # ---------- 醒目的「进行」按钮 ----------
        self.end_turn_btn = tk.Button(
            right, text="进行 ▶",
            command=lambda: self.on_action("end_turn"),
            bg="#27AE60", fg="white",
            activebackground="#2ECC71", activeforeground="white",
            relief="flat", bd=0,
            padx=18, pady=4, cursor="hand2",
            font=(self.font_family, 11, "bold"),
            highlightthickness=0,
        )
        self.end_turn_btn.pack(side="left", padx=(14, 2))
        self.end_turn_btn.bind("<Enter>",
            lambda e: self.end_turn_btn.configure(bg="#2ECC71"))
        self.end_turn_btn.bind("<Leave>",
            lambda e: self.end_turn_btn.configure(bg="#27AE60"))

    def _make_menu_button(self, parent, text, build_fn):
        mb = tk.Menubutton(
            parent, text=text,
            bg=THEME["info_bg"], fg=THEME["info_fg"],
            activebackground=THEME["info_hover_bg"],
            activeforeground="#FFFFFF",
            relief="flat", bd=0,
            padx=12, pady=4, cursor="hand2",
            font=(self.font_family, FONT_SIZES["menu"]),
            highlightthickness=0,
        )
        menu = tk.Menu(
            mb, tearoff=0,
            font=(self.font_family, FONT_SIZES["menu"]),
            activebackground="#3D566E", activeforeground="#FFFFFF",
        )
        build_fn(menu)
        mb.configure(menu=menu)
        mb.pack(side="left", padx=1)
        self._menus.append(menu)
        return mb

    # ---------- 上报动作 ----------
    def _emit(self, action):
        self.on_action(action)

    # ---------- 各下拉菜单定义 ----------
    def _add_edit_command(self, menu, **kw):
        """★ 登记一个「编辑类」菜单项：非编辑模式下可一键全禁。"""
        menu.add_command(**kw)
        self._edit_entries.append((menu, menu.index("end")))

    def _build_file_menu(self, m):
        self._add_edit_command(m, label="选择剧本",
                               command=lambda: self._emit("select_scenario"))
        m.add_separator()
        self._add_edit_command(m, label="保存", accelerator="Ctrl+S",
                               command=lambda: self._emit("save_scenario"))
        self._add_edit_command(m, label="另存为", accelerator="Ctrl+Shift+S",
                               command=lambda: self._emit("save_scenario_as"))
        m.add_separator()
        m.add_command(label="退出", command=lambda: self._emit("quit"))

    def _build_edit_menu(self, m):
        self._edit_menu = m
        # 撤销/重做也是编辑类项：统一登记，state 由 set_edit_state 动态控
        self._add_edit_command(m, label="撤销", accelerator="Ctrl+Z",
                               command=lambda: self._emit("undo"))
        self._add_edit_command(m, label="重做", accelerator="Ctrl+Shift+Z",
                               command=lambda: self._emit("redo"))

    def _build_game_menu(self, m):
        m.add_command(label="新游戏", command=lambda: self._emit("new_game"))
        m.add_command(label="读取存档", command=lambda: self._emit("load_game"))
        m.add_command(label="保存存档", command=lambda: self._emit("save_game"))
        m.add_separator()
        m.add_command(label="游戏设置", command=lambda: self._emit("settings"))
        m.add_separator()
        m.add_command(label="退出", command=lambda: self._emit("quit"))

    def _build_faction_menu(self, m):
        internal = tk.Menu(m, tearoff=0)
        internal.add_command(label="内政 · 开发",
                             command=lambda: self._emit("internal_develop"))
        internal.add_command(label="内政 · 商业",
                             command=lambda: self._emit("internal_trade"))
        internal.add_command(label="内政 · 农业",
                             command=lambda: self._emit("internal_farm"))
        m.add_cascade(label="内政", menu=internal)

        military = tk.Menu(m, tearoff=0)
        military.add_command(label="征兵", command=lambda: self._emit("military_recruit"))
        military.add_command(label="训练", command=lambda: self._emit("military_train"))
        military.add_command(label="出征", command=lambda: self._emit("military_expedition"))
        m.add_cascade(label="军事", menu=military)

        diplomacy = tk.Menu(m, tearoff=0)
        diplomacy.add_command(label="同盟", command=lambda: self._emit("diplomacy_ally"))
        diplomacy.add_command(label="停战", command=lambda: self._emit("diplomacy_truce"))
        diplomacy.add_command(label="劝降", command=lambda: self._emit("diplomacy_surrender"))
        m.add_cascade(label="外交", menu=diplomacy)

        m.add_separator()
        m.add_command(label="结束本回合", command=lambda: self._emit("end_turn"))

    def _build_order_menu(self, m):
        m.add_command(label="移动", command=lambda: self._emit("order_move"))
        m.add_command(label="攻击", command=lambda: self._emit("order_attack"))
        m.add_command(label="计略", command=lambda: self._emit("order_scheme"))
        m.add_command(label="待机", command=lambda: self._emit("order_hold"))

    def _build_view_menu(self, m):
        m.add_command(label="地图缩放 · 放大",
                      command=lambda: self._emit("view_zoom_in"))
        m.add_command(label="地图缩放 · 缩小",
                      command=lambda: self._emit("view_zoom_out"))
        m.add_command(label="地图复位", command=lambda: self._emit("view_reset"))
        m.add_separator()
        m.add_command(label="城市列表", command=lambda: self._emit("view_cities"))
        m.add_command(label="人物列表", command=lambda: self._emit("view_characters"))
        m.add_command(label="部队列表", command=lambda: self._emit("view_troops"))

    def _build_help_menu(self, m):
        m.add_command(label="操作说明", command=lambda: self._emit("help_manual"))
        m.add_command(label="关于", command=lambda: self._emit("help_about"))

    # ==========================================================
    # 编辑模式控制
    # ==========================================================
    def set_edit_state(self, can_undo, can_redo):
        """编辑菜单撤销/重做的置灰状态。由 MainWindow 主动调用。"""
        menu = getattr(self, "_edit_menu", None)
        if menu is None:
            return
        e = self._edit_enabled
        menu.entryconfig(0, state="normal" if (can_undo and e) else "disabled")
        menu.entryconfig(1, state="normal" if (can_redo and e) else "disabled")

    def set_edit_enabled(self, enabled):
        """★ 按 APP_MODE 统一启用/禁用所有登记过的编辑类菜单项。

        由 MainWindow._build_layout 调用一次；将来切到游戏模式时，
        只要 APP_MODE 变成 MODE_GAME，这里就会把所有编辑入口一并置灰。
        """
        self._edit_enabled = bool(enabled)
        for menu, index in self._edit_entries:
            menu.entryconfig(index, state="normal" if enabled else "disabled")

    def set_game_mode(self, enabled):
        """enabled=False 时禁用「进行」按钮。"""
        self.end_turn_btn.configure(
            state="normal" if enabled else "disabled")

    # ==========================================================
    # 数据刷新
    # ==========================================================
    def _start_refresh(self):
        self._refresh()
        self.after(_REFRESH_INTERVAL_MS, self._start_refresh)

    def _refresh(self):
        for key, _label, value_text in self.game_state.get_display_items():
            entry = self.items.get(key)
            if entry:
                entry[1].set(value_text)