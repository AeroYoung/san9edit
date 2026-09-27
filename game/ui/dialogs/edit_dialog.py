# -*- coding: utf-8 -*-
"""通用数据驱动编辑弹窗。

只认 Field.kind，不认业务实体。骨架中不出现「if 据点 elif 势力」这类分支。
校验走 Field 的 min/max，readonly 走 display_fn。

两种可选形态（都保持数据驱动）：
    info_sections  只读信息块（(标题, 文本) 列表），放在字段上方 —— 情报/编辑同窗
    readonly=True  全部字段按只读渲染，按钮只剩「关闭」—— 非编辑模式的「XX情报」
    side_image     右侧竖图（头像路径）+ side_caption：势力编辑窗放君主头像用，
                   找不到图 / 没装 Pillow → 显示占位文字，不崩

分组与滚动（需求 §3.8 / §3.11 / §3.10）：
    sections  FieldGroup 元组，分组复用 CollapsibleSection，不另起弹窗框架
    scroll    True → 内容超出 MAX_BODY_H 时出现纵向滚动条

联动（需求 §3.8 独立/附庸）：
    on_change(key, value, dialog)  字段值变化时回调，由调用方决定启用/禁用别的字段
    set_field_enabled(key, flag)   启 / 禁某个字段的输入控件（禁用字段不参与校验）
"""

import logging
import tkinter as tk
from tkinter import ttk, colorchooser

from game.ui.window_utils import center_on_parent

logger = logging.getLogger(__name__)

MAX_BODY_H = 620            # 内容区最大高度（超出走滚动条）


class EditDialog(tk.Toplevel):
    def __init__(self, master, fields, entity, world=None, title="编辑",
                 info_sections=(), readonly=False,
                 side_image=None, side_caption=None,
                 sections=None, scroll=False, on_change=None):
        super().__init__(master)
        logger.debug("构建弹窗：%s（%d 字段，只读=%s，信息块=%d，分组=%d）",
                     title, len(fields), readonly, len(info_sections),
                     len(sections or ()))
        self.title(title)
        self.resizable(False, False)
        # 相对主窗口（root）居中 + transient，而非相对右侧面板
        self._top = master.winfo_toplevel()
        self.transient(self._top)

        self.sections = tuple(sections) if sections else ()
        # 分组给的是布局，字段表给的是取值 / 校验 —— 有分组时以分组为准，避免两处漂移
        self.fields = (tuple(f for g in self.sections for f in g.fields)
                       if self.sections else fields)
        self.entity = entity
        self.world = world
        self.ok = False
        self.readonly = readonly
        self._info_sections = tuple(info_sections)
        self._side_image = side_image
        self._side_caption = side_caption
        self._scroll = bool(scroll)
        self._on_change_hook = on_change
        self._link_busy = False    # 联动回调重入保护
        self._photo = None       # ★ 保引用，防 GC

        self._vars = {}            # key -> tk.Variable
        self._widgets = {}         # key -> 输入控件（set_field_enabled 用）
        self._disabled = set()     # 被联动禁用的字段 key（不参与校验 / 收集）
        self._old_values = {}      # key -> 原值（可编辑字段）
        self._label_to_value = {}  # key -> {label: value}（choice 字段）
        self._swatches = {}        # key -> 色块 Label（color 字段）
        self._err_label = None

        self._build(self.fields, self._info_sections)
        self._build_buttons()

        # 联动初值：让调用方把「当前值决定的启用/禁用状态」先摆正
        if self._on_change_hook is not None:
            for f in self.fields:
                if self._vars.get(f.key) is not None:
                    self._on_value_change(f.key)

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
    def _build(self, fields, info_sections=()):
        main = tk.Frame(self)
        main.pack(fill="both", expand=True)
        if self._side_image is not None or self._side_caption:
            self._build_side(main)          # 右侧头像（先 pack 的靠右）
        outer = tk.Frame(main, padx=14, pady=12)
        outer.pack(side="left", fill="both", expand=True)

        body = self._make_scroll_body(outer) if self._scroll else outer

        if self.sections:
            self._build_sections(body)
            return

        body.columnconfigure(1, weight=1)
        start = 0
        if info_sections:
            start = self._build_info(body, info_sections) + 1
            tk.Frame(body, bg="#DDDDDD", height=1).grid(
                row=start - 1, column=0, columnspan=3, sticky="ew", pady=8)

        for r, f in enumerate(fields, start=start):
            self._build_row(body, r, f)

    def _make_scroll_body(self, outer):
        """把内容区放进 Canvas，超出 MAX_BODY_H 时纵向滚动。返回内容 Frame。"""
        canvas = tk.Canvas(outer, width=560, height=MAX_BODY_H,
                           highlightthickness=0, bg=self.cget("bg"))
        bar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set)
        canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")

        body = tk.Frame(canvas, bg=self.cget("bg"))
        window = canvas.create_window((0, 0), window=body, anchor="nw")

        def _fit_inner(_evt=None):
            want = body.winfo_reqheight()
            canvas.configure(height=min(want, MAX_BODY_H),
                             scrollregion=canvas.bbox("all"))
            outer_width = canvas.winfo_width()
            if outer_width > 1:
                canvas.itemconfigure(window, width=outer_width)

        body.bind("<Configure>", _fit_inner)
        canvas.bind("<Configure>", _fit_inner)
        # 滚轮（Canvas 自己没有滚动条，绑在画布与内容上）
        for widget in (canvas, body):
            widget.bind("<MouseWheel>", lambda e: self._on_wheel(canvas, e))
        self._scroll_canvas = canvas
        return body

    @staticmethod
    def _on_wheel(canvas, event):
        canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def _build_sections(self, body):
        """分组布局：每组一个 CollapsibleSection，默认全部展开。"""
        from game.ui.widgets.collapsible import CollapsibleSection

        for group in self.sections:
            section = CollapsibleSection(body, group.title, desc=group.desc,
                                         expanded=True)
            section.pack(fill="x", pady=(0, 6))
            inner = section.body
            inner.columnconfigure(1, weight=1)
            row = 0
            if group.info:
                row = self._build_info(inner, group.info) + 1
                tk.Frame(inner, bg="#DDDDDD", height=1).grid(
                    row=row - 1, column=0, columnspan=3, sticky="ew", pady=6)
            for f in group.fields:
                self._build_row(inner, row, f)
                row += 1

    def _build_row(self, parent, row, f):
        tk.Label(parent, text=f.label + "：", anchor="e", bg=self.cget("bg")
                 ).grid(row=row, column=0, sticky="e", padx=(0, 8), pady=4)
        self._build_field(parent, row, f)
        if f.hint:
            tk.Label(parent, text=f.hint, fg="#888888",
                     font=("", 8), bg=self.cget("bg")).grid(
                row=row, column=2, sticky="w", padx=(8, 0))

    def _build_side(self, main):
        """右侧竖图（头像）：占位文字兜底，图与说明居中。"""
        from game.ui.portrait import load_thumbnail

        side = tk.Frame(main, padx=14, pady=12)
        side.pack(side="right", fill="y")
        box = tk.Frame(side, width=140, height=140,
                       highlightthickness=1,
                       highlightbackground="#CCCCCC")
        box.pack()
        box.pack_propagate(False)
        label = tk.Label(box, bg="#F5F5F5")
        label.pack(expand=True, fill="both")

        photo, note = load_thumbnail(self._side_image, 140, 140, master=self)
        if photo is not None:
            self._photo = photo
            label.configure(image=photo)
        else:
            label.configure(text=note or "（无头像）", fg="#999999",
                            font=("", 9), justify="center")
        if self._side_caption:
            tk.Label(side, text=self._side_caption, fg="#333333",
                     font=("", 9), wraplength=140, justify="center"
                     ).pack(pady=(6, 0))

    def _build_info(self, body, info_sections):
        """只读信息块：(标题, 文本) → 标题加粗 + 正文（可多行）。"""
        row = 0
        for title, text in info_sections:
            tk.Label(body, text=title, anchor="w", font=("", 9, "bold")
                     ).grid(row=row, column=0, columnspan=2, sticky="w",
                            pady=(6, 0))
            row += 1
            tk.Label(body, text=str(text), anchor="w", justify="left",
                     wraplength=520, fg="#333333"
                     ).grid(row=row, column=0, columnspan=2, sticky="w")
            row += 1
        return row

    def _build_field(self, parent, row, f):
        value = getattr(self.entity, f.key, f.default)

        if f.kind == "readonly" or self.readonly:
            text = (f.display_fn(value, self.world) if f.display_fn
                    else str(value))
            tk.Label(parent, text=text, anchor="w", fg="#333333",
                     bg=self.cget("bg")).grid(
                row=row, column=1, sticky="w", pady=4)
            self._vars[f.key] = None
            return

        # 可编辑字段：记录旧值
        self._old_values[f.key] = value

        if f.kind == "bool":
            var = tk.BooleanVar(value=bool(value))
            widget = tk.Checkbutton(parent, variable=var, bg=self.cget("bg"),
                                    activebackground=self.cget("bg"))
            widget.grid(row=row, column=1, sticky="w", pady=4)
            self._vars[f.key] = var
            self._widgets[f.key] = widget
        elif f.kind == "choice":
            labels = [label for _v, label in f.options]
            value_by_label = {label: v for v, label in f.options}
            self._label_to_value[f.key] = value_by_label
            current_label = next(
                (label for v, label in f.options if v == value),
                labels[0] if labels else "")
            var = tk.StringVar(value=current_label)
            widget = ttk.Combobox(parent, textvariable=var, values=labels,
                                  state="readonly", width=16)
            widget.grid(row=row, column=1, sticky="w", pady=4)
            self._vars[f.key] = var
            self._widgets[f.key] = widget
        elif f.kind == "color":
            self._build_color(parent, row, f, value)
        else:  # int / str
            var = tk.StringVar(value=str(value))
            widget = tk.Entry(parent, textvariable=var, width=18)
            widget.grid(row=row, column=1, sticky="w", pady=4)
            self._vars[f.key] = var
            self._widgets[f.key] = widget

        if self._on_change_hook is not None:
            self._vars[f.key].trace_add(
                "write", lambda *_a, k=f.key: self._on_value_change(k))

    def _build_color(self, body, row, f, value):
        cell = tk.Frame(body, bg=self.cget("bg"))
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
        self._widgets[f.key] = ent

    # ============================================================
    # 联动（由调用方通过 on_change 注入规则，弹窗自身不认业务）
    # ============================================================
    def _on_value_change(self, key):
        if self._link_busy or self._on_change_hook is None:
            return
        self._link_busy = True
        try:
            self._on_change_hook(key, self.field_value(key), self)
        finally:
            self._link_busy = False

    def field_value(self, key):
        """当前控件里的值（未收集 / 未校验，仅供联动判断）。

        choice 字段返回**选项值**而不是显示用的 label（与 set_field_value 对称）。
        """
        var = self._vars.get(key)
        if var is None:
            return getattr(self.entity, key, None)
        try:
            raw = var.get()
        except tk.TclError:
            return None
        if key in self._label_to_value:
            return self._label_to_value[key].get(raw, raw)
        return raw

    def set_field_value(self, key, value):
        """直接写控件值（联动用；choice 传 value，不是 label）。"""
        var = self._vars.get(key)
        if var is None:
            return
        if key in self._label_to_value:
            label = next((lb for lb, v in self._label_to_value[key].items()
                          if v == value), None)
            if label is not None:
                var.set(label)
            return
        var.set("" if value is None else str(value))

    def set_field_enabled(self, key, enabled):
        """启用 / 禁用某字段的输入控件（禁用字段不参与校验与收集）。"""
        widget = self._widgets.get(key)
        if widget is None:
            return
        try:
            if isinstance(widget, tk.Checkbutton):
                widget.configure(state="normal" if enabled else "disabled")
            elif isinstance(widget, ttk.Combobox):
                widget.configure(state="readonly" if enabled else "disabled")
            else:
                widget.configure(state="normal" if enabled else "disabled")
        except tk.TclError:
            return
        if enabled:
            self._disabled.discard(key)
        else:
            self._disabled.add(key)

    def _build_buttons(self):
        bar = tk.Frame(self)
        bar.pack(fill="x", padx=14, pady=(0, 12))
        self._err_label = tk.Label(bar, text="", fg="#B03A2E", anchor="w")
        self._err_label.pack(side="left")
        if self.readonly:
            tk.Button(bar, text="关闭", width=8,
                      command=self._cancel).pack(side="right")
            return
        tk.Button(bar, text="确定", width=8, command=self._on_ok).pack(
            side="right")
        tk.Button(bar, text="取消", width=8, command=self._cancel).pack(
            side="right", padx=(6, 0))

    # ============================================================
    # 校验 / 收集
    # ============================================================
    def _validate(self):
        for f in self.fields:
            if f.key in self._disabled:
                continue          # 联动禁用的字段（如独立时的附庸值）不校验
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
