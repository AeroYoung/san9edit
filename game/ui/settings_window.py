# -*- coding: utf-8 -*-
"""游戏设置窗口。

- 左侧分组树（简单列表）+ 右侧滚动内容区（折叠分组）。
- 修改不立即写盘，点“保存”才写盘 + apply + 通知主窗。
- 关闭时若未保存则弹确认。
"""

import tkinter as tk
from tkinter import ttk, colorchooser, messagebox

from game.config import constants as C
from game.config.style import THEME, FONT_SIZES
from game.config import settings_schema as schema
from game.ui.window_utils import center_on_parent
from game.ui.widgets.collapsible import CollapsibleSection


class SettingsWindow(tk.Toplevel):
    def __init__(self, master, settings_manager, font_family,
                 on_applied=None):
        super().__init__(master)
        self.settings = settings_manager
        self.font_family = font_family
        self.on_applied = on_applied or (lambda changed: None)

        self.title("游戏设置")
        self.transient(master)
        self.configure(bg=THEME["panel_bg"])

        self._closing = False    # 防止保存/关闭路径重入
        # 草稿：所有改动都写在这里，不直接写 manager
        self.draft = {}
        self._rows = {}         # path -> {"setter": fn, "kind": ...}
        self._sections = {}     # group_key -> CollapsibleSection

        # 顶部工具条
        self._build_toolbar()
        # 主体：Canvas + Scrollbar
        self._build_body()
        # 底部按钮
        self._build_footer()

        self._populate()
        self._refresh_dirty_label()
        self._bind_configure_recursive(self._content)   # 新增：子控件也参与 scrollregion 重算

        # 居中 + 模态
        width, height = 940, 660
        center_on_parent(self, master, width, height)
        self.minsize(760, 480)
        try:
            self.grab_set()
        except Exception:
            pass

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ==========================================================
    # 构建
    # ==========================================================
    def _build_toolbar(self):
        bar = tk.Frame(self, bg=THEME["toolbar_bg"])
        bar.pack(fill="x", side="top")

        tk.Label(bar, text="搜索：", bg=THEME["toolbar_bg"],
                 font=(self.font_family, FONT_SIZES["panel_body"]),
                 ).pack(side="left", padx=(10, 2), pady=6)

        self.filter_var = tk.StringVar()
        ent = tk.Entry(bar, textvariable=self.filter_var,
                       font=(self.font_family, FONT_SIZES["panel_body"]),
                       width=22)
        ent.pack(side="left", pady=6)
        self.filter_var.trace_add("write", lambda *a: self._apply_filter())

        self.only_modified_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            bar, text="仅显示已修改项", variable=self.only_modified_var,
            command=self._apply_filter,
            bg=THEME["toolbar_bg"], activebackground=THEME["toolbar_bg"],
            font=(self.font_family, FONT_SIZES["panel_body"]),
        ).pack(side="left", padx=12)

        tk.Label(bar, text=f"本地文件：{self.settings.path}",
                 bg=THEME["toolbar_bg"], fg="#777777",
                 font=(self.font_family, FONT_SIZES["panel_body"]),
                 ).pack(side="right", padx=10)

    def _build_body(self):
        wrap = tk.Frame(self, bg=THEME["panel_bg"])
        wrap.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(wrap, bg=THEME["panel_bg"],
                                 highlightthickness=0)
        vsb = ttk.Scrollbar(wrap, orient="vertical",
                            command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._content = tk.Frame(self._canvas, bg=THEME["panel_bg"])
        self._content_id = self._canvas.create_window(
            (0, 0), window=self._content, anchor="nw")

        def _on_content_config(_):
            # 推迟到下一次 idle：此刻布局才真正稳定
            self._canvas.after_idle(self._update_scrollregion)
        def _on_canvas_config(e):
            self._canvas.itemconfigure(self._content_id, width=e.width)
            self._canvas.after_idle(self._update_scrollregion)
        self._content.bind("<Configure>", _on_content_config, add="+")
        self._canvas.bind("<Configure>", _on_canvas_config, add="+")

        # 滚轮
        self._canvas.bind_all("<MouseWheel>", self._on_wheel, add="+")

    def _build_footer(self):
        bar = tk.Frame(self, bg=THEME["toolbar_bg"], height=44)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self.dirty_var = tk.StringVar(value="尚无修改")
        tk.Label(bar, textvariable=self.dirty_var,
                 bg=THEME["toolbar_bg"], fg="#555555",
                 font=(self.font_family, FONT_SIZES["panel_body"]),
                 ).pack(side="left", padx=12)

        def _btn(text, cmd, fg="black", bg=None, bold=False):
            kw = dict(text=text, command=cmd,
                      font=(self.font_family,
                            FONT_SIZES["panel_body"] + (2 if bold else 0),
                            "bold" if bold else "normal"),
                      fg=fg, relief="flat", bd=0, padx=14, pady=6,
                      cursor="hand2")
            if bg:
                kw["bg"] = bg
                kw["activebackground"] = bg
            return tk.Button(bar, **kw)

        _btn("保存", self._on_save, fg="white",
             bg="#27AE60", bold=True).pack(side="right", padx=4, pady=6)
        _btn("取消", self._on_close).pack(side="right", padx=4, pady=6)
        _btn("恢复全部默认", self._on_reset_all,
             fg="#B03A2E").pack(side="right", padx=4, pady=6)

    # ==========================================================
    # 生成控件
    # ==========================================================
    def _populate(self):
        for g in schema.GROUPS:
            items = schema.items_of_group(g["key"])
            if not items:
                continue
            sec = CollapsibleSection(
                self._content, title=g["title"], desc=g.get("desc", ""),
                on_reset=self._on_reset_group,
                expanded=(g["key"] in ("point", "visibility")),
                font_family=self.font_family,
            )
            sec.pack(fill="x", padx=8, pady=4)
            self._sections[g["key"]] = sec

            for it in items:
                if it.get("hidden"):
                    continue
                print("[populate]", g["key"], it["path"])
                self._add_item_row(sec.body, it)

    def _add_item_row(self, parent, item):
        print("[row]", item["path"])
        row = tk.Frame(parent, bg=THEME["panel_bg"])
        row.pack(fill="x", pady=2)

        left = tk.Frame(row, bg=THEME["panel_bg"], width=200)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        tk.Label(left, text=item["label"], anchor="w",
                 bg=THEME["panel_bg"], fg="#222222",
                 font=(self.font_family, FONT_SIZES["panel_body"]),
                 ).pack(anchor="w")
        if item.get("desc"):
            tk.Label(left, text=item["desc"], anchor="w", justify="left",
                     wraplength=200, bg=THEME["panel_bg"], fg="#888888",
                     font=(self.font_family, FONT_SIZES["panel_body"] - 1),
                     ).pack(anchor="w")

        right = tk.Frame(row, bg=THEME["panel_bg"])
        right.pack(side="left", fill="x", expand=True)

        kind = item["type"]
        if kind == "level_table":
            self._build_level_table(right, item)
        elif kind == "bool":
            self._build_bool(right, item)
        elif kind == "color":
            self._build_color(right, item)
        elif kind in ("int", "float"):
            self._build_number(right, item, kind)
        elif kind == "choice":
            self._build_choice(right, item)
        else:
            tk.Label(right, text=f"（未知类型 {kind}）",
                     bg=THEME["panel_bg"], fg="red").pack(side="left")

        # 行数据登记（供筛选用）
        item["_row_widget"] = row

    # ---------- 各控件 ----------
    def _build_bool(self, parent, item):
        path = item["path"]
        var = tk.BooleanVar(value=bool(self._get(path)))
        def _on():
            self.draft[path] = bool(var.get())
            self._refresh_dirty_label()
        tk.Checkbutton(parent, variable=var, command=_on,
                       bg=THEME["panel_bg"],
                       activebackground=THEME["panel_bg"]).pack(side="left")
        self._rows[path] = {"setter": lambda v: var.set(bool(v))}

    def _build_color(self, parent, item):
        path = item["path"]
        initial = self._get(path) or "#000000"

        swatch = tk.Label(parent, width=4, bg=initial, relief="solid",
                          bd=1, cursor="hand2")
        swatch.pack(side="left", padx=(0, 6))

        hexvar = tk.StringVar(value=initial)
        ent = tk.Entry(parent, textvariable=hexvar, width=10,
                       font=(self.font_family, FONT_SIZES["panel_body"]))
        ent.pack(side="left")

        def _set(v):
            v = str(v or "").strip()
            if not v.startswith("#") or len(v) != 7:
                return
            swatch.configure(bg=v)
            hexvar.set(v)
            self.draft[path] = v
            self._refresh_dirty_label()

        def _pick(_evt=None):
            rgb, hexval = colorchooser.askcolor(
                color=hexvar.get() or "#000000",
                parent=self, title=item["label"])
            if hexval:
                _set(hexval)

        def _on_commit(_evt=None):
            _set(hexvar.get())

        swatch.bind("<Button-1>", _pick)
        ent.bind("<Return>", _on_commit)
        ent.bind("<FocusOut>", _on_commit)

        self._rows[path] = {"setter": _set}

    def _build_number(self, parent, item, kind):
        path = item["path"]
        initial = self._get(path)
        var = tk.StringVar(value=str(initial))

        ent = tk.Entry(parent, textvariable=var, width=10,
                       font=(self.font_family, FONT_SIZES["panel_body"]))
        ent.pack(side="left")

        unit = item.get("value_suffix", "")
        if unit:
            tk.Label(parent, text=unit, bg=THEME["panel_bg"], fg="#666666",
                     font=(self.font_family, FONT_SIZES["panel_body"]),
                     ).pack(side="left", padx=(4, 0))

        err = tk.Label(parent, text="", bg=THEME["panel_bg"], fg="#B03A2E",
                       font=(self.font_family, FONT_SIZES["panel_body"] - 1))
        err.pack(side="left", padx=(8, 0))

        def _commit(_evt=None):
            raw = var.get().strip()
            try:
                v = int(raw) if kind == "int" else float(raw)
            except ValueError:
                err.configure(text="格式错误")
                return
            lo, hi = item.get("min"), item.get("max")
            if lo is not None and v < lo:
                err.configure(text=f"< {lo}"); return
            if hi is not None and v > hi:
                err.configure(text=f"> {hi}"); return
            err.configure(text="")
            self.draft[path] = v
            self._refresh_dirty_label()

        ent.bind("<Return>", _commit)
        ent.bind("<FocusOut>", _commit)

        def _set(v):
            var.set(str(v))
            err.configure(text="")
        self._rows[path] = {"setter": _set}

    def _build_choice(self, parent, item):
        path = item["path"]
        cur = self._get(path)
        vals = [c[0] for c in item["choices"]]
        labels = [c[1] for c in item["choices"]]
        var = tk.StringVar(value=labels[vals.index(cur)] if cur in vals
                                  else labels[0])
        cb = ttk.Combobox(parent, textvariable=var, values=labels,
                          state="readonly", width=12,
                          font=(self.font_family, FONT_SIZES["panel_body"]))
        cb.pack(side="left")
        def _on(_evt=None):
            idx = labels.index(var.get())
            self.draft[path] = vals[idx]
            self._refresh_dirty_label()
        cb.bind("<<ComboboxSelected>>", _on)

        def _set(v):
            if v in vals:
                var.set(labels[vals.index(v)])
        self._rows[path] = {"setter": _set}

    def _build_level_table(self, parent, item):
        path = item["path"]
        table = self._get(path) or {}
        vt = item["value_type"]

        sub = tk.Frame(parent, bg=THEME["panel_bg"])
        sub.pack(side="left", fill="x", expand=True)

        cols = 5
        for i, level in enumerate(sorted(table.keys())):
            r, c = divmod(i, cols)
            cell = tk.Frame(sub, bg=THEME["panel_bg"])
            cell.grid(row=r, column=c, padx=4, pady=2, sticky="w")

            tk.Label(cell, text=f"Lv{level}", width=4,
                    bg=THEME["panel_bg"], fg="#666666",
                    font=(self.font_family, FONT_SIZES["panel_body"] - 1),
                    ).pack(side="left")

            cur = table[level]
            child_path = f"{path}.{level}"

            if vt == "choice":
                vals = [c[0] for c in item["choices"]]
                labels = [c[1] for c in item["choices"]]
                var = tk.StringVar(
                    value=labels[vals.index(cur)] if cur in vals else labels[0])
                cb = ttk.Combobox(cell, textvariable=var, values=labels,
                                state="readonly", width=5,
                                font=(self.font_family,
                                        FONT_SIZES["panel_body"] - 1))
                cb.pack(side="left")
                def _on(_evt=None, cp=child_path, v=var, vs=vals, ls=labels):
                    self.draft[cp] = vs[ls.index(v.get())]
                    self._refresh_dirty_label()
                cb.bind("<<ComboboxSelected>>", _on)
                self._rows[child_path] = {
                    "setter": lambda v, var=var, vs=vals, ls=labels:
                        var.set(ls[vs.index(v)] if v in vs else ls[0])}
            elif vt == "bool":
                var = tk.BooleanVar(value=bool(cur))
                def _on(cp=child_path, v=var):
                    self.draft[cp] = bool(v.get())
                    self._refresh_dirty_label()
                tk.Checkbutton(cell, variable=var, command=_on,
                            bg=THEME["panel_bg"],
                            activebackground=THEME["panel_bg"],
                            ).pack(side="left")
                self._rows[child_path] = {
                    "setter": lambda v, var=var: var.set(bool(v))}
            else:
                is_int = (vt == "int")
                var = tk.StringVar(value=str(cur))
                ent = tk.Entry(cell, textvariable=var, width=6,
                            font=(self.font_family,
                                    FONT_SIZES["panel_body"] - 1))
                ent.pack(side="left")
                err = tk.Label(cell, text="", fg="#B03A2E",
                            bg=THEME["panel_bg"])
                err.pack(side="left")
                def _commit(_evt=None, cp=child_path, v=var, e=err,
                            ii=is_int, im=item):
                    raw = v.get().strip()
                    try:
                        x = int(raw) if ii else float(raw)
                    except ValueError:
                        e.configure(text="!"); return
                    lo, hi = im.get("min"), im.get("max")
                    if lo is not None and x < lo: e.configure(text="!"); return
                    if hi is not None and x > hi: e.configure(text="!"); return
                    e.configure(text="")
                    self.draft[cp] = x
                    self._refresh_dirty_label()
                ent.bind("<Return>", _commit)
                ent.bind("<FocusOut>", _commit)
                self._rows[child_path] = {
                    "setter": lambda v, var=var: var.set(str(v))}

    # ==========================================================
    # 值读写
    # ==========================================================
    def _get(self, path):
        """先从 draft，再从 settings.current，再退回默认。"""
        if path in self.draft:
            return self.draft[path]
        try:
            return self.settings.get(path)
        except KeyError:
            return None

    def _refresh_dirty_label(self):
        n = len(self.draft)
        self.dirty_var.set(f"已修改 {n} 项" if n else "尚无修改")

    # ==========================================================
    # 筛选
    # ==========================================================
    def _apply_filter(self):
        kw = self.filter_var.get().strip().lower()
        only_mod = self.only_modified_var.get()
        for it in schema.ITEMS:
            row = it.get("_row_widget")
            if row is None:
                continue
            visible = True
            if kw and kw not in it["label"].lower() \
                    and kw not in it["path"].lower():
                visible = False
            if only_mod and it["path"] not in self.draft:
                # level_table 的 draft key 带 level 后缀，这里模糊匹配
                if not any(k.startswith(it["path"] + ".") for k in self.draft):
                    visible = False
            if visible:
                row.pack(fill="x", pady=2)
            else:
                row.pack_forget()

    # ==========================================================
    # 恢复默认
    # ==========================================================
    def _on_reset_group(self, section):
        for gk, s in self._sections.items():
            if s is not section:
                continue
            for it in schema.items_of_group(gk):
                p = it["path"]
                if it["type"] == "level_table":
                    default = self.settings.get_default(p)
                    for lv, val in default.items():
                        self.draft.pop(f"{p}.{lv}", None)
                        setter = self._rows.get(f"{p}.{lv}")
                        if setter:
                            setter["setter"](val)
                else:
                    default = self.settings.get_default(p)
                    self.draft.pop(p, None)
                    row = self._rows.get(p)
                    if row:
                        row["setter"](default)
            break
        self._refresh_dirty_label()

    def _on_reset_all(self):
        if not self.draft:
            return
        if not messagebox.askyesno("恢复默认",
                "把所有设置项恢复为默认值？(尚未保存)"):
            return
        self.draft.clear()
        self.settings.reset_all()
        for p, row in self._rows.items():
            try:
                row["setter"](self.settings.get_default(p))
            except Exception:
                pass
        self._refresh_dirty_label()

    # ==========================================================
    # 滚动条
    # ==========================================================
    

    def _update_scrollregion(self):
        try:
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        except tk.TclError:
            pass

    def _bind_configure_recursive(self, widget):
        """给 widget 及其所有后代绑 <Configure>，任何子控件尺寸变化
        都会触发一次 scrollregion 重算。"""
        widget.bind("<Configure>",
                    lambda e: self._canvas.after_idle(self._update_scrollregion),
                    add="+")
        for c in widget.winfo_children():
            self._bind_configure_recursive(c)

    # ==========================================================
    # 保存 / 关闭
    # ==========================================================
    def _on_save(self):
        if self._closing:
            return
        if not self.draft:
            self._do_destroy()
            return

        # 找出需要重启的分组
        need_restart = set()
        for p in self.draft:
            gk = schema.group_of(p) or schema.group_of(p.rsplit(".", 1)[0])
            g = schema.group_meta(gk) if gk else None
            if g and g.get("restart"):
                need_restart.add(g["title"])

        self.settings.set_many(self.draft)
        try:
            self.settings.save()
        except Exception as e:
            messagebox.showerror("保存失败", str(e), parent=self)
            return
        self.settings.apply()

        changed = list(self.draft.keys())
        self.draft.clear()
        self._refresh_dirty_label()

        try:
            self.on_applied(changed)
        except Exception:
            pass

        # 先记住主窗（destroy 后 self.master 依然可读，但提前存更清晰）
        main = self.master

        # 先销毁自己，避免任何后续焦点事件再往 draft 里写值；
        # 然后以主窗为 parent 弹出「需重启」提示。
        self._do_destroy()
        if need_restart:
            messagebox.showinfo(
                "部分设置需重启生效",
                "以下分组的设置需要重启游戏后才能完全生效：\n\n  "
                + "、".join(sorted(need_restart)),
                parent=main,
            )

    def _on_close(self):
        if self._closing:
            return
        if self.draft:
            ans = messagebox.askyesnocancel(
                "未保存的修改",
                "有未保存的修改，是否保存？", parent=self)
            if ans is None:
                return          # 取消关闭
            if ans:
                self._on_save()
                return
            # 否则丢弃
        self._do_destroy()

    def _do_destroy(self):
        """统一销毁入口：绕过 draft 检查，并加锁防重入。"""
        if self._closing:
            return
        self._closing = True
        self._unbind_wheel()
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _on_wheel(self, event):
        # 只在鼠标位于本窗口时响应
        if self.winfo_containing(event.x_root, event.y_root) is None:
            return
        self._canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def _unbind_wheel(self):
        try:
            self._canvas.unbind_all("<MouseWheel>")
        except Exception:
            pass