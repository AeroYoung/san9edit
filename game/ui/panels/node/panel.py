# -*- coding: utf-8 -*-
"""据点面板主类。

    [分组条：势力 / 州 / 郡 / 类型 —— 点选顺序 = 嵌套顺序]
    [Treeview: #0=县名/组名，其余 7 列可点列头排序]
    [横向滚动条 + 竖向滚动条]
"""

from tkinter import ttk

from .columns import COLUMNS, COLUMN_INDEX
from .model import NodeRow
from .grouping import build_tree, GROUP_DIMS
from .group_bar import GroupBar
from .sorting import sort_rows
from .context_menu import popup as popup_context_menu


class NodePanel(ttk.Frame):
    def __init__(self, master, game_state, map_controller=None):
        super().__init__(master)
        self.game_state = game_state
        self.map_controller = map_controller

        self._sort_key = None       # None = 默认顺序
        self._sort_desc = False
        self._item_rows = {}        # Treeview item id -> NodeRow

        self._build_ui()
        self.refresh()

    # ==========================================================
    # UI
    # ==========================================================
    def _build_ui(self):
        # ---------- 分组条 ----------
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=2, pady=(2, 0))
        self.group_bar = GroupBar(
            bar,
            dims={k: v[0] for k, v in GROUP_DIMS.items()},
            on_change=self.refresh,
            initial_selected=["state", "county"],     # ★ 默认 州 > 郡
        )
        self.group_bar.pack(side="left", fill="x", expand=True)

        # ---------- 表体 ----------
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=2, pady=2)

        cols = [c.key for c in COLUMNS]
        self.tree = ttk.Treeview(
            body, columns=cols, show="tree headings", selectmode="browse",
        )
        # #0 列 = 县名 / 组名
        self.tree.heading("#0", text="县",
                          command=lambda: self._on_heading_click("name"))
        self.tree.column("#0", width=110, anchor="w", stretch=False)

        for c in COLUMNS:
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

        # 右键（Windows/Linux: Button-3; Mac: Button-2）
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<Button-2>", self._on_right_click)

    # ==========================================================
    # 排序
    # ==========================================================
    def _on_heading_click(self, key):
        if self._sort_key == key:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_key = key
            self._sort_desc = False
        self.refresh()

    # ==========================================================
    # 右键
    # ==========================================================
    def _on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        row = self._item_rows.get(item)
        if row is None:
            return
        self.tree.selection_set(item)
        popup_context_menu(self, event, row, self.map_controller, self._on_intel,
                   tree=self.tree)
        
    def _on_intel(self, kind, row):
        # 占位：先打印，将来接情报窗口
        print(f"[据点情报] kind={kind} node={row.node_id} {row.name}")

    # ==========================================================
    # 刷新
    # ==========================================================
    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._item_rows = {}

        world = getattr(self.game_state, "world", None)
        if world is None:
            return

        rows = [NodeRow.from_node(n, world) for n in world.nodes.values()]
        group_keys = self.group_bar.selected()

        if group_keys:
            tree = build_tree(
                rows, group_keys,
                sort_key=self._sort_key,
                sort_desc=self._sort_desc,
                columns_by_key=COLUMN_INDEX,
            )
            self._insert_group_nodes("", tree)
        else:
            if self._sort_key:
                rows = sort_rows(rows, COLUMN_INDEX,
                                 self._sort_key, self._sort_desc)
            for r in rows:
                self._insert_row("", r)

    def _insert_group_nodes(self, parent, nodes):
        for title, children in nodes:
            gid = self.tree.insert(parent, "end",
                                   text=title, open=True, tags=("group",))
            if children and isinstance(children[0], tuple):
                self._insert_group_nodes(gid, children)
            else:
                for r in children:
                    self._insert_row(gid, r)

    def _insert_row(self, parent, row):
        values = [col.value(row) for col in COLUMNS]
        item = self.tree.insert(parent, "end",
                                text=row.name, values=values)
        self._item_rows[item] = row