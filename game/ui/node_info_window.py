# -*- coding: utf-8 -*-
"""据点情报窗口。

内容（自上而下）：
    1. 据点基本情况（州 / 郡 / 县 / 类型 / 等级 / 郡治 / 势力 / 人物数 / 驻军）
    2. 据点外官（县级）
    3. 所属州郡的基本情况 + 州 / 郡外官
    4. 州郡外官各实际控制了多少据点
    5. 该郡里不被外官控制的据点，实际在谁手里
    6. 宣称权冲突：县 / 郡 / 州三级外官是否同属一个势力

只读展示，不涉及 Command（改 World 的入口在据点面板右键「编辑」）。
"""

import logging
import tkinter as tk

from game.config.style import THEME, FONT_SIZES
from game.ui.window_utils import center_on_parent

logger = logging.getLogger(__name__)

WIN_W = 620
WIN_MIN_H = 420

BODY_FG = "#333333"
MUTED_FG = "#999999"
WARN_FG = "#B03A2E"
NAME_LIMIT = 3          # 每类最多列几个据点名
TITLE = "据点情报"


class NodeInfoWindow(tk.Toplevel):
    def __init__(self, master, node, world, font_family="TkDefaultFont"):
        super().__init__(master)
        self.node = node
        self.world = world
        self.font_family = font_family
        self._top = master.winfo_toplevel()

        logger.debug("打开据点情报窗口：%s %s", node.id, node.name)
        self.title(f"{node.name} — {TITLE}")
        self.transient(self._top)
        self.configure(bg=THEME["panel_bg"])
        self.resizable(False, True)

        self._build_ui()
        self.update_idletasks()
        center_on_parent(self, self._top, WIN_W,
                         max(self.winfo_reqheight(), WIN_MIN_H))
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.bind("<Escape>", lambda e: self.destroy())
        self.focus_set()

    # ------------------------------------------------------------
    # UI 工具
    # ------------------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 16}
        tk.Label(
            self, text=self.node.name, bg=THEME["panel_bg"], fg="#222222",
            font=(self.font_family, FONT_SIZES["panel_title"] + 4, "bold"),
        ).pack(pady=(14, 6))

        self._section("据点", pad)
        self._line(self._node_summary(), pad)

        self._section("外官（县）", pad)
        self._line(self._official_line(self.node.id) or "（无）", pad,
                   muted=self._official_line(self.node.id) is None)

        self._section("所属州郡", pad)
        for text in self._region_lines():
            self._line(text, pad)

        self._section("州郡外官的实际控制", pad)
        for text in self._control_lines():
            self._line(text, pad)

        self._section(f"本郡其它据点（{self._county_name()}）", pad)
        for text in self._other_holder_lines():
            self._line(text, pad)

        self._section("宣称权冲突", pad)
        text, conflict = self._claim_line()
        self._line(text, pad, warn=conflict)

        tk.Frame(self, bg=THEME["panel_bg"], height=12).pack()

    def _section(self, text, pad):
        tk.Label(
            self, text=text, bg=THEME["panel_bg"], fg="#222222",
            font=(self.font_family, FONT_SIZES["panel_title"], "bold"),
        ).pack(anchor="w", pady=(8, 2), **pad)

    def _line(self, text, pad, muted=False, warn=False):
        fg = MUTED_FG if muted else (WARN_FG if warn else BODY_FG)
        tk.Label(
            self, text=text, bg=THEME["panel_bg"], fg=fg,
            justify="left", anchor="w",
            wraplength=WIN_W - 48,
            font=(self.font_family, FONT_SIZES["panel_body"]),
        ).pack(anchor="w", pady=1, **pad)

    # ------------------------------------------------------------
    # 数据
    # ------------------------------------------------------------
    def _county_name(self):
        return self.world.county_name(self.node.county_id)

    def _node_summary(self):
        node = self.node
        owner = "无主"
        if node.owner:
            f = self.world.faction(node.owner)
            owner = f.name if f is not None else "无主（脏数据）"
        kind = "郡治" if node.is_capital else node.type
        persons = len([c for c in self.world.characters.values()
                       if c.node == node.id and c.appeared])
        return (f"%s · %s · %s（%s） · 等级 %d · %s\n"
                f"编号 %s · 势力 %s · 登场人物 %d · 驻军 %s"
                % (self.world.state_name(node.state_id),
                   self.world.county_name(node.county_id),
                   node.name, node.id, node.level, kind,
                   node.id, owner, persons, f"{node.troops:,}"))

    def _official_of(self, region_id):
        return self.world.official_of(region_id)

    def _official_line(self, region_id):
        """「官名-姓名」；无外官 → None。"""
        label = self.world.official_label(region_id)
        return label or None

    def _faction_of_official(self, item):
        """外官的势力 id（君主即 faction == id；无势力 → 人物 id）。"""
        if not item:
            return None
        ch = self.world.character(item.get("character_id"))
        if ch is None:
            return None
        return ch.faction or ch.id

    def _region_lines(self):
        """州 / 郡两行的名称 + 外官。"""
        lines = []
        for name, rid, item in (
            ("州", self.node.state_id, self._official_of(self.node.state_id)),
            ("郡", self.node.county_id, self._official_of(self.node.county_id)),
        ):
            region = (self.world.state_name(rid) if name == "州"
                      else self.world.county_name(rid))
            label = self.world.official_label(rid)
            lines.append(f"{name}：{region}（{rid}）" +
                         (f" · 外官 {label}" if label else " · 外官（无）"))
        return lines

    def _control_lines(self):
        """州 / 郡外官各控制多少据点（本州、全部）。"""
        lines = []
        for name, rid in (("州", self.node.state_id), ("郡", self.node.county_id)):
            item = self._official_of(rid)
            if not item:
                lines.append(f"{name}外官：（无）")
                continue
            fid = self._faction_of_official(item)
            label = self.world.official_label(rid)
            if fid is None:
                lines.append(f"{label}：人物不在剧本中")
                continue
            in_state = [n for n in self.world.nodes.values()
                        if n.owner == fid and n.id[:2] == self.node.state_id[:2]]
            total = [n for n in self.world.nodes.values() if n.owner == fid]
            f = self.world.faction(fid)
            fname = f.name if f is not None else "—"
            lines.append(f"{label}（势力 {fname}）：本州 {len(in_state)} 个据点 / "
                         f"全部 {len(total)} 个据点")
        return lines

    def _other_holder_lines(self):
        """本郡里不被「郡外官（无则州外官）」控制的据点，实际在谁手里。"""
        county_id = self.node.county_id
        ref_item = self._official_of(county_id) or self._official_of(
            self.node.state_id)
        ref_fid = self._faction_of_official(ref_item)

        buckets = {}
        for n in self.world.nodes.values():
            if n.id[:4] != county_id:
                continue
            if n.owner == ref_fid:
                continue
            if n.owner and self.world.faction(n.owner) is not None:
                key = self.world.faction(n.owner).name
            elif n.owner:
                key = f"脏数据（{n.owner}）"
            else:
                key = "无主"
            buckets.setdefault(key, []).append(n.name)

        if not buckets:
            return ["（本郡据点在上述外官治下）"]
        lines = []
        for key in sorted(buckets, key=lambda k: (-len(buckets[k]), k)):
            names = buckets[key]
            shown = "、".join(names[:NAME_LIMIT])
            more = f" 等 {len(names)} 个" if len(names) > NAME_LIMIT else ""
            lines.append(f"{key}：{len(names)} 个 —— {shown}{more}")
        return lines

    def _claim_line(self):
        """县 / 郡 / 州三级外官的势力是否一致 → (文案, 是否冲突)。"""
        rows = []
        for name, rid in (("县", self.node.id),
                          ("郡", self.node.county_id),
                          ("州", self.node.state_id)):
            item = self._official_of(rid)
            if not item:
                rows.append((name, None, None))
                continue
            fid = self._faction_of_official(item)
            f = self.world.faction(fid) if fid else None
            rows.append((name, self.world.official_label(rid),
                         f.name if f is not None else "—"))

        parts = [f"{n}外官 {label}（{fname}）" if label else f"{n}外官（无）"
                 for n, label, fname in rows]
        distinct = {fname for _, label, fname in rows if label}
        if len(distinct) > 1:
            return ("存在宣称权冲突：县 / 郡 / 州外官分属不同势力 → "
                    + "；".join(parts), True)
        if len(distinct) == 1:
            return ("无冲突：已设外官的各层级同属 " + next(iter(distinct))
                    + " → " + "；".join(parts), False)
        return ("三级都没有外官，无可比 → " + "；".join(parts), False)
