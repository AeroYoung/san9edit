# -*- coding: utf-8 -*-
"""通用列表面板基类。

4 个 panel（据点 / 人物 / 势力 / 部队）共享这套基础设施：
列表（Treeview）、排序、分组、搜索、多选、右键菜单、双向定位。

具体 panel 只写配置：
    COLUMNS / NAME_COLUMN / GROUP_DIMS / DEFAULT_GROUP / PRIORITY_NAME
    CUSTOM_GROUPING + build_groups()   —— 固定分组（势力）
    fetch_rows() / context_menu_items() / row_key() / locate_on_map()
"""

import logging
import tkinter as tk
from tkinter import ttk

from .columns import Column
from .model import Group
from .group_bar import GroupBar
from .search_bar import SearchBar
from .sorting import sort_rows
from .grouping import build_tree
from .context_menu import MenuItem, MenuContext, build_menu

logger = logging.getLogger(__name__)


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
    GROUP_TITLE_COUNT: bool = True   # True → 组头显示「组名（N）」叶子行数
    KEEP_VIEW_ON_EDIT: bool = False  # True → 编辑后的 refresh(keep_view=True) 走就地更新
    edit_session = None              # ★ 由 SidePanel.set_edit_session 注入

    def __init__(self, master, game_state, map_controller=None):
        super().__init__(master)
        self.game_state = game_state
        self.map_controller = map_controller

        self._sort_key = None
        self._sort_desc = False
        self._item_rows = {}         # tree item id -> row
        self._row_items = {}         # row_key -> tree item id
        self._item_keys = {}         # tree item id -> 结构 key（组=路径元组 / 行=("row", row_key)）
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
        self._item_rows = {}
        self._row_items = {}
        self._item_keys = {}

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
        logger.debug("排序：%s %s", key, "降序" if self._sort_desc else "升序")
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
            row_priority=self.row_priority(group_keys),
            title_count=self.GROUP_TITLE_COUNT,
        )

    # ==========================================================
    # 刷新
    # ==========================================================
    def refresh(self, keep_view=False):
        """刷新。

        keep_view=True 且面板声明 KEEP_VIEW_ON_EDIT → 就地更新（不重建 Treeview，
        保持滚动位置 / 选中项 / 分组展开状态）；否则整表重建。

        就地更新异常时退回整表重建（只丢视图状态，不丢功能），否则登记表一旦写脏，
        后续每次刷新都会继续报错。
        """
        if keep_view and self.KEEP_VIEW_ON_EDIT:
            try:
                if self._reconcile():
                    return
            except Exception:
                logger.warning("就地刷新失败，退回整表重建：%s",
                               type(self).__name__, exc_info=True)
        self._rebuild()

    def _rebuild(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._item_rows = {}
        self._row_items = {}
        self._item_keys = {}
        self._before_refresh()

        rows = self._apply_search(self.fetch_rows())
        logger.debug("刷新 %s：%d 行", type(self).__name__, len(rows))
        groups = self._build_groups(rows)
        if groups is None:
            if self._sort_key:
                rows = sort_rows(rows, self._column_index(),
                                 self._sort_key, self._sort_desc)
            for r in rows:
                self._insert_row("", r)
        else:
            self._insert_group_nodes("", groups)

    def _insert_group_nodes(self, parent, groups, parent_key=()):
        for g in groups:
            gkey = parent_key + (g.title,)
            gid = self.tree.insert(parent, "end",
                                   text=g.label(), open=g.open, tags=g.tags)
            self._item_keys[gid] = gkey
            if g.has_subgroups():
                self._insert_group_nodes(gid, g.children, gkey)
            else:
                for r in g.children:
                    self._insert_row(gid, r, row_tag=g.row_tag)

    def _row_tags(self, row, row_tag=None):
        """行 tag = 组给的 row_tag + 面板自定义 tag（row_tags 钩子）。"""
        tags = []
        if row_tag:
            tags.append(row_tag)
        tags.extend(self.row_tags(row) or ())
        return tuple(tags)

    def _insert_row(self, parent, row, row_tag=None):
        values = [c.value(row) for c in self._visible_columns]
        text = self.NAME_COLUMN.value(row) if self.NAME_COLUMN is not None else ""
        kwargs = {}
        tags = self._row_tags(row, row_tag)
        if tags:
            kwargs["tags"] = tags
        if self.NAME_COLUMN is not None and self.NAME_COLUMN.image:
            img = self.NAME_COLUMN.image(row)
            if img is not None:
                kwargs["image"] = img
        item = self.tree.insert(parent, "end", text=text, values=values, **kwargs)
        self._item_rows[item] = row
        key = self.row_key(row)
        if key is not None:
            self._row_items[key] = item
            self._item_keys[item] = ("row", key)

    # ==========================================================
    # 就地刷新（不重建 Treeview）
    # ==========================================================
    def _reconcile(self):
        """按 结构 key 复用已有 item，就地更新文本 / 值 / tag / 位置。

        保持：滚动位置（锚定原顶部条目）、选中项、分组展开状态。
        返回 False 表示无法就地（表格为空 / 名称列带图片）→ 调用方退回整表重建。
        """
        if not self.tree.get_children(""):
            return False
        if self.NAME_COLUMN is not None and self.NAME_COLUMN.image:
            return False          # 图片列需重建缓存，不走就地

        rows = self._apply_search(self.fetch_rows())
        by_key = {}
        for r in rows:
            by_key[self.row_key(r)] = r

        anchor_key = self._anchor_key(by_key)
        yview = self.tree.yview()
        target = self._target_specs(rows)

        # _item_keys 是 {item: key}；这里要按 key 取 item，反向建一份
        existing = {key: item for item, key in self._item_keys.items()}
        wanted = {spec["key"] for spec in target}
        for key, item in existing.items():
            if key in wanted:
                continue
            if self.tree.exists(item):
                self.tree.delete(item)
            self._forget_item(item)   # 随父组被连带删掉的，也要清登记

        # ★ 删组会连带删掉组内行：这些行的 key 仍可能在新结构里（只是换了父组），
        #   但 item 已经不是活的 → 从 existing 里剔除，让它们走「新建」分支。
        #   不剔的话 tree.item() 会抛 TclError: Item xxx not found。
        for item, key in list(self._item_keys.items()):
            if not self.tree.exists(item):
                existing.pop(key, None)
                self._forget_item(item)

        pos = {}                  # parent item -> 下一个子项序号
        for spec in target:
            parent_item = "" if not spec["parent"] else existing.get(spec["parent"])
            if spec["parent"] and not parent_item:
                continue          # 父组缺失（异常数据）→ 跳过该条
            item = existing.get(spec["key"])
            if item is None:
                item = self._insert_spec(parent_item, spec)
                existing[spec["key"]] = item
            else:
                self._update_spec(item, spec)
            self._item_keys[item] = spec["key"]
            index = pos.get(parent_item, 0)
            if self.tree.parent(item) != parent_item \
                    or self.tree.index(item) != index:
                self.tree.move(item, parent_item, index)
            pos[parent_item] = index + 1
            if spec["kind"] == "row":
                self._item_rows[item] = spec["row"]
                self._row_items[spec["key"][1]] = item

        self._restore_view(anchor_key, existing, yview)
        logger.debug("就地刷新 %s：%d 条", type(self).__name__, len(target))
        return True

    def _insert_spec(self, parent_item, spec):
        if spec["kind"] == "group":
            return self.tree.insert(parent_item, "end", text=spec["text"],
                                    open=spec["open"], tags=spec["tags"])
        kwargs = {}
        if spec["tags"]:
            kwargs["tags"] = spec["tags"]
        return self.tree.insert(parent_item, "end", text=spec["text"],
                                values=spec["values"], **kwargs)

    def _update_spec(self, item, spec):
        if spec["kind"] == "group":
            self.tree.item(item, text=spec["text"], tags=spec["tags"])
        else:
            self.tree.item(item, text=spec["text"], values=spec["values"],
                           tags=spec["tags"])

    def _forget_item(self, item):
        self._item_rows.pop(item, None)
        key = self._item_keys.pop(item, None)
        if key and key[0] == "row":
            self._row_items.pop(key[1], None)

    def _target_specs(self, rows):
        """目标结构（前序展开）：[spec]，spec = {key, kind, parent, text, values, tags, row, open}"""
        groups = self._build_groups(rows)
        out = []
        if groups is None:
            if self._sort_key:
                rows = sort_rows(rows, self._column_index(),
                                 self._sort_key, self._sort_desc)
            for r in rows:
                out.append(self._row_spec((), r))
            return out
        self._collect_specs(groups, (), out)
        return out

    def _collect_specs(self, groups, parent_key, out):
        for g in groups:
            gkey = parent_key + (g.title,)
            out.append({
                "key": gkey, "kind": "group", "parent": parent_key,
                "text": g.label(), "values": None, "tags": tuple(g.tags),
                "row": None, "open": g.open,
            })
            if g.has_subgroups():
                self._collect_specs(g.children, gkey, out)
            else:
                for r in g.children:
                    out.append(self._row_spec(gkey, r, g.row_tag))

    def _row_spec(self, parent_key, row, row_tag=None):
        text = self.NAME_COLUMN.value(row) if self.NAME_COLUMN is not None else ""
        return {
            "key": ("row", self.row_key(row)), "kind": "row", "parent": parent_key,
            "text": text, "values": [c.value(row) for c in self._visible_columns],
            "tags": self._row_tags(row, row_tag), "row": row, "open": None,
        }

    def _anchor_key(self, by_key):
        """滚动锚点：从可见区顶部往下，取第一个「位置稳定」的条目。

        组头位置稳定；数据行只在内容未变时才算（内容变了它会移出原位）——
        原顶行被改了就让位给下一行，依次类推。
        """
        item = self.tree.identify_row(1)
        if not item:
            children = self.tree.get_children("")
            item = children[0] if children else None
        guard = 0
        while item and guard < 500:
            guard += 1
            key = self._item_keys.get(item)
            if key is not None:
                if key[0] != "row":
                    return key
                if self._item_rows.get(item) == by_key.get(key[1]):
                    return key
            item = self.tree.next(item)
        return None

    def _restore_view(self, anchor_key, existing, yview):
        """把滚动位置还原到锚点条目（不可用则还原到原滚动比例）。

        Treeview 的行高一致 →「锚点序号 / 可见条目总数」就是它该在的滚动比例，
        用 yview_moveto 把锚点顶回可见区首行。
        （Treeview.yview(item) 不接受 item 参数，会抛 TclError。）
        """
        item = existing.get(anchor_key) if anchor_key else None
        index, total = self._visible_pos(item)
        if index is not None and total > 1:
            self.tree.yview_moveto(min(1.0, index / total))
            return
        self.tree.yview_moveto(yview[0])

    def _visible_pos(self, target):
        """(target 在可见顺序里的序号, 可见条目总数)。不可见 / 不在树里 → (None, 总数)。

        只统计当前展开可见的条目（折叠组的子项不计）。
        """
        if target is None or not self.tree.exists(target):
            return None, 0
        children = self.tree.get_children("")
        item = children[0] if children else None
        index = None
        total = 0
        while item:
            if item == target:
                index = total
            total += 1
            item = self.tree.next(item)
        return index, total

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
        # 非编辑模式（无 session）→ 带 edit 标识的项统一置灰
        menu = build_menu(self, items,
                          edit_enabled=self.edit_session is not None)
        self._menus.append(menu)
        restore_focus = self._current_focus()
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
            # ★ 菜单关闭后键盘焦点会留在菜单窗口上（focus_get() 变 None），
            #   之后所有快捷键（Ctrl+S / Ctrl+Z…）都会失效 —— 还给原控件
            if restore_focus is not None and restore_focus.winfo_exists():
                restore_focus.focus_set()

    def _current_focus(self):
        """当前键盘焦点控件；没有焦点 → 退回列表本身（右键后仍能继续用键盘）。"""
        try:
            widget = self.winfo_toplevel().focus_get()
        except Exception:
            return self.tree
        return widget if widget is not None else self.tree

    # ==========================================================
    # 双向定位
    # ==========================================================
    def scroll_to_row(self, key):
        """反向定位（地图 → 列表）：滚动到 key 对应行，展开祖先，选中。"""
        item = self._row_items.get(key)
        if item is None:
            logger.debug("反向定位失败：%s 无对应行", key)
            return
        logger.debug("反向定位：%s", key)
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

    def _notify_edit(self, keep_view=False):
        """向上找 SidePanel 的 on_panel_edit。

        keep_view=True → 请求就地刷新（只有 KEEP_VIEW_ON_EDIT 的面板会采用）。
        """
        w = self.master
        while w is not None:
            hook = getattr(w, "on_panel_edit", None)
            if callable(hook):
                hook(keep_view=keep_view)
                return
            w = getattr(w, "master", None)
        self.refresh(keep_view=keep_view)

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
        logger.debug("重载列：%s", type(self).__name__)
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

    def row_priority(self, group_keys):
        """叶子行的优先排序键（在用户列排序之前生效）。无 → None。"""
        return None

    def row_tags(self, row):
        """该行额外的 Treeview tag（如未登场整行着色）。子类覆盖。"""
        return ()

    def row_key(self, row):
        return getattr(row, "id", None) or getattr(row, "name", None)
