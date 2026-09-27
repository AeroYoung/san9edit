# -*- coding: utf-8 -*-
"""可搜索下拉框：输入关键字实时过滤选项。

- 输入时下拉自动展开（用 ttk::combobox::Post 而非 <Down> 减少焦点跳走）
- normalize() 由调用方在收集值时触发，把非法输入纠正为合法选项
- set_values() 供动态替换选项集
"""
import tkinter as tk
from tkinter import ttk


class SearchableCombobox(ttk.Combobox):
    """可搜索下拉。输入关键字过滤；normalize() 把输入纠正为合法选项。

    规则（normalize 时）：
      - 文本恰是某选项      → 保留
      - 文本唯一匹配某选项  → 自动补全
      - 多匹配 / 无匹配     → 回退到上次有效值
    """

    def __init__(self, master, values=(), **kw):
        super().__init__(master, **kw)
        self._all_values = list(values)
        self.configure(values=self._all_values, state="normal")
        initial = self.get()
        self._last_valid = initial if initial in self._all_values else \
            (self._all_values[0] if self._all_values else "")
        self.bind("<KeyRelease>", self._on_key)
        self.bind("<<ComboboxSelected>>", self._on_selected)

    # ---------- 输入过滤 ----------
    def _on_key(self, event):
        # 导航键不触发过滤
        if event.keysym in ("Up", "Down", "Left", "Right", "Return",
                            "Escape", "Tab", "Home", "End",
                            "Prior", "Next", "Shift_L", "Shift_R",
                            "Control_L", "Control_R"):
            return
        text = self.get().strip()
        if not text:
            self.configure(values=self._all_values)
            return
        low = text.lower()
        matches = [v for v in self._all_values if low in v.lower()]
        self.configure(values=matches or self._all_values)
        # 延迟一帧再展开，避免和当前按键事件抢焦点
        self.after_idle(self._popdown)

    def _popdown(self):
        """展开下拉列表但不抢走输入框焦点（用户能接着打字）。"""
        try:
            self.tk.call("ttk::combobox::Post", self._w)
        except tk.TclError:
            # 兜底：某些 Tk 版本 / 平台没有该内部命令
            try:
                self.event_generate("<Down>")
                self.after_idle(self._refocus)
            except tk.TclError:
                pass

    def _refocus(self):
        try:
            self.focus_set()
            self.icursor("end")
        except tk.TclError:
            pass

    def _on_selected(self, event=None):
        self._last_valid = self.get()
        self.configure(values=self._all_values)

    # ---------- 公开 ----------
    def set_values(self, values):
        """替换整个选项集（例如势力列表变化时）。"""
        self._all_values = list(values)
        self.configure(values=self._all_values)

    def normalize(self):
        """把当前文本按规则纠正为合法选项，返回纠正后的文本。"""
        try:
            text = self.get().strip()
        except tk.TclError:
            return self._last_valid
        if text in self._all_values:
            self._last_valid = text
            return text
        matches = [v for v in self._all_values
                   if text and text.lower() in v.lower()]
        if len(matches) == 1:
            self.set(matches[0])
            self._last_valid = matches[0]
            return matches[0]
        self.set(self._last_valid)
        return self._last_valid