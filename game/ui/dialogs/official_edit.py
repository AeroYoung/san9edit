# -*- coding: utf-8 -*-
"""外官编辑：给某人物增 / 改 / 删外官（一人可任多职，一区一官）。

入口：人物情报窗口（MODE_EDIT 下为「编辑人物」）的外官区。
规则（需求 §3.3）：
    - 可选行政区**仅限该人物所属势力的实控区域**（该势力名下据点对应的州 / 郡 / 县）
    - rank 由 region_id 位数锁定（2 州 / 4 郡 / 6 县）
    - 官名默认走 core/official_title.py 生成，允许 override
    - 一区一官：新外官替换该区原条目
    - 解耦：默认只改外官；两个可选级联（移动到治所 / 变更势力）默认不勾选
改 World 只走 Command（OfficialSetCommand / OfficialRemoveCommand 等，整包 CompositeCommand）。
"""

import logging
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import messagebox
from typing import List, Optional

from game.config.style import THEME, FONT_SIZES
from game.core.official_title import make_title, rank_of
from game.ui.dialogs.pick_list import PickList, WorldHolder
from game.ui.panels.list.columns import Column
from game.ui.window_utils import center_on_parent

logger = logging.getLogger(__name__)

WIN_W = 700
LIST_H = 190


@dataclass(frozen=True)
class RegionOption:
    """该人物势力实控范围内的一个行政区。"""
    id: str
    label: str          # 默认官名（规则生成）
    rank: str
    region_name: str    # 州名 / 郡名 / 县名
    seat: str           # 治所据点 id（级联「移动到治所」用）
    owner: Optional[str]  # 治所的实控势力（级联「变更势力」用）


REGION_COLUMNS = (
    Column("rank", "等级", 44, "center", lambda r: r.rank),
    Column("seat", "治所", 60, "center", lambda r: r.seat),
)
REGION_NAME_COLUMN = Column("name", "行政区", 120, "w",
                            lambda r: f"{r.region_name}（{r.id}）")

OFFICIAL_COLUMNS = (
    Column("rank", "等级", 44, "center", lambda r: r.rank),
    Column("name", "官名", 120, "w", lambda r: r.name),
)
OFFICIAL_NAME_COLUMN = Column("region", "行政区", 110, "w",
                              lambda r: r.region_id)


@dataclass(frozen=True)
class OfficialRow:
    """外官区列表里的一行（world 现状 + 待提交改动）。"""
    region_id: str
    name: str
    rank: str


def region_options(world, faction_id, mu_states=()) -> List[RegionOption]:
    """该势力实控区域（州 / 郡 / 县三层去重），带默认官名与治所。"""
    if not faction_id:
        return []
    nodes = [n for n in world.nodes.values() if n.owner == faction_id]
    seen = {}
    for node in nodes:
        for rid, seat in ((node.id, node.id),
                          (node.county_id, node.id),
                          (node.state_id, node.id)):
            if rid in seen:
                continue
            seen[rid] = seat

    options = []
    for rid, seat in sorted(seen.items()):
        node = world.node(seat)
        rank = rank_of(rid) or ""
        if len(rid) == 2:
            region_name = world.state_name(rid)
            seat = _county_seat(world, nodes, rid)
        elif len(rid) == 4:
            region_name = world.county_name(rid)
            seat = _county_seat(world, nodes, rid)
        else:
            region_name = node.name if node is not None else rid
        seat_node = world.node(seat)
        options.append(RegionOption(
            id=rid, rank=rank, region_name=region_name, seat=seat,
            owner=(seat_node.owner if seat_node is not None else None),
            label=make_title(
                rid,
                state_name=world.state_name(rid[:2]) if len(rid) == 2 else None,
                county_name=world.county_name(rid) if len(rid) == 4 else None,
                city_name=(node.name if node is not None else ""),
                type_=(node.type if node is not None else "城"),
                level=(node.level if node is not None else 5),
                mu_states=mu_states,
            ),
        ))
    # 排序：州 → 郡 → 县，同级按 id
    options.sort(key=lambda o: (len(o.id), o.id))
    return options


def _county_seat(world, faction_nodes, region_id):
    """区域治所：该区域内的郡治（is_capital），没有就取区内第一个据点。"""
    inside = [n for n in faction_nodes if n.id.startswith(region_id)]
    if not inside:
        return ""
    for node in inside:
        if node.is_capital:
            return node.id
    return inside[0].id


@dataclass
class OfficialEditPlan:
    """外官编辑的提交内容（纯数据，供命令生成与测试）。"""
    character_id: str
    set_items: tuple = ()          # ((region_id, item), ...)
    remove_regions: tuple = ()     # (region_id, ...)
    move_to_seat: bool = False
    change_faction: bool = False
    seats: dict = field(default_factory=dict)   # region_id -> 治所 id


def build_official_commands(world, plan: OfficialEditPlan) -> list:
    """外官编辑 → 命令列表（外官 → 可选级联）。"""
    from game.core.edit_commands import (
        CharacterEditCommand, OfficialRemoveCommand, OfficialSetCommand)

    cmds = []
    for rid in plan.remove_regions:
        item = world.official_of(rid)
        if item is not None:
            cmds.append(OfficialRemoveCommand(rid, item))
    for rid, item in plan.set_items:
        cmds.append(OfficialSetCommand(rid, world.official_of(rid), item))

    ch = world.character(plan.character_id)
    if ch is not None:
        proposed = {}
        seat = plan.seats.get(plan.set_items[-1][0]) if plan.set_items else None
        if plan.move_to_seat and seat:
            proposed["node"] = seat
            proposed["location"] = seat
        if plan.change_faction and plan.set_items:
            region_id = plan.set_items[-1][0]
            seat_node = world.node(plan.seats.get(region_id) or "")
            if seat_node is not None and seat_node.owner:
                proposed["faction"] = seat_node.owner
        if proposed:
            old = {k: getattr(ch, k) for k in proposed}
            new = {k: v for k, v in proposed.items() if old[k] != v}
            if new:
                cmds.append(CharacterEditCommand(
                    ch.id, {k: old[k] for k in new}, new))
    return cmds


def edit_officials(parent, world, character, session, open_dialog) -> bool:
    """外官编辑共用流程。返回 True = 已执行命令。"""
    if session is None or world is None or character is None:
        return False
    dlg = open_dialog(lambda: OfficialEditDialog(parent, world, character))
    if dlg is None or not dlg.ok or dlg.plan is None:
        logger.debug("外官编辑：已取消")
        return False
    cmds = build_official_commands(world, dlg.plan)
    if not cmds:
        logger.debug("外官编辑：无变化")
        return False

    from game.core.edit_session import CompositeCommand
    session.execute(CompositeCommand(cmds, "编辑外官") if len(cmds) > 1
                    else cmds[0])
    logger.info("编辑外官：%s / 设置 %d 条 / 删除 %d 条 / 级联=%s",
                character.id, len(dlg.plan.set_items),
                len(dlg.plan.remove_regions),
                (dlg.plan.move_to_seat, dlg.plan.change_faction))
    return True


class OfficialEditDialog(tk.Toplevel):
    """外官增 / 改 / 删；两个可选级联默认不勾选。"""

    def __init__(self, master, world, character):
        super().__init__(master)
        self.world = world
        self.character = character
        self.ok = False
        self.plan = None

        self._top = master.winfo_toplevel()
        self.font_family = getattr(self._top, "font_family", "TkDefaultFont")
        self._pending_set = {}        # region_id -> item（待新增 / 覆盖）
        self._pending_remove = set()  # 待删除的 region_id
        self._seats = {}              # region_id -> 治所据点 id（级联用）

        self.title("编辑外官")
        self.transient(self._top)
        self.configure(bg=THEME["panel_bg"])
        self.resizable(False, False)

        self._build_ui()
        self.update_idletasks()
        center_on_parent(self, self._top, WIN_W,
                         max(self.winfo_reqheight(), 560))
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.bind("<Escape>", lambda e: self._cancel())
        self.focus_set()

    # ------------------------------------------------------------
    # UI
    # ------------------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 16}
        tk.Label(self, text=f"外官编辑：{self.character.display_name()}",
                 bg=THEME["panel_bg"], fg="#222222",
                 font=(self.font_family, FONT_SIZES["panel_title"] + 2, "bold")
                 ).pack(anchor="w", pady=(12, 2), **pad)
        tk.Label(self, text="一人可任多个外官；同一行政区只能有一位（新区覆盖原官）",
                 bg=THEME["panel_bg"], fg="#555555",
                 font=(self.font_family, FONT_SIZES["panel_body"])
                 ).pack(anchor="w", **pad)

        self._label("当前外官（含待提交改动）", pad)
        holder = tk.Frame(self, height=LIST_H, bg=THEME["panel_bg"])
        holder.pack(fill="x", **pad)
        holder.pack_propagate(False)
        self.official_pick = PickList(
            holder, WorldHolder(self.world),
            columns=OFFICIAL_COLUMNS, name_column=OFFICIAL_NAME_COLUMN,
            rows_fn=self._current_rows, key_fn=lambda r: r.region_id)
        self.official_pick.pack(fill="both", expand=True)
        tk.Button(self, text="删除选中外官", width=14,
                  command=self._remove_selected).pack(anchor="w", pady=(2, 6),
                                                      **pad)

        self._label("可任命的行政区（限本势力实控区域）", pad)
        holder2 = tk.Frame(self, height=LIST_H, bg=THEME["panel_bg"])
        holder2.pack(fill="x", **pad)
        holder2.pack_propagate(False)
        self.region_pick = PickList(
            holder2, WorldHolder(self.world),
            columns=REGION_COLUMNS, name_column=REGION_NAME_COLUMN,
            rows_fn=lambda: region_options(self.world,
                                           self.character.faction),
            key_fn=lambda r: r.id)
        self.region_pick.pack(fill="both", expand=True)
        self.region_pick.tree.bind("<<TreeviewSelect>>",
                                   lambda e: self._on_region_pick())

        form = tk.Frame(self, bg=THEME["panel_bg"])
        form.pack(fill="x", pady=(6, 0), **pad)
        tk.Label(form, text="官名（可改）", bg=THEME["panel_bg"], fg="#333333",
                 font=(self.font_family, FONT_SIZES["panel_body"])).pack(side="left")
        self._title_var = tk.StringVar()
        tk.Entry(form, textvariable=self._title_var, width=20).pack(side="left",
                                                                   padx=(6, 12))
        tk.Button(form, text="设为该区外官", width=14,
                  command=self._add_selected).pack(side="left")

        self._move_var = tk.BooleanVar(value=False)
        self._faction_var = tk.BooleanVar(value=False)
        opt = tk.Frame(self, bg=THEME["panel_bg"])
        opt.pack(fill="x", pady=(4, 0), **pad)
        for text, var in (("同时将人物移动到该行政区治所", self._move_var),
                          ("同时将人物势力变更为该行政区实控势力",
                           self._faction_var)):
            tk.Checkbutton(opt, text=text, variable=var, anchor="w",
                           bg=THEME["panel_bg"], fg="#333333",
                           activebackground=THEME["panel_bg"],
                           font=(self.font_family, FONT_SIZES["panel_body"])
                           ).pack(fill="x")

        self._err = tk.Label(self, text="", bg=THEME["panel_bg"], fg="#B03A2E",
                             anchor="w",
                             font=(self.font_family, FONT_SIZES["panel_body"]))
        self._err.pack(fill="x", pady=(4, 0), **pad)

        buttons = tk.Frame(self, bg=THEME["panel_bg"])
        buttons.pack(fill="x", pady=(4, 12), **pad)
        tk.Button(buttons, text="保存", width=10,
                  command=self._confirm).pack(side="right")
        tk.Button(buttons, text="取消", width=10,
                  command=self._cancel).pack(side="right", padx=(0, 8))

    def _label(self, text, pad):
        tk.Label(self, text=text, bg=THEME["panel_bg"], fg="#222222",
                 font=(self.font_family, FONT_SIZES["panel_title"], "bold")
                 ).pack(anchor="w", pady=(6, 2), **pad)

    # ------------------------------------------------------------
    def _current_rows(self):
        """现有外官（跳过待删）+ 待新增，按 region_id 排序。"""
        rows = {}
        for item in self.world.officials_of_character(self.character.id):
            rid = item["region_id"]
            if rid in self._pending_remove:
                continue
            rows[rid] = OfficialRow(rid, item.get("name", ""), item.get("rank", ""))
        for rid, item in self._pending_set.items():
            rows[rid] = OfficialRow(rid, item.get("name", ""), item.get("rank", ""))
        return [rows[k] for k in sorted(rows)]

    def _on_region_pick(self):
        row = self.region_pick.selected_row()
        self._title_var.set(row.label if row is not None else "")

    def _remove_selected(self):
        row = self.official_pick.selected_row()
        if row is None:
            self._err.configure(text="请先在「当前外官」里选一条")
            return
        self._pending_set.pop(row.region_id, None)
        self._pending_remove.add(row.region_id)
        self._err.configure(text="")
        self.official_pick.refresh()

    def _add_selected(self):
        row = self.region_pick.selected_row()
        if row is None:
            self._err.configure(text="请先选一个行政区")
            return
        ch = self.world.character(self.character.id)
        if ch is None or not ch.appeared:
            self._err.configure(text="只允许给「已登场」人物任命外官")
            return
        name = self._title_var.get().strip() or row.label
        if not name:
            self._err.configure(text="官名不能为空")
            return
        self._pending_remove.discard(row.id)
        self._pending_set[row.id] = {"name": name,
                                     "character_id": self.character.id,
                                     "rank": row.rank}
        self._seats[row.id] = row.seat
        self._err.configure(text="")
        self.official_pick.refresh()

    def _confirm(self):
        self.plan = OfficialEditPlan(
            character_id=self.character.id,
            set_items=tuple(self._pending_set.items()),
            remove_regions=tuple(sorted(self._pending_remove)),
            move_to_seat=bool(self._move_var.get()),
            change_faction=bool(self._faction_var.get()),
            seats=dict(self._seats),
        )
        self.ok = True
        self.destroy()

    def _cancel(self):
        self.ok = False
        self.destroy()
