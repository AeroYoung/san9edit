# -*- coding: utf-8 -*-
"""据点批量易主：选新 owner（势力列表 + 无主）+ 可选「同步调整人物归属」。

入口：据点面板右键「批量修改所属」（单选 / 多选都走这里）。
改 World 只走 Command：NodeEditCommand +（勾选时）CharacterEditCommand，
整包 CompositeCommand，一次 undo 全部回退（§8.3 第 36 条 / §10.1）。

勾选级联时的规则（需求 §3.2）：
    该据点**已登场**人物：faction = 新 owner；node = location = 该据点；
    新 owner 为空（无主）→ 三者清空（下野）。未登场人物不动。
"""

import logging
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import List, Optional

from game.config.style import THEME, FONT_SIZES
from game.ui.dialogs.node_fields import owner_options
from game.ui.window_utils import center_on_parent

logger = logging.getLogger(__name__)

WIN_W = 520
WIN_MIN_H = 300


@dataclass(frozen=True)
class OwnerChange:
    """一个据点的易主计划。"""
    node_id: str
    node_name: str
    old_owner: Optional[str]
    new_owner: Optional[str]
    persons: tuple = ()          # 需要同步归属的已登场人物 id


def plan_owner_changes(world, rows, new_owner, cascade) -> List[OwnerChange]:
    """纯函数：算出要改的据点（已经是新 owner 的跳过）。"""
    plans = []
    for row in rows:
        node = world.node(row.node_id)
        if node is None or node.owner == new_owner:
            continue
        persons = ()
        if cascade:
            persons = tuple(c.id for c in world.characters.values()
                            if c.node == node.id and c.appeared)
        plans.append(OwnerChange(node.id, node.name, node.owner,
                                 new_owner, persons))
    return plans


def person_change(world, cid, node_id, new_owner):
    """人物的 (old, new)：只含真正变化的字段（新 owner 为空 → 下野）。"""
    ch = world.character(cid)
    proposed = {"faction": new_owner, "node": node_id, "location": node_id}
    old = {k: getattr(ch, k) for k in proposed}
    new = {k: v for k, v in proposed.items() if old[k] != v}
    return {k: old[k] for k in new}, new


def build_commands(world, plans) -> list:
    """计划 → 命令列表（据点 owner 各自一条；勾选级联时人物各补一条）。"""
    from game.core.edit_commands import CharacterEditCommand, NodeEditCommand

    cmds = []
    for plan in plans:
        cmds.append(NodeEditCommand(plan.node_id,
                                    {"owner": plan.old_owner},
                                    {"owner": plan.new_owner}))
        for cid in plan.persons:
            old, new = person_change(world, cid, plan.node_id, plan.new_owner)
            if new:
                cmds.append(CharacterEditCommand(cid, old, new))
    return cmds


def change_node_owner(parent, world, rows, session, open_dialog) -> bool:
    """据点面板「批量修改所属」共用流程。返回 True = 已执行命令。"""
    if session is None or world is None or not rows:
        return False

    dlg = open_dialog(lambda: ChangeOwnerDialog(parent, world, rows))
    if dlg is None or not dlg.ok:
        logger.debug("批量修改所属：已取消")
        return False

    plans = plan_owner_changes(world, rows, dlg.new_owner, dlg.cascade)
    cmds = build_commands(world, plans)
    if not cmds:
        messagebox.showinfo("批量修改所属", "选中的据点已经属于该势力。",
                            parent=parent)
        return False

    from game.core.edit_session import CompositeCommand
    if len(cmds) == 1:
        session.execute(cmds[0])
    else:
        session.execute(CompositeCommand(cmds, "批量修改所属"))
    logger.info("批量修改所属：目标 %s / 据点 %d 个 / 同步人物 %d 人",
                dlg.new_owner, len(plans),
                sum(len(p.persons) for p in plans))
    return True


# ============================================================
# 弹窗
# ============================================================
class ChangeOwnerDialog(tk.Toplevel):
    """选新 owner + 是否同步调整人物归属。"""

    def __init__(self, master, world, rows):
        super().__init__(master)
        self.world = world
        self.rows = list(rows)
        self.ok = False
        self.new_owner = None
        self.cascade = False

        self._top = master.winfo_toplevel()
        self.font_family = getattr(self._top, "font_family", "TkDefaultFont")

        self.title("批量修改所属")
        self.transient(self._top)
        self.configure(bg=THEME["panel_bg"])
        self.resizable(False, False)

        self._build_ui()
        self._refresh_info()
        self.update_idletasks()
        center_on_parent(self, self._top, WIN_W,
                         max(self.winfo_reqheight(), WIN_MIN_H))
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.bind("<Escape>", lambda e: self._cancel())
        self.focus_set()

    def _build_ui(self):
        pad = {"padx": 16}
        tk.Label(
            self, text=f"批量修改所属（{len(self.rows)} 个据点）",
            bg=THEME["panel_bg"], fg="#222222",
            font=(self.font_family, FONT_SIZES["panel_title"] + 2, "bold"),
        ).pack(anchor="w", pady=(12, 6), **pad)

        row = tk.Frame(self, bg=THEME["panel_bg"])
        row.pack(fill="x", **pad)
        tk.Label(row, text="新所属：", bg=THEME["panel_bg"], fg="#333333",
                 font=(self.font_family, FONT_SIZES["panel_body"])).pack(side="left")
        options = owner_options(self.world)
        self._labels = [label for _v, label in options]
        self._value_by_label = {label: v for v, label in options}
        self._owner_var = tk.StringVar(value=self._labels[0] if self._labels else "")
        ttk.Combobox(row, textvariable=self._owner_var, values=self._labels,
                     state="readonly", width=18).pack(side="left")
        self._owner_var.trace_add("write", lambda *a: self._refresh_info())

        self._cascade_var = tk.BooleanVar(value=False)      # 默认不勾选
        tk.Checkbutton(
            self, text="同步调整人物归属（该据点已登场人物：势力 / 所属 / 所在一并改）",
            variable=self._cascade_var, bg=THEME["panel_bg"], fg="#333333",
            activebackground=THEME["panel_bg"], anchor="w",
            font=(self.font_family, FONT_SIZES["panel_body"]),
            command=self._refresh_info,
        ).pack(fill="x", pady=(8, 0), **pad)

        self._info = tk.Label(
            self, text="", bg=THEME["panel_bg"], fg="#555555",
            justify="left", anchor="w", wraplength=WIN_W - 48,
            font=(self.font_family, FONT_SIZES["panel_body"]),
        )
        self._info.pack(fill="x", pady=(10, 0), **pad)

        buttons = tk.Frame(self, bg=THEME["panel_bg"])
        buttons.pack(fill="x", pady=(12, 12), **pad)
        tk.Button(buttons, text="确定", width=10,
                  command=self._confirm).pack(side="right")
        tk.Button(buttons, text="取消", width=10,
                  command=self._cancel).pack(side="right", padx=(0, 8))

    def _current_owner(self):
        return self._value_by_label.get(self._owner_var.get())

    def _refresh_info(self):
        new_owner = self._current_owner()
        plans = plan_owner_changes(self.world, self.rows, new_owner,
                                   self._cascade_var.get())
        skipped = len(self.rows) - len(plans)
        persons = sum(len(p.persons) for p in plans)
        f = self.world.faction(new_owner) if new_owner else None
        target = f.name if f is not None else "无主"
        lines = [f"目标势力：{target}",
                 f"会改变所属：{len(plans)} 个据点",
                 f"已是该势力（跳过）：{skipped} 个"]
        if self._cascade_var.get():
            lines.append(f"会同步归属的已登场人物：{persons} 人")
        else:
            lines.append("仅改据点所属，不动人物")
        self._info.configure(text="\n".join(lines))

    def _confirm(self):
        self.new_owner = self._current_owner()
        self.cascade = bool(self._cascade_var.get())
        self.ok = True
        self.destroy()

    def _cancel(self):
        self.ok = False
        self.destroy()
