# -*- coding: utf-8 -*-
"""官职体系窗口。

两种模式：
    - 按人物（默认）：全部登场人物，一行一人；只显示有外官或武官的人。
      列：姓名 / 外官 / 武官 / 身份 / 所属势力 / 所在 / 位阶；默认按势力分组，
      组内君主置顶。
    - 按官职：武官（全部）+ 外官（默认仅有人担任）；列：类型 / 州 / 郡 /
      官职 / 位阶 / 人物；分组 = 类型 → 州 → 郡（武官无州郡子组）。

双击数据行：
    - 模式一 → 打开该人物情报窗口
    - 模式二 → 单个人物直接打开；多人弹选择列表
"""

import logging
import tkinter as tk
from collections import defaultdict
from tkinter import ttk

from game.config.style import THEME, FONT_SIZES
from game.core import military_title
from game.core.official_title import (
    compute_county_ranks, official_rank_of_title,
    city_rank_by_level, state_title, county_title, city_title,
)
from game.ui.window_utils import center_on_parent

logger = logging.getLogger(__name__)

MU_STATES = {"02", "08", "11", "12"}

WIN_W = 1000
WIN_H = 720

MODE_PERSON = "person"
MODE_JOB = "job"

NO_STATE = "—"
NO_COUNTY = "—"


class JobSystemWindow(tk.Toplevel):
    def __init__(self, master, world, font_family="TkDefaultFont"):
        super().__init__(master)
        self.world = world
        self.font_family = font_family
        self._top = master.winfo_toplevel()

        self._mode = MODE_PERSON
        self._show_rank_in_cell = True
        self._show_all_officials = False
        self._search_text = ""

        # 排序状态
        self._sort_key = None
        self._sort_desc = False

        self._county_ranks = compute_county_ranks(world.nodes.values())

        self.title("官职体系")
        self.transient(self._top)
        self.configure(bg=THEME["panel_bg"])

        self._build_ui()
        self.update_idletasks()
        center_on_parent(self, self._top, WIN_W, WIN_H)
        self.bind("<Escape>", lambda e: self.destroy())
        self.focus_set()

    # ============================================================
    # UI 组装
    # ============================================================
    def _build_ui(self):
        # ---- 顶部控制栏 ----
        bar = tk.Frame(self, bg=THEME["panel_bg"])
        bar.pack(fill="x", padx=10, pady=(10, 6))

        self._mode_var = tk.StringVar(value=self._mode)
        tk.Radiobutton(
            bar, text="按人物", value=MODE_PERSON, variable=self._mode_var,
            command=self._on_mode_change, bg=THEME["panel_bg"],
            font=(self.font_family, FONT_SIZES["panel_body"]),
        ).pack(side="left")
        tk.Radiobutton(
            bar, text="按官职", value=MODE_JOB, variable=self._mode_var,
            command=self._on_mode_change, bg=THEME["panel_bg"],
            font=(self.font_family, FONT_SIZES["panel_body"]),
        ).pack(side="left", padx=(6, 16))

        self._rank_cell_var = tk.BooleanVar(value=self._show_rank_in_cell)
        self._rank_cell_chk = tk.Checkbutton(
            bar, text="单元格显示位阶", variable=self._rank_cell_var,
            command=self._on_rank_cell_change, bg=THEME["panel_bg"],
            font=(self.font_family, FONT_SIZES["panel_body"]),
        )
        self._rank_cell_chk.pack(side="left")

        self._all_off_var = tk.BooleanVar(value=self._show_all_officials)
        self._all_off_chk = tk.Checkbutton(
            bar, text="显示全部外官（含无人担任）",
            variable=self._all_off_var,
            command=self._on_all_officials_change, bg=THEME["panel_bg"],
            font=(self.font_family, FONT_SIZES["panel_body"]),
        )
        self._all_off_chk.pack(side="left", padx=(16, 0))

        # ---- 搜索栏 ----
        search = tk.Frame(self, bg=THEME["panel_bg"])
        search.pack(fill="x", padx=10, pady=(0, 6))
        tk.Label(search, text="搜索：", bg=THEME["panel_bg"],
                 font=(self.font_family, FONT_SIZES["panel_body"])
                 ).pack(side="left")
        self._search_var = tk.StringVar(value=self._search_text)
        entry = tk.Entry(search, textvariable=self._search_var,
                         font=(self.font_family, FONT_SIZES["panel_body"]))
        entry.pack(side="left", fill="x", expand=True, padx=(4, 4))
        entry.bind("<KeyRelease>", lambda e: self._on_search())
        tk.Button(search, text="清空", command=self._clear_search,
                  font=(self.font_family, FONT_SIZES["panel_body"])
                  ).pack(side="left")

        # ---- 表格 ----
        body = tk.Frame(self, bg=THEME["panel_bg"])
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(body, show="tree headings",
                                 selectmode="browse")
        vsb = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)

        self.tree.tag_configure("group", background="#F3F4F6",
                                font=(self.font_family, 9, "bold"))
        self.tree.bind("<Double-Button-1>", self._on_double_click)

        self._on_mode_change()

    # ============================================================
    # 控件回调
    # ============================================================
    def _on_mode_change(self):
        self._mode = self._mode_var.get()
        person = (self._mode == MODE_PERSON)
        self._rank_cell_chk.configure(state="normal" if person else "disabled")
        self._all_off_chk.configure(state="disabled" if person else "normal")
        # 切模式清排序状态（列不同）
        self._sort_key = None
        self._sort_desc = False
        self._rebuild_tree_columns()
        self._refresh()

    def _on_rank_cell_change(self):
        self._show_rank_in_cell = self._rank_cell_var.get()
        self._refresh()

    def _on_all_officials_change(self):
        self._show_all_officials = self._all_off_var.get()
        self._refresh()

    def _on_search(self):
        self._search_text = self._search_var.get().strip()
        self._refresh()

    def _clear_search(self):
        self._search_var.set("")
        self._search_text = ""
        self._refresh()

    def _on_heading_click(self, key):
        if self._sort_key == key:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_key = key
            self._sort_desc = False
        self._refresh()

    # ============================================================
    # 表格列
    # ============================================================
    def _rebuild_tree_columns(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        old_cols = self.tree["columns"]
        if old_cols:
            self.tree.configure(columns=())
        for key in old_cols:
            try:
                self.tree.heading(key, text="")
                self.tree.column(key, width=0)
            except tk.TclError:
                pass

        if self._mode == MODE_PERSON:
            self.tree.configure(columns=("official", "military", "role",
                                          "faction", "location", "rank"))
            self._set_heading("#0", "姓名", 120, "w")
            self._set_heading("official", "外官", 220, "w")
            self._set_heading("military", "武官", 140, "w")
            self._set_heading("role",     "身份",  70, "center")
            self._set_heading("faction",  "所属势力", 90, "center")
            self._set_heading("location", "所在", 100, "center")
            self._set_heading("rank",     "位阶",  50, "center")
        else:
            self.tree.configure(columns=("state", "county", "job",
                                          "rank", "persons"))
            self._set_heading("#0", "类型", 80, "center")
            self._set_heading("state",   "州",  80, "center")
            self._set_heading("county",  "郡", 100, "center")
            self._set_heading("job",     "官职", 180, "w")
            self._set_heading("rank",    "位阶",  50, "center")
            self._set_heading("persons", "人物", 400, "w")

    def _set_heading(self, key, title, width, anchor):
        self.tree.heading(
            key, text=title,
            command=lambda k=key: self._on_heading_click(k),
        )
        self.tree.column(key, width=width, anchor=anchor, stretch=False)

    # ============================================================
    # 刷新
    # ============================================================
    def _refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        if self._mode == MODE_PERSON:
            self._refresh_person_mode()
        else:
            self._refresh_job_mode()

    # ---------------- 模式一：按人物 ----------------
    def _refresh_person_mode(self):
        # 1. 收集行
        rows = []
        for ch in self.world.characters.values():
            if not ch.appeared:
                continue
            if not self._person_has_job(ch):
                continue
            if self._search_text and self._search_text not in ch.name:
                continue
            rows.append(self._make_person_row(ch))

        # 2. 按势力分组
        groups = defaultdict(list)
        for r in rows:
            groups[r["faction"]].append(r)

        # 3. 组内排序（君主恒置顶）
        for items in groups.values():
            items.sort(key=self._person_sort_key,
                       reverse=self._sort_desc)

        # 4. 插入（「在野」排最后）
        ordered = sorted(groups.items(),
                         key=lambda kv: (kv[0] == "在野", kv[0]))
        for fname, items in ordered:
            gid = self.tree.insert(
                "", "end", text=f"{fname}（{len(items)}）",
                open=True, tags=("group",))
            for r in items:
                self.tree.insert(
                    gid, "end", text=r["name"], iid=r["iid"],
                    values=(r["official"], r["military"], r["role"],
                            r["faction"], r["location"], r["rank_text"]))

    def _make_person_row(self, ch):
        official_text, official_rank = self._official_cell_and_rank(ch)
        military_text, military_rank = self._military_cell_and_rank(ch)
        overall = self._overall_rank(ch, official_rank, military_rank)
        return {
            "ch": ch,
            "iid": ch.id,
            "name": ch.name,
            "official": official_text,
            "official_rank": official_rank,
            "military": military_text,
            "military_rank": military_rank,
            "role": ch.role or "—",
            "faction": self._faction_name(ch),
            "location": self._node_name(ch.location),
            "overall_rank": overall,
            "rank_text": str(overall) if overall is not None else "—",
            "is_ruler": (ch.faction is not None and ch.faction == ch.id),
        }

    def _person_sort_key(self, r):
        """(君主优先, 列排序值)。"""
        ruler_key = 0 if r["is_ruler"] else 1
        col_key = self._sort_key
        if col_key is None or col_key == "#0":
            return (ruler_key, r["ch"].id)
        if col_key == "rank":
            v = r["overall_rank"]
            return (ruler_key, 0 if v is not None else 1, v or 0)
        # 其余字符串列
        v = {
            "official": r["official"],
            "military": r["military"],
            "role": r["role"],
            "faction": r["faction"],
            "location": r["location"],
        }.get(col_key, "")
        return (ruler_key, str(v or ""))

    def _person_has_job(self, ch):
        if ch.military_title:
            return True
        return bool(self.world.officials_of_character(ch.id))

    def _faction_name(self, ch):
        if not ch.faction:
            return "在野"
        f = self.world.faction(ch.faction)
        return f.name if f else "在野"

    def _node_name(self, node_id):
        if not node_id:
            return "—"
        n = self.world.node(node_id)
        return n.name if n else "—"

    def _official_cell_and_rank(self, ch):
        items = self.world.officials_of_character(ch.id)
        if not items:
            return "—", None
        parts = []
        ranks = []
        for item in items:
            title = item.get("name", "")
            r = self._official_rank(item)
            if r is not None:
                ranks.append(r)
            if self._show_rank_in_cell:
                parts.append(f"{title}({r})" if r is not None else title)
            else:
                parts.append(title)
        best = min(ranks) if ranks else None
        return "、".join(parts), best

    def _military_cell_and_rank(self, ch):
        if not ch.military_title:
            return "—", None
        r = military_title.rank_of(ch.military_title)
        if not self._show_rank_in_cell:
            return ch.military_title, r
        return (f"{ch.military_title}({r})" if r is not None
                else ch.military_title), r

    def _overall_rank(self, ch, official_rank, military_rank):
        ranks = [r for r in (official_rank, military_rank) if r is not None]
        return min(ranks) if ranks else None

    def _official_rank(self, item):
        rid = item.get("region_id", "")
        if len(rid) == 6:
            node = self.world.node(rid)
            return city_rank_by_level(node.level) if node else None
        return official_rank_of_title(item.get("name", ""), rid,
                                      self._county_ranks)

    # ---------------- 模式二：按官职 ----------------
    def _refresh_job_mode(self):
        # 结构：rows = [(type, state, county, job, rank, persons_text,
        #                sort_persons), ...]
        rows = self._collect_job_rows()

        # 搜索过滤
        if self._search_text:
            key = self._search_text
            rows = [r for r in rows
                    if key in r[3]  # 官职
                    or any(key in n for n in r[6])]  # 人物名

        # 分组：类型 → 州 → 郡
        tree = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        for r in rows:
            tree[r[0]][r[1]][r[2]].append(r)

        # 排序（组内）
        for typ_d in tree.values():
            for state_d in typ_d.values():
                for county_d in state_d.values():
                    county_d.sort(key=self._job_sort_key,
                                  reverse=self._sort_desc)

        # 插入（类型顺序：武官 → 外官）
        for typ in ("武官", "外官"):
            if typ not in tree:
                continue
            total_type = sum(len(lst)
                             for st in tree[typ].values()
                             for lst in st.values())
            gid = self.tree.insert(
                "", "end", text=f"{typ}（{total_type}）",
                open=True, tags=("group",))

            if typ == "武官":
                # 武官无州郡子组，直接平铺
                flat = [r for st in tree[typ].values()
                        for lst in st.values() for r in lst]
                flat.sort(key=self._job_sort_key,
                          reverse=self._sort_desc)
                for r in flat:
                    self._insert_job_leaf(gid, r)
            else:
                for state in sorted(tree[typ]):
                    state_items = tree[typ][state]
                    total_state = sum(len(lst)
                                      for lst in state_items.values())
                    sid = self.tree.insert(
                        gid, "end", text="",
                        values=(f"{state}（{total_state}）", "", "", "", ""),
                        open=True, tags=("group",))
                    for county in sorted(state_items):
                        items = state_items[county]
                        cid = self.tree.insert(
                            sid, "end", text="",
                            values=("", "",
                                    f"{county}（{len(items)}）", "", ""),
                            open=True, tags=("group",))
                        for r in items:
                            self._insert_job_leaf(cid, r)

    def _insert_job_leaf(self, parent, r):
        _typ, state, county, job, rank, persons_text, _names = r
        self.tree.insert(
            parent, "end", text="",
            values=(state, county, job,
                    str(rank) if rank is not None else "—",
                    persons_text))

    def _collect_job_rows(self):
        """返回 [(type, state, county, job, rank, persons_text, names)]。"""
        # 聚合表：(type, state, county, job, rank) -> [names]
        buckets = defaultdict(list)

        # 1) 武官（全部列出，state / county 都是空）
        for title in military_title.all_titles():
            r = military_title.rank_of(title)
            buckets[("武官", NO_STATE, NO_COUNTY, title, r)] = []

        # 2) 外官
        if self._show_all_officials:
            for sid, sname in self.world.state_names.items():
                if len(sid) != 2:
                    continue
                t = state_title(sid, sname, MU_STATES)
                r = official_rank_of_title(t, sid)
                key = ("外官", sname, NO_COUNTY, t, r)
                buckets[key] = buckets.get(key, [])
            for cid, cname in self.world.county_names.items():
                if len(cid) != 4:
                    continue
                t = county_title(cname)
                r = official_rank_of_title(t, cid, self._county_ranks)
                sname = self.world.state_name(cid[:2])
                key = ("外官", sname, cname, t, r)
                buckets[key] = buckets.get(key, [])
            for n in self.world.nodes.values():
                t = city_title(n.name, n.type, n.level)
                r = city_rank_by_level(n.level)
                sname = self.world.state_name(n.state_id)
                cname = self.world.county_name(n.county_id)
                key = ("外官", sname, cname, t, r)
                buckets[key] = buckets.get(key, [])

        # 3) 填人物
        for rid, item in self.world.officials.items():
            ch = self.world.character(item.get("character_id"))
            if ch is None or not ch.appeared:
                continue
            r = self._official_rank(dict(item, region_id=rid))
            sname, cname = self._region_names(rid)
            key = ("外官", sname, cname, item.get("name", ""), r)
            buckets[key].append(ch.name)
        for ch in self.world.characters.values():
            if not ch.appeared or not ch.military_title:
                continue
            r = military_title.rank_of(ch.military_title)
            key = ("武官", NO_STATE, NO_COUNTY, ch.military_title, r)
            buckets.setdefault(key, []).append(ch.name)

        # 4. 组装成 rows
        rows = []
        for (typ, state, county, job, rank), names in buckets.items():
            names_sorted = sorted(set(names))
            persons_text = "、".join(names_sorted) if names_sorted else "—"
            rows.append((typ, state, county, job, rank, persons_text,
                         names_sorted))
        return rows

    def _region_names(self, rid):
        if len(rid) == 2:
            return self.world.state_name(rid), NO_COUNTY
        if len(rid) == 4:
            return self.world.state_name(rid[:2]), self.world.county_name(rid)
        if len(rid) == 6:
            return (self.world.state_name(rid[:2]),
                    self.world.county_name(rid[:4]))
        return NO_STATE, NO_COUNTY

    def _job_sort_key(self, r):
        col_key = self._sort_key
        if col_key is None or col_key == "#0":
            # 默认：位阶升序 → 官职字典序
            rank = r[4]
            return (rank is None, rank or 0, r[3])
        if col_key == "state":
            return str(r[1] or "")
        if col_key == "county":
            return str(r[2] or "")
        if col_key == "job":
            return str(r[3] or "")
        if col_key == "rank":
            rank = r[4]
            return (rank is None, rank or 0)
        if col_key == "persons":
            # 用第一个人名排序
            return r[6][0] if r[6] else ""
        return ""

    # ============================================================
    # 双击
    # ============================================================
    def _on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        if "group" in self.tree.item(item, "tags"):
            return

        if self._mode == MODE_PERSON:
            self._open_character(item)
            return

        values = self.tree.item(item, "values")
        if len(values) < 5:
            return
        names_text = values[4]
        if not names_text or names_text == "—":
            return
        names = [n.strip() for n in names_text.split("、") if n.strip()]
        if not names:
            return
        if len(names) == 1:
            self._open_character_by_name(names[0])
        else:
            self._pick_and_open(names)

    def _open_character(self, cid):
        ch = self.world.character(cid)
        if ch is None:
            return
        self._open_window(ch)

    def _open_character_by_name(self, name):
        for ch in self.world.characters.values():
            if ch.name == name:
                self._open_window(ch)
                return

    def _open_window(self, ch):
        from game.ui.character_info_window import CharacterInfoWindow
        CharacterInfoWindow(self._top, ch, world=self.world,
                            font_family=self.font_family, session=None)

    def _pick_and_open(self, names):
        top = tk.Toplevel(self)
        top.title("选择人物")
        top.transient(self)
        tk.Label(top, text="选择要查看的人物：",
                 font=(self.font_family, FONT_SIZES["panel_body"])
                 ).pack(padx=10, pady=(10, 4), anchor="w")
        lb = tk.Listbox(top, width=20, height=min(20, len(names)),
                        font=(self.font_family, FONT_SIZES["panel_body"]))
        for n in names:
            lb.insert("end", n)
        lb.pack(padx=10, pady=(0, 6), fill="both", expand=True)

        def _confirm(_e=None):
            sel = lb.curselection()
            if not sel:
                return
            name = lb.get(sel[0])
            top.destroy()
            self._open_character_by_name(name)

        lb.bind("<Double-Button-1>", _confirm)
        tk.Button(top, text="确定", command=_confirm,
                  font=(self.font_family, FONT_SIZES["panel_body"])
                  ).pack(pady=(0, 10))
        self.update_idletasks()
        center_on_parent(top, self, 260, 300)
        top.grab_set()
        top.focus_set()