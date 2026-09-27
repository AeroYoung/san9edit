# -*- coding: utf-8 -*-
"""通用数据驱动编辑弹窗。

只认 Field.kind，不认业务实体。
校验走 Field 的 min/max，readonly 走 display_fn。

形态：
    info_sections  只读信息块（(标题, 文本) 列表），放在字段上方
    readonly=True  全部字段按只读渲染，按钮只剩「关闭」
    sections       FieldGroup 元组，分组复用 CollapsibleSection
    scroll         True → 内容超出上限时出现滚动条
    on_link_click  信息块中 [[c:id|名字]] / [[f:id|名字]] / [[n:id|名字]]
                   标记的点击回调，签名 fn(kind, entity_id)
"""

import logging
import re
import tkinter as tk
from tkinter import ttk, colorchooser

from game.ui.widgets.searchable_combo import SearchableCombobox
from game.ui.window_utils import center_on_parent

logger = logging.getLogger(__name__)

MAX_BODY_H = 620

_LINK_RE = re.compile(r"\[\[([cfn]):([^|\]]+)\|([^\]]+)\]\]")


def _parse_link_text(text):
    """把带链接标记的字符串拆成 [(seg_text, kind|None, entity_id|None), ...]。

    标记形如 [[c:0952|刘备]] / [[f:0521|曹操]] / [[n:030703|居风]]。
    """
    result = []
    pos = 0
    for m in _LINK_RE.finditer(text):
        if m.start() > pos:
            result.append((text[pos:m.start()], None, None))
        result.append((m.group(3), m.group(1), m.group(2)))
        pos = m.end()
    if pos < len(text):
        result.append((text[pos:], None, None))
    return result


def _readonly_entry(parent, text):
    """只读单行 Entry：可鼠标拖动选中 + Ctrl+C 复制。"""
    entry = tk.Entry(
        parent, relief="flat", borderwidth=0, highlightthickness=0,
        readonlybackground="white", fg="#333333",
    )
    entry.insert(0, str(text))
    entry.configure(state="readonly")
    return entry


class EditDialog(tk.Toplevel):
    def __init__(self, master, fields, entity, world=None, title="编辑",
                 info_sections=(), readonly=False,
                 side_image=None, side_caption=None,
                 sections=None, scroll=False, on_change=None,
                 on_link_click=None):
        super().__init__(master)
        logger.debug("构建弹窗：%s（%d 字段，只读=%s，信息块=%d，分组=%d）",
                     title, len(fields), readonly, len(info_sections),
                     len(sections or ()))
        self.title(title)
        self.resizable(True, True)
        self.minsize(360, 240)
        self._top = master.winfo_toplevel()
        self.transient(self._top)

        self.sections = tuple(sections) if sections else ()
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
        self._on_link_click = on_link_click
        self._link_busy = False
        self._photo = None
        self._scroll_canvas = None
        self._fitting = False

        self._vars = {}
        self._widgets = {}
        self._disabled = set()
        self._old_values = {}
        self._label_to_value = {}
        self._swatches = {}
        self._err_label = None

        self._build(self.fields, self._info_sections)
        self._build_buttons()

        if self._on_change_hook is not None:
            for f in self.fields:
                if self._vars.get(f.key) is not None:
                    self._on_value_change(f.key)

        self.bind("<Escape>", lambda e: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)

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
            self._build_side(main)
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
        """内容区放入 Canvas：横 / 竖滚动条按内容 vs 视口大小自动出现。"""
        canvas = tk.Canvas(outer, width=560, height=MAX_BODY_H,
                           highlightthickness=0, bg=self.cget("bg"))
        bar_y = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        bar_x = ttk.Scrollbar(outer, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=bar_y.set, xscrollcommand=bar_x.set)

        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        canvas.grid(row=0, column=0, sticky="nsew")
        bar_y.grid(row=0, column=1, sticky="ns")
        bar_x.grid(row=1, column=0, sticky="ew")
        bar_y.grid_remove()
        bar_x.grid_remove()

        body = tk.Frame(canvas, bg=self.cget("bg"))
        window = canvas.create_window((0, 0), window=body, anchor="nw")

        def _fit_inner(_evt=None):
            if self._fitting:
                return
            self._fitting = True
            try:
                body.update_idletasks()
                natural_w = body.winfo_reqwidth()
                natural_h = body.winfo_reqheight()
                cw = canvas.winfo_width()
                ch = canvas.winfo_height()
                if cw <= 1 or ch <= 1:
                    return
                canvas.itemconfigure(window, width=max(cw, natural_w))
                if natural_h > ch:
                    bar_y.grid()
                else:
                    bar_y.grid_remove()
                if natural_w > cw:
                    bar_x.grid()
                else:
                    bar_x.grid_remove()
                canvas.configure(scrollregion=canvas.bbox("all"))
            finally:
                self._fitting = False

        body.bind("<Configure>", _fit_inner)
        canvas.bind("<Configure>", _fit_inner)
        for widget in (canvas, body):
            widget.bind("<MouseWheel>", lambda e: self._on_wheel(canvas, e))
        self._scroll_canvas = canvas
        return body

    @staticmethod
    def _on_wheel(canvas, event):
        canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def _build_sections(self, body):
        """分组布局：每组一个 CollapsibleSection，按 group.layout 分派渲染。"""
        from game.ui.widgets.collapsible import CollapsibleSection

        for group in self.sections:
            section = CollapsibleSection(body, group.title, desc=group.desc,
                                         expanded=True)
            section.pack(fill="x", pady=(0, 6))
            inner = section.body
            layout = getattr(group, "layout", "rows")
            if layout == "two_cols":
                self._render_two_cols(inner, group)
            elif layout == "inline":
                self._render_inline(inner, group)
            else:
                self._render_rows(inner, group)

    def _render_rows(self, inner, group):
        """默认：标签在左、控件在右，一行一个字段。"""
        self._render_group_body(inner, group.info, group.fields)

    def _render_group_body(self, frame, info, fields):
        """在某容器里按「info 块 → 字段行」顺序 grid 排布。"""
        frame.columnconfigure(1, weight=1)
        row = 0
        if info:
            row = self._build_info(frame, info) + 1
            tk.Frame(frame, bg="#DDDDDD", height=1).grid(
                row=row - 1, column=0, columnspan=3, sticky="ew", pady=6)
        for f in fields:
            self._build_row(frame, row, f)
            row += 1

    def _render_two_cols(self, inner, group):
        """左右两栏：按 left_keys / left_info_titles 划分，左栏顶部可挂头像。"""
        left = tk.Frame(inner, bg=self.cget("bg"))
        right = tk.Frame(inner, bg=self.cget("bg"))
        left.grid(row=0, column=0, sticky="nw", padx=(0, 16))
        right.grid(row=0, column=1, sticky="new")
        inner.columnconfigure(1, weight=1)

        if group.side_image or group.side_caption:
            self._build_side_inline(left, group.side_image, group.side_caption)

        left_body = tk.Frame(left, bg=self.cget("bg"))
        left_body.pack(fill="x")

        left_keys = set(group.left_keys or ())
        left_titles = set(group.left_info_titles or ())
        left_info = [t for t in group.info if t[0] in left_titles]
        right_info = [t for t in group.info if t[0] not in left_titles]
        left_fields = [f for f in group.fields if f.key in left_keys]
        right_fields = [f for f in group.fields if f.key not in left_keys]

        if left_info or left_fields:
            self._render_group_body(left_body, left_info, left_fields)
        self._render_group_body(right, right_info, right_fields)

    def _render_inline(self, inner, group):
        """所有字段排成一行：标签 + 控件依次横向排列。"""
        bar = tk.Frame(inner, bg=self.cget("bg"))
        bar.pack(anchor="w", fill="x", pady=(2, 0))
        for f in group.fields:
            cell = tk.Frame(bar, bg=self.cget("bg"))
            cell.pack(side="left", padx=(0, 12))
            tk.Label(cell, text=f.label + "：", anchor="e",
                     bg=self.cget("bg")).pack(side="left")
            value = getattr(self.entity, f.key, f.default)
            self._old_values[f.key] = value
            place, var, state = self._make_field_widget(cell, f, value)
            place.pack(side="left")
            self._vars[f.key] = var
            self._widgets[f.key] = state
            if self._on_change_hook is not None and var is not None:
                var.trace_add("write",
                              lambda *_a, k=f.key: self._on_value_change(k))

    def _build_side_inline(self, parent, image_path, caption):
        """组内左侧头像（140×140），找不到图 → 占位文字，不崩。"""
        from game.ui.portrait import load_thumbnail

        wrap = tk.Frame(parent, bg=self.cget("bg"))
        wrap.pack(anchor="w", pady=(0, 8))

        box = tk.Frame(wrap, width=140, height=140,
                       highlightthickness=1,
                       highlightbackground="#CCCCCC")
        box.pack()
        box.pack_propagate(False)
        label = tk.Label(box, bg="#F5F5F5")
        label.pack(expand=True, fill="both")

        photo, note = load_thumbnail(image_path, 140, 140, master=self)
        if photo is not None:
            self._photo = photo
            label.configure(image=photo)
        else:
            label.configure(text=note or "（无头像）", fg="#999999",
                            font=("", 9), justify="center")
        if caption:
            tk.Label(wrap, text=caption, fg="#333333", font=("", 9),
                     wraplength=140, justify="center").pack(pady=(4, 0))

    def _build_row(self, parent, row, f):
        tk.Label(parent, text=f.label + "：", anchor="e", bg=self.cget("bg")
                 ).grid(row=row, column=0, sticky="e", padx=(0, 8), pady=4)
        self._build_field(parent, row, f)
        if f.hint:
            tk.Label(parent, text=f.hint, fg="#888888",
                     font=("", 8), bg=self.cget("bg")).grid(
                row=row, column=2, sticky="w", padx=(8, 0))

    def _build_side(self, main):
        """右侧竖图（头像）：占位文字兜底。"""
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

    # ============================================================
    # info 块（只读，可拖选复制，支持 [[k:id|名字]] 链接）
    # ============================================================
    def _build_info(self, body, info_sections):
        row = 0
        for title, text in info_sections:
            tk.Label(body, text=title, anchor="w", font=("", 9, "bold")
                     ).grid(row=row, column=0, columnspan=3, sticky="w",
                            pady=(6, 0))
            row += 1
            self._build_info_text(body, row, str(text))
            row += 1
        return row

    def _build_info_text(self, parent, row, text):
        """只读多行文本：支持拖选 / Ctrl+C；[[k:id|名字]] 渲染为可点链接。"""
        t = tk.Text(parent, height=1, wrap="word",
                    relief="flat", borderwidth=0, highlightthickness=0,
                    padx=0, pady=0, bg="white", fg="#333333",
                    cursor="arrow", font=("", 9))
        t.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 3))

        for seg_text, kind, eid in _parse_link_text(str(text)):
            if kind is None:
                t.insert("end", seg_text)
            else:
                tag = "link_%s_%s_%s" % (kind, eid, t.index("end-1c"))
                t.insert("end", seg_text, (tag,))
                t.tag_configure(tag, foreground="#1F6FBF")
                t.tag_bind(tag, "<Button-1>",
                           lambda e, k=kind, i=eid: self._on_link(k, i))
                t.tag_bind(tag, "<Enter>",
                           lambda e, c=t: c.configure(cursor="hand2"))
                t.tag_bind(tag, "<Leave>",
                           lambda e, c=t: c.configure(cursor="arrow"))

        def _on_key(event):
            if event.state & 0x4 and event.keysym.lower() in ("c", "a"):
                return None
            return "break"
        t.bind("<Key>", _on_key)

        def _fit():
            try:
                if t.winfo_width() <= 1:
                    t.after(20, _fit)
                    return
                n = t.count("1.0", "end-1c", "displaylines")
                if n is None:
                    return
                if isinstance(n, (list, tuple)):
                    n = n[0] if n else 1
                if n is None:
                    return
                want = max(1, int(n))
                if int(t.cget("height")) != want:
                    t.configure(height=want)
            except (tk.TclError, TypeError, ValueError):
                pass
        t.after_idle(_fit)

        return t

    def _on_link(self, kind, entity_id):
        """点链接：先释放本弹窗的 grab，调回调，再抢回 grab。"""
        if self._on_link_click is None:
            return
        try:
            self.grab_release()
        except tk.TclError:
            pass
        try:
            self._on_link_click(kind, entity_id)
        finally:
            try:
                self.grab_set()
            except tk.TclError:
                pass

    # ============================================================
    # 字段渲染
    # ============================================================
    def _build_field(self, parent, row, f):
        value = getattr(self.entity, f.key, f.default)

        if f.kind == "readonly" or self.readonly:
            text = (f.display_fn(value, self.world) if f.display_fn
                    else str(value))
            entry = _readonly_entry(parent, text)
            entry.grid(row=row, column=1, sticky="ew", pady=4)
            self._vars[f.key] = None
            return

        self._old_values[f.key] = value
        place, var, state = self._make_field_widget(parent, f, value)
        place.grid(row=row, column=1, sticky="w", pady=4)
        self._vars[f.key] = var
        self._widgets[f.key] = state

        if self._on_change_hook is not None and var is not None:
            var.trace_add("write",
                          lambda *_a, k=f.key: self._on_value_change(k))

    def _make_field_widget(self, parent, f, value):
        """创建字段控件（未布局）。返回 (place, var, state)。"""
        if f.kind == "bool":
            var = tk.BooleanVar(value=bool(value))
            w = tk.Checkbutton(parent, variable=var, bg=self.cget("bg"),
                               activebackground=self.cget("bg"))
            return w, var, w

        if f.kind == "choice":
            labels = [label for _v, label in f.options]
            value_by_label = {label: v for v, label in f.options}
            self._label_to_value[f.key] = value_by_label
            current_label = next(
                (label for v, label in f.options if v == value),
                labels[0] if labels else "")
            var = tk.StringVar(value=current_label)
            w = SearchableCombobox(parent, labels,
                                   textvariable=var, width=18)
            return w, var, w

        if f.kind == "color":
            cell = tk.Frame(parent, bg=self.cget("bg"))
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
            return cell, hexvar, ent

        # int / str
        var = tk.StringVar(value=str(value))
        w = tk.Entry(parent, textvariable=var, width=18, bg="white")

        if f.kind == "int":
            def _validate(new_val, _f=f):
                if new_val == "":
                    return True
                if not new_val.isdigit():
                    return False
                v = int(new_val)
                if _f.min is not None and v < _f.min:
                    return False
                if _f.max is not None and v > _f.max:
                    return False
                return True
            vcmd = w.register(_validate)
            w.configure(validate="key", validatecommand=(vcmd, "%P"))

        return w, var, w

    # ============================================================
    # 联动
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
        widget = self._widgets.get(key)
        if widget is None:
            return
        try:
            if isinstance(widget, tk.Checkbutton):
                widget.configure(state="normal" if enabled else "disabled")
            elif isinstance(widget, ttk.Combobox):
                widget.configure(state="normal" if enabled else "disabled")
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
                continue
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
        # destroy 前先规范化所有可搜索下拉（normalize 需要 widget 尚存）
        for widget in self._widgets.values():
            if isinstance(widget, SearchableCombobox):
                try:
                    widget.normalize()
                except tk.TclError:
                    pass
        self.ok = True
        self.destroy()
        logger.debug("弹窗确定")

    def _cancel(self):
        self.ok = False
        self.destroy()
        logger.debug("弹窗取消")