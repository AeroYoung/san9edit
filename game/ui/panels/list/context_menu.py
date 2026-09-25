# -*- coding: utf-8 -*-
"""右键菜单：从配置构建，支持分隔符 / 子菜单 / 动态启用禁用。"""

import tkinter as tk
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional


@dataclass
class MenuItem:
    label: str = ""
    command: Optional[Callable[[], None]] = None
    enabled: bool = True
    submenu: Optional[List["MenuItem"]] = None
    separator: bool = False
    edit: bool = False       # ★ 编辑类入口标识：非编辑模式下由 build_menu 统一禁用

    @classmethod
    def sep(cls):
        return cls(separator=True)


@dataclass
class MenuContext:
    """右键菜单上下文：右键那一行 + 所有选中行。

    定位类操作（定位到地图）用 right_click_row，
    批量类操作（情报）用 selected_rows。
    """
    right_click_row: Any = None
    selected_rows: List[Any] = field(default_factory=list)


def build_menu(parent, items, edit_enabled=True):
    """把 MenuItem 列表递归构建成 tk.Menu。

    edit_enabled=False 时，所有带 edit 标识的项统一置灰（非编辑模式）。
    """
    menu = tk.Menu(parent, tearoff=0)
    for it in items:
        if it.separator:
            menu.add_separator()
        elif it.submenu:
            sub = build_menu(menu, it.submenu, edit_enabled)
            menu.add_cascade(label=it.label, menu=sub,
                             state=_state(_enabled(it, edit_enabled)))
        else:
            menu.add_command(label=it.label, command=it.command,
                             state=_state(_enabled(it, edit_enabled)))
    return menu


def _enabled(item, edit_enabled):
    """编辑类项在非编辑模式下统一禁用。"""
    if item.edit and not edit_enabled:
        return False
    return item.enabled


def _state(enabled):
    return "normal" if enabled else "disabled"
