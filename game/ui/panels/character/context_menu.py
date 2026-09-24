# -*- coding: utf-8 -*-
"""人物面板右键菜单。"""

import tkinter as tk


def popup(parent, event, row, controller, on_intel, tree=None):
    menu = tk.Menu(parent, tearoff=0)

    menu.add_command(label=row.display_name, state="disabled")
    menu.add_separator()
    menu.add_command(label="人物情报",
                     command=lambda: on_intel("character", row))
    menu.add_command(label="复制编号",
                     command=lambda: _copy_id(parent, row.id))
    menu.add_separator()
    menu.add_command(label="定位到据点",
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


def _copy_id(parent, cid):
    try:
        parent.clipboard_clear()
        parent.clipboard_append(cid)
    except Exception:
        pass


def _set_all_open(tree, open_):
    def walk(parent):
        for item in tree.get_children(parent):
            if tree.get_children(item):
                tree.item(item, open=open_)
            walk(item)
    walk("")