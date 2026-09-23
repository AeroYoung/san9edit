# -*- coding: utf-8 -*-
"""窗口相关的小工具。"""

import tkinter as tk


def maximize(window):
    """让窗口最大化，兼容 Windows / Linux / macOS。"""
    try:
        window.state("zoomed")                    # Windows / 部分 Linux
        return
    except tk.TclError:
        pass
    try:
        window.attributes("-zoomed", True)        # 另一部分 Linux
        return
    except tk.TclError:
        pass
    # 兜底：手动铺满屏幕
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    window.geometry(f"{sw}x{sh}+0+0")


def center_on_parent(child, parent, width, height):
    """把 child 窗口相对 parent 窗口居中，并夹在屏幕内。

    child / parent 都是 Toplevel 或 Tk 实例。
    width / height 是 child 的期望尺寸（像素）。
    """
    parent.update_idletasks()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    pw = parent.winfo_width()
    ph = parent.winfo_height()

    x = px + (pw - width) // 2
    y = py + (ph - height) // 2

    # 避免跑出屏幕
    sw = child.winfo_screenwidth()
    sh = child.winfo_screenheight()
    x = max(0, min(x, sw - width))
    y = max(0, min(y, sh - height))

    child.geometry(f"{width}x{height}+{x}+{y}")