# -*- coding: utf-8 -*-
"""通用数据驱动编辑弹窗。

只认 Field.kind，不认业务实体。骨架中不出现「if 据点 elif 势力」这类分支。
校验走 Field 的 min/max，readonly 走 display_fn。
"""

import logging
import tkinter as tk
from tkinter import ttk, colorchooser

from game.ui.window_utils import center_on_parent

logger = logging.getLogger(__name__)


class EditDialog(tk.Toplevel):
    def __init__(self, master, fields, entity, world=None, title="编辑"):
        super().__init__(master)
        logger.debug("构建编辑弹窗：%s（%d 字段）", title, len(fields))
        self.title(title)
        self.resizable(False, False)
        # 相对主窗口（root）居中 + transient，而非相对右侧面板
        self._top = master.winfo_toplevel()
        self.transient(self._top)

        self.fields = fields
        self.entity = entity
        self.world = world
        self.ok = False

        self._vars = {}            # key -> tk.Variable
        self._old_values = {}      # key -> 原值（可编辑字段）
        self._label_to_value = {}  # key -> {label: value}（choice 字段）
        self._swatches = {}        # key -> 色块 Label（color 字段）
        self._err_label = None

        self._build(fields)
        self._build_buttons()

        self.bind("<Escape>", lambda e: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        # 尺寸确定后再居中（相对主窗口）
        self.update_idletasks()
        w = max(self.winfo_reqwidth(), 300)
        h = self.winfo_reqheight()
        center_on_parent(self, self._top, w, h)

        try:
            self.grab_set()
        except Exception:
            pass
        self.focus_set()

    # ============================================================
    # 构建
    # ============================================================
    def _build(self, fields):
        body = tk.Frame(self, padx=14, pady=12)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        for r, f in enumerate(fields):
            tk.Label(body, text=f.label + "：", anchor="e").grid(
                row=r, column=0, sticky="e", padx=(0, 8), pady=4)
            self._build_field(body, r, f)
            if f.hint:
                tk.Label(body, text=f.hint, fg="#888888",
                         font=("", 8)).grid(
                    row=r, column=2, sticky="w", padx=(8, 0))

    def _build_field(self, body, row, f):
        value = getattr(self.entity, f.key, f.default)

        if f.kind == "readonly":
            text = f.display_fn(value, self.world) if f.display_fn else str(value)
            tk.Label(body, text=text, anchor="w", fg="#333333").grid(
                row=row, column=1, sticky="w", pady=4)
            self._vars[f.key] = None
            return

        # 可编辑字段：记录旧值
        self._old_values[f.key] = value

        if f.kind == "bool":
            var = tk.BooleanVar(value=bool(value))
            tk.Checkbutton(body, variable=var).grid(
                row=row, column=1, sticky="w", pady=4)
            self._vars[f.key] = var
        elif f.kind == "choice":
            labels = [label for _v, label in f.options]
            value_by_label = {label: v for v, label in f.options}
            self._label_to_value[f.key] = value_by_label
            current_label = next(
                (label for v, label in f.options if v == value),
                labels[0] if labels else "")
            var = tk.StringVar(value=current_label)
            ttk.Combobox(body, textvariable=var, values=labels,
                         state="readonly", width=16).grid(
                row=row, column=1, sticky="w", pady=4)
            self._vars[f.key] = var
        elif f.kind == "color":
            self._build_color(body, row, f, value)
        else:  # int / str
            var = tk.StringVar(value=str(value))
            tk.Entry(body, textvariable=var, width=18).grid(
                row=row, column=1, sticky="w", pady=4)
            self._vars[f.key] = var

    def _build_color(self, body, row, f, value):
        cell = tk.Frame(body)
        cell.grid(row=row, column=1, sticky="w", pady=4)

        initial = str(value or "#888888")
        swatch = tk.Label(cell, width=4, bg=initial, relief="solid",
                          bd=1, cursor="hand2")
        swatch.pack(side="left", padx=(0, 6))
        self._swatches[f.key] = swatch

        hexvar = tk.StringVar(value=initial)
        ent = tk.Entry(cell, textvariable=hexvar, width=10)
        ent.pack(side="left")

        def _set(v):
            v = str(v or "").strip()
            if not v.startswith("#") or len(v) != 7:
                return
            swatch.configure(bg=v)
            hexvar.set(v)

        def _pick(_evt=None):
            _rgb, hexval = colorchooser.askcolor(
                color=hexvar.get() or "#000000",
                parent=self, title=f.label)
            if hexval:
                _set(hexval)

        def _on_commit(_evt=None):
            _set(hexvar.get())

        swatch.bind("<Button-1>", _pick)
        ent.bind("<Return>", _on_commit)
        ent.bind("<FocusOut>", _on_commit)
        self._vars[f.key] = hexvar

    def _build_buttons(self):
        bar = tk.Frame(self)
        bar.pack(fill="x", padx=14, pady=(0, 12))
        self._err_label = tk.Label(bar, text="", fg="#B03A2E", anchor="w")
        self._err_label.pack(side="left")
        tk.Button(bar, text="确定", width=8, command=self._on_ok).pack(
            side="right")
        tk.Button(bar, text="取消", width=8, command=self._cancel).pack(
            side="right", padx=(6, 0))

    # ============================================================
    # 校验 / 收集
    # ============================================================
    def _validate(self):
        for f in self.fields:
            if f.kind == "int":
                raw = self._vars[f.key].get().strip()
                try:
                    v = int(raw)
                except ValueError:
                    self._show_error(f"{f.label}：格式错误")
                    return False
                if f.min is not None and v < f.min:
                    self._show_error(f"{f.label}：不能小于 {f.min}")
                    return False
                if f.max is not None and v > f.max:
                    self._show_error(f"{f.label}：不能大于 {f.max}")
                    return False
        self._show_error("")
        return True

    def _show_error(self, text):
        if self._err_label is not None:
            self._err_label.configure(text=text)

    def _collect(self):
        values = {}
        for f in self.fields:
            if f.kind == "readonly" or not f.editable:
                continue
            values[f.key] = self._read_field(f)
        return values

    def _read_field(self, f):
        var = self._vars[f.key]
        if f.kind == "bool":
            return bool(var.get())
        if f.kind == "int":
            return int(var.get().strip())
        if f.kind == "choice":
            label = var.get()
            return self._label_to_value[f.key].get(label, label)
        return var.get()   # str / color

    # ============================================================
    # 结果
    # ============================================================
    def get_changed(self):
        """返回 (new_values, old_values)，只含真正变化的字段。"""
        new_values = self._collect()
        changed_new = {}
        changed_old = {}
        for k, v in new_values.items():
            old = self._old_values.get(k)
            if old != v:
                changed_new[k] = v
                changed_old[k] = old
        if changed_new:
            logger.debug("字段变更：%s",
                         {k: (self._old_values.get(k), v)
                          for k, v in changed_new.items()})
        return changed_new, changed_old

    # ============================================================
    # 确定 / 取消
    # ============================================================
    def _on_ok(self):
        if not self._validate():
            logger.warning("弹窗校验失败，拒绝提交")
            return
        self.ok = True
        self.destroy()
        logger.debug("弹窗确定")

    def _cancel(self):
        self.ok = False
        self.destroy()
        logger.debug("弹窗取消")
