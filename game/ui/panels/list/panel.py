# -*- coding: utf-8 -*-
"""通用列表面板基类。

4 个 panel（据点 / 人物 / 势力 / 部队）共享这套基础设施：
列表（Treeview）、排序、分组、搜索、多选、右键菜单、双向定位。

具体 panel 只写配置：
    COLUMNS / NAME_COLUMN / GROUP_DIMS / DEFAULT_GROUP / PRIORITY_NAME
    CUSTOM_GROUPING + build_groups()   —— 固定分组（势力）
    fetch_rows() / context_menu_items() / row_key() / locate_on_map()
"""

import tkinter as tk
from tkinter import ttk

from .columns import Column
from .model import Group
from .group_bar import GroupBar
from .search_bar import SearchBar
from .sorting import sort_rows
from .grouping import build_tree
from .context_menu import MenuItem, MenuContext, build_menu


class GenericListPanel(ttk.Frame):
    # ==========================================================
    # 子类覆盖的配置
    # ==========================================================
    COLUMNS: tuple = ()
    NAME_COLUMN: Column = None       # #0 列（名称列）
    GROUP_DIMS: dict = {}            # key -> (显示名, 取值函数)
    DEFAULT_GROUP: tuple = ()        # 默认选中的分组
    PRIORITY_NAME: str = None        # 置顶组名（只最外层）
    CUSTOM_GROUPING: bool = False    # True = 用 build_groups() 覆盖默认维度分组
    edit_session = None              # ★ 由 SidePanel.set_edit_session 注入

    def __init__(self, master, game_state, map_controller=None):
        super().__init__(master)
        self.game_state = game_state
        self.map_controller = map_controller

        self._sort_key = None
        self._sort_desc = False
        self._item_rows = {}         # tree item id -> row
        self._row_items = {}         # row_key -> tree item id
        self._search_query = ""
        self._syncing = False        # 反向定位防递归
        self._menus = []             # 持有菜单引用防 GC
        # ★ 按 PANEL_COLUMNS 解析可见列（先于 _build_ui）
        self._visible_columns, self._visible_name = self._resolve_columns()
        
        self._build_ui()
        self.refresh()

    # ==========================================================
    # UI
    # ==========================================================
    def _build_ui(self):
        # 搜索框
        self.search_bar = SearchBar(self, on_change=self._on_search_change)
        self.search_bar.pack(fill="x", padx=2, pady=(2, 0))

        # 分组条（自定义分组时不用）
        if not self.CUSTOM_GROUPING and self.GROUP_DIMS:
            bar = ttk.Frame(self)
            bar.pack(fill="x", padx=2, pady=(2, 0))
            self.group_bar = GroupBar(
                bar,
                dims={k: v[0] for k, v in self.GROUP_DIMS.items()},
                on_change=self.refresh,
                initial_selected=list(self.DEFAULT_GROUP),
            )
            self.group_bar.pack(side="left", fill="x", expand=True)

        # 表体（可重建）
        self._body = ttk.Frame(self)
        self._body.pack(fill="both", expand=True, padx=2, pady=2)
        self._build_tree_in(self._body)

    def _build_tree_in(self, body):
        """在 body 里构建 Treeview + 滚动条。可被 reload_columns 复用。"""
        for w in body.winfo_children():
            w.destroy()

        cols = [c.key for c in self._visible_columns]
        self.tree = ttk.Treeview(
            body, columns=cols, show="tree headings", selectmode="extended",
        )

        if self.NAME_COLUMN is not None:
            self.tree.heading(
                "#0", text=self.NAME_COLUMN.title,
                command=lambda: self._on_heading_click(self.NAME_COLUMN.key),
            )
            self.tree.column("#0", width=self.NAME_COLUMN.width,
                             anchor=self.NAME_COLUMN.anchor, stretch=False)

        for c in self._visible_columns:
            self.tree.heading(c.key, text=c.title,
                              command=lambda k=c.key: self._on_heading_click(k))
            self.tree.column(c.key, width=c.width, anchor=c.anchor, stretch=False)

        vsb = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(body, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)

        self.tree.tag_configure("group", background="#F3F4F6",
                                font=("", 9, "bold"))
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<Button-2>", self._on_right_click)
        self.tree.bind("<Control-a>", self._on_select_all)

        # 子类自定义 tag（faction_panel 有 _configure_tags）
        hook = getattr(self, "_configure_tags", None)
        if callable(hook):
            hook()

    # ==========================================================
    # 搜索
    # ==========================================================
    def _on_search_change(self):
        self._search_query = self.search_bar.query()
        self.refresh()

    def _apply_search(self, rows):
        tokens = self.search_bar.parse_query(self._search_query)
        if not tokens:
            return rows
        return [r for r in rows if self._matches(r, tokens)]

    def _matches(self, row, tokens):
        return all(self._match_one(row, tok) for tok in tokens)

    def _match_one(self, row, tok):
        if self.NAME_COLUMN is not None \
                and self._value_contains(self.NAME_COLUMN.value(row), tok):
            return True
        for c in self._visible_columns:
            if self._value_contains(c.value(row), tok):
                return True
        return False

    @staticmethod
    def _value_contains(v, tok):
        return v is not None and tok in str(v).lower()

    # ==========================================================
    # 排序 / 分组
    # ==========================================================
    def _on_heading_click(self, key):
        if self._sort_key == key:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_key = key
            self._sort_desc = False
        self.refresh()

    def _column_index(self):
        idx = {c.key: c for c in self._visible_columns}
        if self.NAME_COLUMN is not None:
            idx[self.NAME_COLUMN.key] = self.NAME_COLUMN
        return idx

    def _build_groups(self, rows):
        if self.CUSTOM_GROUPING:
            return self.build_groups(rows)
        group_keys = self.group_bar.selected() if hasattr(self, "group_bar") else []
        if not group_keys:
            return None
        return build_tree(
            rows, self.GROUP_DIMS, group_keys,
            sort_key=self._sort_key, sort_desc=self._sort_desc,
            columns_by_key=self._column_index(),
            priority_name=self.priority_name(),
        )

    # ==========================================================
    # 刷新
    # ==========================================================
    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._item_rows = {}
        self._row_items = {}
        self._before_refresh()

        rows = self._apply_search(self.fetch_rows())
        groups = self._build_groups(rows)
        if groups is None:
            if self._sort_key:
                rows = sort_rows(rows, self._column_index(),
                                 self._sort_key, self._sort_desc)
            for r in rows:
                self._insert_row("", r)
        else:
            self._insert_group_nodes("", groups)

    def _insert_group_nodes(self, parent, groups):
        for g in groups:
            gid = self.tree.insert(parent, "end",
                                   text=g.title, open=g.open, tags=g.tags)
            if g.has_subgroups():
                self._insert_group_nodes(gid, g.children)
            else:
                for r in g.children:
                    self._insert_row(gid, r, row_tag=g.row_tag)

    def _insert_row(self, parent, row, row_tag=None):
        values = [c.value(row) for c in self._visible_columns]
        text = self.NAME_COLUMN.value(row) if self.NAME_COLUMN is not None else ""
        kwargs = {}
        if row_tag:
            kwargs["tags"] = (row_tag,)
        if self.NAME_COLUMN is not None and self.NAME_COLUMN.image:
            img = self.NAME_COLUMN.image(row)
            if img is not None:
                kwargs["image"] = img
        item = self.tree.insert(parent, "end", text=text, values=values, **kwargs)
        self._item_rows[item] = row
        key = self.row_key(row)
        if key is not None:
            self._row_items[key] = item

    # ==========================================================
    # 右键菜单
    # ==========================================================
    def _on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        row = self._item_rows.get(item)
        if row is None:
            return
        # 右键的行不在选中集时，单选它；否则保留多选
        if item not in self.tree.selection():
            self.tree.selection_set(item)

        ctx = MenuContext(
            right_click_row=row,
            selected_rows=self._selected_rows(),
        )
        items = self.context_menu_items(ctx)
        if not items:
            return
        self._show_context_menu(event, items)

    def _selected_rows(self):
        return [self._item_rows[i] for i in self.tree.selection()
                if i in self._item_rows]

    def _on_select_all(self, event=None):
        """Ctrl+A：全选所有数据行（不含组头）。"""
        self.tree.selection_set(list(self._item_rows.keys()))
        return "break"

    def _show_context_menu(self, event, items):
        menu = build_menu(self, items)
        self._menus.append(menu)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ==========================================================
    # 双向定位
    # ==========================================================
    def scroll_to_row(self, key):
        """反向定位（地图 → 列表）：滚动到 key 对应行，展开祖先，选中。"""
        item = self._row_items.get(key)
        if item is None:
            return
        self._syncing = True
        try:
            self._expand_ancestors(item)
            self.tree.see(item)
            self.tree.selection_set(item)
        finally:
            self._syncing = False

    def _expand_ancestors(self, item):
        parent = self.tree.parent(item)
        while parent:
            self.tree.item(parent, open=True)
            parent = self.tree.parent(parent)

    def locate_on_map(self, row):
        """列表 → 地图：默认按 row.node_id / coords 定位。子类可覆盖。"""
        if self._syncing or self.map_controller is None:
            return
        node_id = getattr(row, "node_id", None)
        coords = getattr(row, "coords", None)
        if node_id:
            self.map_controller.fit_to_node(node_id, fallback_lonlat=coords or None)

    def _toggle_all(self, open_):
        def walk(parent):
            for item in self.tree.get_children(parent):
                if self.tree.get_children(item):
                    self.tree.item(item, open=open_)
                walk(item)
        walk("")

    # ==========================================================
    # 编辑会话
    # ==========================================================
    def _open_dialog(self, dlg_factory):
        """向上找带 open_edit_dialog 的对象（SidePanel 转发给 MainWindow）。"""
        w = self.master
        while w is not None:
            hook = getattr(w, "open_edit_dialog", None)
            if callable(hook):
                return hook(dlg_factory)
            w = getattr(w, "master", None)
        # 兜底：直接开
        return dlg_factory()

    def _notify_edit(self):
        """向上找 SidePanel 的 on_panel_edit。"""
        w = self.master
        while w is not None:
            hook = getattr(w, "on_panel_edit", None)
            if callable(hook):
                hook()
                return
            w = getattr(w, "master", None)
        self.refresh()

    # ==========================================================
    # 列配置（PANEL_COLUMNS）
    # ==========================================================
    def _resolve_columns(self):
        """读 style.PANEL_COLUMNS，返回 (可见列 tuple, name_column)。

        规则：
          - order 中的 key 优先排前面，未出现的按声明顺序追加
          - hidden 中的列被过滤（NAME_COLUMN 不参与）
          - order / hidden 里的未知 key 忽略
        子类没声明 PANEL_KEY 时，退化为直接返回类属性 COLUMNS。
        """
        panel_key = getattr(self, "PANEL_KEY", None)
        if not panel_key:
            return self.COLUMNS, self.NAME_COLUMN

        try:
            from game.config.style import PANEL_COLUMNS
        except Exception:
            return self.COLUMNS, self.NAME_COLUMN

        cfg = (PANEL_COLUMNS or {}).get(panel_key) or {}
        order = list(cfg.get("order") or [])
        hidden = set(cfg.get("hidden") or [])

        by_key = {c.key: c for c in self.COLUMNS}
        arranged = [by_key[k] for k in order if k in by_key]
        seen = set(order)
        for c in self.COLUMNS:
            if c.key not in seen:
                arranged.append(c)

        visible = tuple(c for c in arranged if c.key not in hidden)
        return visible, self.NAME_COLUMN

    def reload_columns(self):
        """设置保存后由 MainWindow 调用：重读配置，重建表格。"""
        self._visible_columns, self._visible_name = self._resolve_columns()
        # 若排序键已被隐藏，则清除排序状态
        if self._sort_key:
            visible_keys = {c.key for c in self._visible_columns}
            if self.NAME_COLUMN is not None:
                visible_keys.add(self.NAME_COLUMN.key)
            if self._sort_key not in visible_keys:
                self._sort_key = None
                self._sort_desc = False
        self._build_tree_in(self._body)
        self.refresh()

    # ==========================================================
    # 子类覆盖的钩子
    # ==========================================================
    def _before_refresh(self):
        """refresh 清空表格后、重建数据前调用（子类清理缓存）。"""

    def fetch_rows(self):
        return []

    def build_groups(self, rows):
        """自定义分组回调（CUSTOM_GROUPING=True 时调用）。"""
        return []

    def context_menu_items(self, ctx):
        return []

    def priority_name(self):
        return self.PRIORITY_NAME

    def row_key(self, row):
        return getattr(row, "id", None) or getattr(row, "name", None)
