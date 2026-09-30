# -*- coding: utf-8 -*-
"""人物「移动到据点」：据点单选弹窗 + 实时信息块 + 二次确认 + 命令生成。

入口：人物面板右键「移动到据点」。
改 World 只走 Command —— CharacterEditCommand / CompositeCommand（§8.3 第 36 条）。

单人变更规则（需求 §3.6）：
    君主 · 目标无主 / 他势力      → 阻断（不进命令，只提示）
    君主 · 目标 owner == 自己 id  → 只改 node / location
    非君主 · 目标有主             → node / location 改，faction 跟随目标 owner
    非君主 · 目标无主             → node / location 改，faction = None（下野）
    role 本次不动；appeared 只在「目标有主 + 询问答是」时置 True。

弹窗内的据点列表是据点面板的**裁剪副本**：强制单选、无右键菜单、不分组，
列配置与据点面板共享（PANEL_KEY = "node"）。
"""

import logging
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import messagebox, ttk
from typing import List, Optional

from game.config.style import THEME, FONT_SIZES
from game.ui.dialogs.pick_list import PickList, WorldHolder
from game.ui.panels.node_panel import (
    COLUMNS as NODE_COLUMNS,
    NAME_COLUMN as NODE_NAME_COLUMN,
    NodeRow,
)
from game.ui.window_utils import center_on_parent

logger = logging.getLogger(__name__)

WIN_W = 660
WIN_H = 580
LIST_H = 300

# 单人变更分类
KIND_UNCHANGED = "unchanged"    # node 已在目标 → 不进命令
KIND_BLOCKED = "blocked"        # 君主不能去 → 不进命令
KIND_NODE_ONLY = "node_only"    # 仅换据点、势力不变
KIND_FACTION = "faction"        # 会变更势力
KIND_FREE = "free"              # 会下野


def target_owner(world, node):
    """目标据点的势力 id；无主 / owner 是脏数据 → None（需求 §3.5）。"""
    if node is None or not node.owner:
        return None
    return node.owner if world.faction(node.owner) is not None else None


@dataclass(frozen=True)
class CharMove:
    id: str
    name: str
    kind: str
    old: dict = field(default_factory=dict)     # 只含真正变化的字段
    new: dict = field(default_factory=dict)
    appeared_pending: bool = False              # 未登场 + 目标有主 → 「会设为登场」


@dataclass(frozen=True)
class MovePlan:
    node_id: str
    owner: Optional[str]
    moves: tuple            # 要执行的变更（不含阻断 / 已在目标）
    blocked: tuple          # 被阻断的君主
    unchanged: int          # 已在目标据点的人数


def plan_moves(world, rows, node_id, set_appeared=False) -> List[CharMove]:
    """按需求 §3.6 逐人算 old / new（纯函数，供信息块与命令生成共用）。

    - old / new 只含**真正变化**的字段（§3.9 / §10.2）
    - set_appeared=True 时，未登场人物 + 目标有主 → 追加 appeared=True
    """
    node = world.node(node_id)
    owner = target_owner(world, node)
    result = []

    for row in rows:
        ch = world.character(row.id)
        if ch is None:
            logger.warning("人物不存在：%s", row.id)
            continue

        if ch.node == node_id:
            result.append(CharMove(ch.id, ch.name, KIND_UNCHANGED))
            continue

        is_ruler = ch.faction is not None and ch.faction == ch.id
        if is_ruler and owner != ch.id:      # 无主 / 他势力 → 阻断
            result.append(CharMove(ch.id, ch.name, KIND_BLOCKED))
            continue

        proposed = {"node": node_id, "location": node_id}
        if owner is None:
            if ch.faction is not None:
                proposed["faction"] = None
                kind = KIND_FREE
            else:
                kind = KIND_NODE_ONLY
        elif ch.faction == owner:
            kind = KIND_NODE_ONLY
        else:
            proposed["faction"] = owner
            kind = KIND_FACTION

        # 君主按 §3.6 第 3 条：appeared 不变
        pending = (not ch.appeared) and owner is not None and not is_ruler
        if set_appeared and pending:
            proposed["appeared"] = True

        old = {k: getattr(ch, k) for k in proposed}
        new = {k: v for k, v in proposed.items() if old[k] != v}
        if not new:
            result.append(CharMove(ch.id, ch.name, KIND_UNCHANGED))
            continue
        result.append(CharMove(
            ch.id, ch.name, kind,
            old={k: old[k] for k in new}, new=new,
            appeared_pending=pending,
        ))
    return result


def build_commands(plan: MovePlan) -> list:
    """MovePlan → CharacterEditCommand 列表（无变化者已在外层剔除）。"""
    from game.core.edit_commands import CharacterEditCommand
    return [CharacterEditCommand(m.id, m.old, m.new)
            for m in plan.moves if m.new]


def dialog_move_characters(parent, world, rows, session, open_dialog) -> bool:
    """人物面板「移动到据点」共用流程。返回 True = 已执行命令（调用方负责刷新）。

    步骤：守卫 → 开弹窗（模态）→ 弹窗内完成 登场询问 + 二次确认 →
    命令生成 → session.execute。
    """
    if session is None or world is None or not rows:
        return False

    dlg = open_dialog(lambda: MoveToNodeDialog(parent, world, rows))
    if dlg is None or not dlg.ok or dlg.plan is None:
        logger.debug("移动到据点：已取消")
        return False

    cmds = build_commands(dlg.plan)
    if not cmds:
        logger.debug("移动到据点：无字段变化，不生成命令")
        return False

    from game.core.edit_session import CompositeCommand
    if len(cmds) == 1:
        session.execute(cmds[0])
    else:
        session.execute(CompositeCommand(cmds, "移动到据点"))
    logger.info("移动到据点：目标 %s / 变更 %d 人 / 阻断 %d 人 / 跳过 %d 人",
                dlg.plan.node_id, len(cmds), len(dlg.plan.blocked),
                dlg.plan.unchanged)
    return True


# ============================================================
# 弹窗内嵌的据点列表（据点面板的裁剪副本，列配置与据点面板共享）
# ============================================================
class NodePickList(PickList):
    PANEL_KEY = "node"                 # ★ 复用据点面板的列配置（PANEL_COLUMNS）

    def __init__(self, master, world):
        super().__init__(
            master, WorldHolder(world),
            columns=NODE_COLUMNS, name_column=NODE_NAME_COLUMN,
            rows_fn=lambda: self._fetch(world),
            key_fn=lambda row: row.node_id,
        )

    @staticmethod
    def _fetch(world):
        counts = world.count_characters_by_node()
        return [NodeRow.from_node(n, world, person_count=counts.get(n.id, 0))
                for n in world.nodes.values()]


# ============================================================
# 通用据点选择（给「编辑人物」的所属 / 所在用）
# ============================================================
class NodePickDialog(tk.Toplevel):
    """通用据点单选弹窗：确定后 `node_id` 为目标据点，取消为 None。"""

    def __init__(self, master, world, title="选择据点"):
        super().__init__(master)
        self.world = world
        self.node_id = None

        self._top = master.winfo_toplevel()
        self.font_family = getattr(self._top, "font_family", "TkDefaultFont")

        self.title(title)
        self.transient(self._top)
        self.configure(bg=THEME["panel_bg"])
        self.resizable(False, False)

        tk.Label(self, text=title, bg=THEME["panel_bg"], fg="#222222",
                 font=(self.font_family, FONT_SIZES["panel_title"] + 2, "bold")
                 ).pack(anchor="w", padx=16, pady=(12, 2))
        holder = tk.Frame(self, height=LIST_H, bg=THEME["panel_bg"])
        holder.pack(fill="x", padx=12, pady=(2, 6))
        holder.pack_propagate(False)
        self.picker = NodePickList(holder, world)
        self.picker.pack(fill="both", expand=True)

        buttons = tk.Frame(self, bg=THEME["panel_bg"])
        buttons.pack(fill="x", padx=16, pady=(0, 12))
        tk.Button(buttons, text="确定", width=10,
                  command=self._confirm).pack(side="right")
        tk.Button(buttons, text="取消", width=10,
                  command=self.destroy).pack(side="right", padx=(0, 8))

        self.update_idletasks()
        center_on_parent(self, self._top, WIN_W, max(self.winfo_reqheight(), 420))
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.bind("<Escape>", lambda e: self.destroy())
        self.focus_set()

    def _confirm(self):
        row = self.picker.selected_row()
        self.node_id = row.node_id if row is not None else None
        self.destroy()


def pick_node(parent, world, title="选择据点"):
    """弹出据点单选窗，返回选中的 node_id（取消 → None）。"""
    dlg = NodePickDialog(parent, world, title)
    parent.wait_window(dlg)
    return dlg.node_id


# ============================================================
# 弹窗
# ============================================================
class MoveToNodeDialog(tk.Toplevel):
    """移动目标选择：上部据点列表 + 下部信息块 + 确定/取消。"""

    # 信息块行序（§3.4）
    INFO_KEYS = ("target", "selected", "node", "node_only", "faction",
                 "free", "appear", "blocked")

    def __init__(self, master, world, rows):
        super().__init__(master)
        self.world = world
        self.rows = list(rows)
        self.ok = False
        self.plan = None

        self._top = master.winfo_toplevel()
        self.font_family = getattr(self._top, "font_family", "TkDefaultFont")
        self._info_labels = {}

        self.title("移动到据点")
        self.transient(self._top)
        self.configure(bg=THEME["panel_bg"])
        self.resizable(False, False)

        self._build_ui()
        self._refresh_info()          # 初始态：未选中 → 「请选择一个据点」
        self.update_idletasks()
        center_on_parent(self, self._top, WIN_W, WIN_H)
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
        tk.Label(
            self, text="移动到据点", bg=THEME["panel_bg"], fg="#222222",
            font=(self.font_family, FONT_SIZES["panel_title"] + 2, "bold"),
        ).pack(anchor="w", padx=16, pady=(12, 2))

        tk.Label(
            self, text="选择目标据点（单选）：", bg=THEME["panel_bg"],
            fg="#555555", font=(self.font_family, FONT_SIZES["panel_body"]),
        ).pack(anchor="w", padx=16)

        holder = tk.Frame(self, height=LIST_H, bg=THEME["panel_bg"])
        holder.pack(fill="x", padx=12, pady=(2, 6))
        holder.pack_propagate(False)
        self.picker = NodePickList(holder, self.world)
        self.picker.pack(fill="both", expand=True)
        self.picker.tree.bind("<<TreeviewSelect>>", self._on_pick)

        tk.Frame(self, bg=THEME["status_sep"], height=1).pack(
            fill="x", padx=16, pady=(0, 6))
        self._build_info(self)

        buttons = tk.Frame(self, bg=THEME["panel_bg"])
        buttons.pack(fill="x", padx=16, pady=(4, 12))
        self._ok_btn = tk.Button(
            buttons, text="确定", width=10, command=self._confirm,
            state="disabled",
        )
        self._ok_btn.pack(side="right")
        tk.Button(buttons, text="取消", width=10,
                  command=self._cancel).pack(side="right", padx=(0, 8))

    def _build_info(self, parent):
        wrap = tk.Frame(parent, bg=THEME["panel_bg"])
        wrap.pack(fill="x", padx=16, pady=(0, 4))
        for key in self.INFO_KEYS:
            label = tk.Label(
                wrap, text="", bg=THEME["panel_bg"], fg="#333333",
                font=(self.font_family, FONT_SIZES["panel_body"]),
                anchor="w", justify="left",
            )
            label.pack(fill="x")
            self._info_labels[key] = label

    # ------------------------------------------------------------
    # 选择 / 信息块
    # ------------------------------------------------------------
    def _selected_row(self):
        return self.picker.selected_row()

    def _on_pick(self, event=None):
        self._refresh_info()

    def _refresh_info(self):
        row = self._selected_row()
        if row is None:
            self._set_info([(k, "") for k in self.INFO_KEYS]
                           + [("target", "请选择一个据点")])
            self._ok_btn.configure(state="disabled")
            return

        node_id = row.node_id
        owner = target_owner(self.world, self.world.node(node_id))
        owner_name = "无主"
        if owner:
            f = self.world.faction(owner)
            owner_name = f.name if f is not None else "无主"

        # 信息块按「会同时设为登场」预估（§3.4）
        moves = plan_moves(self.world, self.rows, node_id, set_appeared=True)
        blocked = [m for m in moves if m.kind == KIND_BLOCKED]
        active = [m for m in moves if m.kind not in (KIND_UNCHANGED, KIND_BLOCKED)]
        counts = {
            KIND_NODE_ONLY: sum(1 for m in active if m.kind == KIND_NODE_ONLY),
            KIND_FACTION: sum(1 for m in active if m.kind == KIND_FACTION),
            KIND_FREE: sum(1 for m in active if m.kind == KIND_FREE),
        }
        pending = sum(1 for m in active if m.appeared_pending)

        lines = [
            ("target", "目标据点：%s · %s · %s · %s · 规模 %s · %s" % (
                row.state_name, row.county_name, row.name,
                row.display_type, row.level, owner_name)),
            ("selected", "选中人数：%d" % (len(self.rows) - len(blocked))),
            ("node", "会改变据点：%d 人" % len(active)),
            ("node_only", "仅换据点、势力不变：%d 人" % counts[KIND_NODE_ONLY]),
            ("faction", "会变更势力：%d 人" % counts[KIND_FACTION]),
            ("free", "会下野：%d 人" % counts[KIND_FREE]),
            ("appear", "会设为登场：%d 人（确定后将询问）" % pending),
            ("blocked", "被阻断：%s" % self._blocked_text(blocked)),
        ]
        self._set_info(lines)
        self._ok_btn.configure(state="normal" if active else "disabled")

    @staticmethod
    def _blocked_text(blocked):
        if not blocked:
            return "无"
        names = "、".join(m.name for m in blocked[:3])
        if len(blocked) > 3:
            names += " 等 %d 人" % len(blocked)
        return names

    def _set_info(self, lines):
        for key, text in lines:
            label = self._info_labels.get(key)
            if label is not None:
                label.configure(text=text)

    # ------------------------------------------------------------
    # 确定 / 取消
    # ------------------------------------------------------------
    def _confirm(self):
        row = self._selected_row()
        if row is None:
            return
        node_id = row.node_id
        owner = target_owner(self.world, self.world.node(node_id))

        # §3.10 全员已在目标据点
        preview = plan_moves(self.world, self.rows, node_id, set_appeared=False)
        if not [m for m in preview
                if m.kind not in (KIND_UNCHANGED, KIND_BLOCKED)]:
            if any(m.kind == KIND_BLOCKED for m in preview):
                self._all_blocked(preview)
                return
            messagebox.showinfo("移动到据点", "选中的人物已经在目标据点。",
                                parent=self)
            return

        # §3.7 未登场询问（只在目标有主时）
        set_appeared = False
        pending = [m for m in preview if m.appeared_pending]
        if pending and owner is not None:
            set_appeared = messagebox.askyesno(
                "同时设为登场",
                "目标据点「%s」有势力。\n是否同时将选中的 %d 位未登场人物设为登场？"
                % (row.name, len(pending)),
                parent=self, default="yes",
            )

        moves = plan_moves(self.world, self.rows, node_id,
                           set_appeared=set_appeared)
        active = [m for m in moves
                  if m.kind not in (KIND_UNCHANGED, KIND_BLOCKED)]
        blocked = [m for m in moves if m.kind == KIND_BLOCKED]
        unchanged = sum(1 for m in moves if m.kind == KIND_UNCHANGED)

        # §3.8 二次确认
        if not messagebox.askyesno(
            "确认移动",
            self._confirm_text(row, owner, active, blocked, set_appeared),
            parent=self,
        ):
            return                       # 取消 → 返回弹窗，不关闭

        self.plan = MovePlan(
            node_id=node_id, owner=owner,
            moves=tuple(m for m in active if m.new),
            blocked=tuple(blocked), unchanged=unchanged,
        )
        self.ok = True
        self.destroy()

    def _confirm_text(self, row, owner, active, blocked, set_appeared):
        owner_name = "无主"
        if owner:
            f = self.world.faction(owner)
            owner_name = f.name if f is not None else "无主"
        counts = {
            KIND_FACTION: sum(1 for m in active if m.kind == KIND_FACTION),
            KIND_FREE: sum(1 for m in active if m.kind == KIND_FREE),
        }
        appeared_n = sum(1 for m in active
                         if set_appeared and m.new.get("appeared"))
        lines = [
            "目标据点：%s · %s · %s · %s" % (
                row.state_name, row.county_name, row.name, owner_name),
            "变更据点：%d 人" % len(active),
            "变更势力：%d 人" % counts[KIND_FACTION],
            "下野：%d 人" % counts[KIND_FREE],
            "设为登场：%d 人" % appeared_n,
            "被阻断君主：%s" % self._blocked_text(blocked),
            "",
            "确认执行？",
        ]
        return "\n".join(lines)

    def _all_blocked(self, moves):
        blocked = [m for m in moves if m.kind == KIND_BLOCKED]
        logger.info("移动到据点：%d 位君主被阻断", len(blocked))
        messagebox.showwarning(
            "君主不能移动到他处",
            "选中的君主只能移动到自己的据点。\n\n被阻断：%s"
            % self._blocked_text(blocked),
            parent=self,
        )
        self.ok = False
        self.destroy()

    def _cancel(self):
        if not self.ok:
            logger.debug("移动到据点：取消")
        self.ok = False
        self.destroy()
