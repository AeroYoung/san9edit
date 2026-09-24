# -*- coding: utf-8 -*-
"""据点右键菜单。"""

import tkinter as tk


def popup(parent, event, row, controller, on_intel, tree=None):
    """弹出右键菜单。

    row        : NodeRow
    controller : MapController | None
    on_intel   : Callable[[kind, NodeRow], None]
    tree       : ttk.Treeview | None，用于「全部展开 / 全部折叠」
    """
    menu = tk.Menu(parent, tearoff=0)

    menu.add_command(label=row.name, state="disabled")
    menu.add_separator()
    menu.add_command(label="据点情报",
                     command=lambda: on_intel("node", row))
    menu.add_command(label="人物情报",
                     command=lambda: on_intel("character", row))
    menu.add_command(label="势力情报",
                     command=lambda: on_intel("faction", row))
    menu.add_separator()
    menu.add_command(label="定位到地图",
                     command=lambda: _locate(controller, row))

    if tree is not None:
        menu.add_separator()
        menu.add_command(label="全部展开",
                         command=lambda: _set_all_open(tree, True))
        menu.add_command(label="全部折叠",
                         command=lambda: _set_all_open(tree, False))

    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()


def _locate(controller, row):
    if controller is None or not row.node_id:
        return
    controller.fit_to_node(row.node_id, fallback_lonlat=row.coords or None)


def _set_all_open(tree, open_):
    """递归设置所有有子节点的项。"""
    def walk(parent):
        for item in tree.get_children(parent):
            if tree.get_children(item):
                tree.item(item, open=open_)
            walk(item)
    walk("")