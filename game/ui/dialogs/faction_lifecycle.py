# -*- coding: utf-8 -*-
"""势力生命周期：新建（选都城 + 选君主 + 填信息）与删除（预览 + 级联）。

新建规则（需求 §3.1）：
    势力 id = 君主人物 id；必须在**无主据点**里选一个都城、
    在**已登场且无势力**的人物里选君主；禁止建立无据点势力。
    建完：君主 faction = 新 id、node / location = 都城、
    都城 Node.owner = 新 id、都城其它人物不动。

删除级联（需求 §3.1）：
    势力摘除 + 名下据点改无主 + 名下人物 faction / node / location 清空
    （appeared 不变）+ 仅删除「其人物属于被删势力」的外官条目 +
    player_faction_id 指向它时清空。整包 CompositeCommand，一次 undo 全退。

改 World 只走 Command（§8.3 第 36 条）。
"""

import logging
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox
from typing import List, Optional

from game.config.style import THEME, FONT_SIZES
from game.ui.dialogs.pick_list import PickList, WorldHolder
from game.ui.panels.list.columns import Column
from game.ui.window_utils import center_on_parent

logger = logging.getLogger(__name__)

WIN_W = 720
LIST_H = 220


# ============================================================
# 可选的都城 / 君主
# ============================================================
@dataclass(frozen=True)
class NodeOption:
    """可作都城的无主据点。"""
    id: str
    name: str
    state_name: str
    county_name: str
    level: int


@dataclass(frozen=True)
class RulerOption:
    """可作君主的已登场且无势力人物。"""
    id: str
    name: str
    leadership: int
    might: int
    intelligence: int
    politics: int
    charisma: int


NODE_COLUMNS = (
    Column("state",  "州", 52, "center", lambda r: r.state_name),
    Column("county", "郡", 62, "center", lambda r: r.county_name),
    Column("level",  "等级", 42, "center", lambda r: r.level, sort_numeric=True),
)
NODE_NAME_COLUMN = Column("name", "无主据点", 110, "w", lambda r: r.name)

RULER_COLUMNS = (
    Column("lead", "统", 34, "center", lambda r: r.leadership, sort_numeric=True),
    Column("migt", "武", 34, "center", lambda r: r.might, sort_numeric=True),
    Column("int",  "智", 34, "center", lambda r: r.intelligence, sort_numeric=True),
    Column("pol",  "政", 34, "center", lambda r: r.politics, sort_numeric=True),
    Column("cha",  "魅", 34, "center", lambda r: r.charisma, sort_numeric=True),
)
RULER_NAME_COLUMN = Column("name", "已登场·无势力人物", 150, "w", lambda r: r.name)


def free_nodes(world) -> List[NodeOption]:
    """无主据点（owner 为空 / owner 是脏数据都算无主）。"""
    return [NodeOption(n.id, n.name, world.state_name(n.state_id),
                       world.county_name(n.county_id), n.level)
            for n in world.nodes.values()
            if not n.owner or world.faction(n.owner) is None]


def free_rulers(world) -> List[RulerOption]:
    """已登场且没有势力的人物。"""
    return [RulerOption(c.id, c.display_name(), c.leadership, c.might,
                        c.intelligence, c.politics, c.charisma)
            for c in world.characters.values()
            if c.appeared and not c.faction]


@dataclass(frozen=True)
class FactionCreatePlan:
    """新建势力的全部变更（纯数据，供命令生成与测试）。"""
    faction_id: str
    values: dict                       # name / color / prestige / stance
    node_id: str
    character_id: str


def build_create_commands(world, plan: FactionCreatePlan) -> list:
    """新建势力 → 命令列表（势力 + 君主 + 都城 owner）。"""
    from game.core.edit_commands import (
        CharacterEditCommand, FactionCreateCommand, NodeEditCommand)

    ch = world.character(plan.character_id)
    node = world.node(plan.node_id)
    cmds = [FactionCreateCommand(plan.faction_id, plan.values)]

    proposed = {"faction": plan.faction_id, "node": plan.node_id,
                "location": plan.node_id}
    old = {k: getattr(ch, k) for k in proposed}
    new = {k: v for k, v in proposed.items() if old[k] != v}
    if new:
        cmds.append(CharacterEditCommand(ch.id,
                                         {k: old[k] for k in new}, new))
    if node.owner != plan.faction_id:
        cmds.append(NodeEditCommand(node.id, {"owner": node.owner},
                                    {"owner": plan.faction_id}))
    return cmds


def create_faction(parent, world, session, open_dialog) -> bool:
    """势力面板「新建势力」共用流程。返回 True = 已执行命令。"""
    if session is None or world is None:
        return False

    if not free_nodes(world):
        messagebox.showinfo("新建势力",
                            "无可选无主据点，无法新建势力。", parent=parent)
        return False
    if not free_rulers(world):
        messagebox.showinfo(
            "新建势力",
            "无可用君主人物，请先在人物面板设为登场 / 移出势力。",
            parent=parent)
        return False

    dlg = open_dialog(lambda: FactionCreateDialog(parent, world))
    if dlg is None or not dlg.ok or dlg.plan is None:
        logger.debug("新建势力：已取消")
        return False

    cmds = build_create_commands(world, dlg.plan)
    from game.core.edit_session import CompositeCommand
    session.execute(CompositeCommand(cmds, "新建势力") if len(cmds) > 1
                    else cmds[0])
    logger.info("新建势力：%s（君主 %s，都城 %s）",
                dlg.plan.faction_id, dlg.plan.character_id, dlg.plan.node_id)
    return True


# ============================================================
# 删除
# ============================================================
@dataclass(frozen=True)
class FactionDeletePlan:
    """删除势力的级联清单。"""
    faction_id: str
    node_ids: tuple
    character_ids: tuple
    official_ids: tuple
    vassal_ids: tuple = ()          # ★ 名下附庸（删除宗主后自动独立）


def plan_delete(world, faction_id) -> FactionDeletePlan:
    """算出级联对象（在**改 World 之前**算，因为外官归属依赖当前人物势力）。"""
    nodes = tuple(n.id for n in world.nodes.values() if n.owner == faction_id)
    chars = tuple(c.id for c in world.characters.values()
                  if c.faction == faction_id)
    officials = tuple(rid for rid, item in world.officials.items()
                      if item.get("character_id") in set(chars))
    vassals = tuple(f.id for f in sorted(world.factions.values(),
                                         key=lambda f: f.id)
                    if f.id != faction_id
                    and not getattr(f, "independent", True)
                    and f.overlord_id == faction_id)
    return FactionDeletePlan(faction_id, nodes, chars, officials, vassals)


def build_delete_commands(world, plan: FactionDeletePlan) -> list:
    """删除势力 → 命令列表（附庸独立 → 外官 → 人物 → 据点 → 势力）。

    删宗主时名下附庸自动独立（需求 §4 边界表）：独立 = 勾上 independent、
    宗主清空、附庸值归 0，与编辑弹窗的「附庸 → 独立」口径一致。
    """
    from game.core.edit_commands import (
        CharacterEditCommand, FactionDeleteCommand, FactionEditCommand,
        NodeEditCommand, OfficialRemoveCommand)

    cmds = []
    for fid in plan.vassal_ids:
        cmds.append(FactionEditCommand(
            fid,
            {"independent": False, "overlord_id": plan.faction_id,
             "vassal_value": world.factions[fid].vassal_value},
            {"independent": True, "overlord_id": None, "vassal_value": 0},
        ))
    for rid in plan.official_ids:
        item = world.official_of(rid)
        if item is not None:
            cmds.append(OfficialRemoveCommand(rid, item))
    for cid in plan.character_ids:
        ch = world.character(cid)
        proposed = {"faction": None, "node": None, "location": None}
        old = {k: getattr(ch, k) for k in proposed}
        new = {k: v for k, v in proposed.items() if old[k] != v}
        if new:
            cmds.append(CharacterEditCommand(cid, {k: old[k] for k in new}, new))
    for nid in plan.node_ids:
        node = world.node(nid)
        cmds.append(NodeEditCommand(nid, {"owner": node.owner}, {"owner": None}))
    cmds.append(FactionDeleteCommand(plan.faction_id))
    return cmds


def delete_faction(parent, world, faction, session, open_dialog) -> bool:
    """势力面板「删除势力」共用流程。返回 True = 已执行命令。"""
    if session is None or world is None or faction is None:
        return False

    plan = plan_delete(world, faction.id)
    dlg = open_dialog(lambda: FactionDeleteDialog(parent, world, faction, plan))
    if dlg is None or not dlg.ok:
        logger.debug("删除势力：已取消")
        return False

    cmds = build_delete_commands(world, plan)
    from game.core.edit_session import CompositeCommand
    session.execute(CompositeCommand(cmds, "删除势力") if len(cmds) > 1
                    else cmds[0])
    logger.info("删除势力：%s / 据点 %d / 人物 %d / 外官 %d",
                faction.id, len(plan.node_ids), len(plan.character_ids),
                len(plan.official_ids))
    return True


# ============================================================
# 弹窗：新建
# ============================================================
class FactionCreateDialog(tk.Toplevel):
    """新建势力：选都城 + 选君主 + 填信息。"""

    def __init__(self, master, world):
        super().__init__(master)
        self.world = world
        self.ok = False
        self.plan = None

        self._top = master.winfo_toplevel()
        self.font_family = getattr(self._top, "font_family", "TkDefaultFont")

        self._node_ids = [n.id for n in free_nodes(world)]
        self._ruler_ids = [r.id for r in free_rulers(world)]

        self.title("新建势力")
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

    def _build_ui(self):
        pad = {"padx": 16}
        tk.Label(self, text="新建势力", bg=THEME["panel_bg"], fg="#222222",
                 font=(self.font_family, FONT_SIZES["panel_title"] + 2, "bold")
                 ).pack(anchor="w", pady=(12, 4), **pad)

        self._label("① 选择都城（无主据点，单选）", pad)
        self.node_pick = PickList(
            self._holder_list(), WorldHolder(self.world),
            columns=NODE_COLUMNS, name_column=NODE_NAME_COLUMN,
            rows_fn=lambda: free_nodes(self.world),
            key_fn=lambda r: r.id,
        )
        self.node_pick.pack(fill="both", expand=True)

        self._label("② 选择君主（已登场且无势力人物，单选）", pad)
        self.ruler_pick = PickList(
            self._holder_list(), WorldHolder(self.world),
            columns=RULER_COLUMNS, name_column=RULER_NAME_COLUMN,
            rows_fn=lambda: free_rulers(self.world),
            key_fn=lambda r: r.id,
        )
        self.ruler_pick.pack(fill="both", expand=True)

        self._label("③ 势力信息", pad)
        form = tk.Frame(self, bg=THEME["panel_bg"])
        form.pack(fill="x", **pad)
        self._name_var = tk.StringVar()
        self._color_var = tk.StringVar(value="#888888")
        self._prestige_var = tk.StringVar(value="1000")
        self._stance_var = tk.StringVar(value="0")
        for label, var, width in (("势力名", self._name_var, 18),
                                  ("颜色", self._color_var, 10),
                                  ("威望", self._prestige_var, 8),
                                  ("关系（-100~100）", self._stance_var, 8)):
            row = tk.Frame(form, bg=THEME["panel_bg"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, width=16, anchor="w",
                     bg=THEME["panel_bg"], fg="#333333",
                     font=(self.font_family, FONT_SIZES["panel_body"])).pack(side="left")
            tk.Entry(row, textvariable=var, width=width).pack(side="left")

        self._err = tk.Label(self, text="", bg=THEME["panel_bg"],
                             fg="#B03A2E", anchor="w",
                             font=(self.font_family, FONT_SIZES["panel_body"]))
        self._err.pack(fill="x", pady=(4, 0), **pad)

        buttons = tk.Frame(self, bg=THEME["panel_bg"])
        buttons.pack(fill="x", pady=(4, 12), **pad)
        tk.Button(buttons, text="确定", width=10,
                  command=self._confirm).pack(side="right")
        tk.Button(buttons, text="取消", width=10,
                  command=self._cancel).pack(side="right", padx=(0, 8))

    def _holder_list(self):
        """列表容器：固定高度、自身 pack 进弹窗（内部再塞 PickList）。"""
        holder = tk.Frame(self, height=LIST_H, bg=THEME["panel_bg"])
        holder.pack(fill="x", padx=16, pady=(2, 6))
        holder.pack_propagate(False)
        return holder

    def _label(self, text, pad):
        tk.Label(self, text=text, bg=THEME["panel_bg"], fg="#222222",
                 font=(self.font_family, FONT_SIZES["panel_title"], "bold")
                 ).pack(anchor="w", pady=(4, 0), **pad)

    # ------------------------------------------------------------
    def _confirm(self):
        node_row = self.node_pick.selected_row()
        ruler_row = self.ruler_pick.selected_row()
        if node_row is None or ruler_row is None:
            self._err.configure(text="请先选择都城与君主")
            return

        name = self._name_var.get().strip() or ruler_row.name
        try:
            prestige = int(self._prestige_var.get() or 0)
            stance = int(self._stance_var.get() or 0)
        except ValueError:
            self._err.configure(text="威望 / 关系必须是整数")
            return
        stance = max(-100, min(100, stance))
        color = self._color_var.get().strip() or "#888888"

        # 势力 id = 君主人物 id
        self.plan = FactionCreatePlan(
            faction_id=ruler_row.id,
            values={"name": name, "color": color,
                    "prestige": prestige, "stance": stance},
            node_id=node_row.id,
            character_id=ruler_row.id,
        )
        self.ok = True
        self.destroy()

    def _cancel(self):
        self.ok = False
        self.destroy()


# ============================================================
# 弹窗：删除预览
# ============================================================
class FactionDeleteDialog(tk.Toplevel):
    """删除势力前的预览：据点 / 人物 / 外官清单。"""

    def __init__(self, master, world, faction, plan):
        super().__init__(master)
        self.world = world
        self.faction = faction
        self.plan = plan
        self.ok = False

        self._top = master.winfo_toplevel()
        self.font_family = getattr(self._top, "font_family", "TkDefaultFont")

        self.title("删除势力")
        self.transient(self._top)
        self.configure(bg=THEME["panel_bg"])
        self.resizable(False, False)

        self._build_ui()
        self.update_idletasks()
        center_on_parent(self, self._top, 560,
                         max(self.winfo_reqheight(), 360))
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.bind("<Escape>", lambda e: self._cancel())
        self.focus_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _build_ui(self):
        pad = {"padx": 16}
        tk.Label(self, text=f"删除势力：{self.faction.name}",
                 bg=THEME["panel_bg"], fg="#222222",
                 font=(self.font_family, FONT_SIZES["panel_title"] + 2, "bold")
                 ).pack(anchor="w", pady=(12, 4), **pad)
        tk.Label(self, text="以下内容会一并变更（可一次撤销）：",
                 bg=THEME["panel_bg"], fg="#555555",
                 font=(self.font_family, FONT_SIZES["panel_body"])
                 ).pack(anchor="w", **pad)

        for title, names in (
            ("名下附庸 → 自动独立（宗主清空、附庸值归 0）",
             self._names(self.plan.vassal_ids, "faction")),
            ("名下据点 → 变无主", self._names(self.plan.node_ids, "node")),
            ("名下人物 → 势力 / 所属 / 所在清空（登场状态不变）",
             self._names(self.plan.character_ids, "character")),
            ("其人物的外官条目 → 删除", self._official_names()),
        ):
            tk.Label(self, text=f"{title}（{len(names)}）",
                     bg=THEME["panel_bg"], fg="#222222",
                     font=(self.font_family, FONT_SIZES["panel_title"], "bold")
                     ).pack(anchor="w", pady=(8, 0), **pad)
            tk.Label(self, text="、".join(names[:12]) + (" 等" if len(names) > 12 else "")
                     if names else "（无）",
                     bg=THEME["panel_bg"], fg="#333333", justify="left",
                     anchor="w", wraplength=520,
                     font=(self.font_family, FONT_SIZES["panel_body"])
                     ).pack(anchor="w", **pad)

        buttons = tk.Frame(self, bg=THEME["panel_bg"])
        buttons.pack(fill="x", pady=(14, 12), **pad)
        tk.Button(buttons, text="删除", width=10,
                  command=self._confirm).pack(side="right")
        tk.Button(buttons, text="取消", width=10,
                  command=self._cancel).pack(side="right", padx=(0, 8))

    def _names(self, ids, kind):
        out = []
        for i in ids:
            if kind == "node":
                obj = self.world.node(i)
            elif kind == "faction":
                obj = self.world.faction(i)
            else:
                obj = self.world.character(i)
            if obj is not None:
                out.append(obj.name)
        return out

    def _official_names(self):
        out = []
        for rid in self.plan.official_ids:
            label = self.world.official_label(rid)
            out.append(label or rid)
        return out

    def _confirm(self):
        self.ok = True
        self.destroy()

    def _cancel(self):
        self.ok = False
        self.destroy()
