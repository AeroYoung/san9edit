# -*- coding: utf-8 -*-
"""人物面板主类。

    [分组条：势力 / 所在 / 身份 / 性别]
    [Treeview: #0=姓名（字），其余 8 列可点列头排序]
"""

from tkinter import ttk

from .columns import COLUMNS, COLUMN_INDEX
from .model import CharacterRow
from .grouping import build_tree, GROUP_DIMS
from .group_bar import GroupBar
from .sorting import sort_rows
from .context_menu import popup as popup_context_menu


class CharacterPanel(ttk.Frame):
    def __init__(self, master, game_state, map_controller=None):
        super().__init__(master)
        self.game_state = game_state
        self.map_controller = map_controller

        self._sort_key = None
        self._sort_desc = False
        self._item_rows = {}

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=2, pady=(2, 0))
        self.group_bar = GroupBar(
            bar,
            dims={k: v[0] for k, v in GROUP_DIMS.items()},
            on_change=self.refresh,
            initial_selected=["faction"],
        )
        self.group_bar.pack(side="left", fill="x", expand=True)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=2, pady=2)

        cols = [c.key for c in COLUMNS]
        self.tree = ttk.Treeview(
            body, columns=cols, show="tree headings",
            selectmode="browse",
        )
        self.tree.heading("#0", text="姓名",
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

        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<Button-2>", self._on_right_click)

    def _on_heading_click(self, key):
        if self._sort_key == key:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_key = key
            self._sort_desc = False
        self.refresh()

    def _on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        row = self._item_rows.get(item)
        if row is None:
            return
        self.tree.selection_set(item)
        popup_context_menu(self, event, row, self.map_controller,
                           self._on_intel, tree=self.tree)

    def _on_intel(self, kind, row):
        print(f"[人物情报] kind={kind} id={row.id} {row.display_name}")

        def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._item_rows = {}

        world = getattr(self.game_state, "world", None)
        if world is None:
            return

        rows = [CharacterRow.from_character(c, world)
                for c in world.characters.values()]
        group_keys = self.group_bar.selected()

        # ★ 玩家势力组名（用于置顶）
        priority = self._player_faction_name(world)

        if group_keys:
            tree = build_tree(
                rows, group_keys,
                sort_key=self._sort_key, sort_desc=self._sort_desc,
                columns_by_key=COLUMN_INDEX,
                priority_name=priority,
            )
            self._insert_group_nodes("", tree)
        else:
            if self._sort_key:
                rows = sort_rows(rows, COLUMN_INDEX,
                                 self._sort_key, self._sort_desc)
            for r in rows:
                self._insert_row("", r)

    def _player_faction_name(self, world):
        """玩家势力的展示名；无则 None。"""
        pfid = getattr(world, "player_faction_id", None)
        if not pfid:
            return None
        f = world.faction(pfid)
        return f.name if f else None

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
                                text=row.display_name, values=values)
        self._item_rows[item] = row