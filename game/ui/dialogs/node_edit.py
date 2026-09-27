# -*- coding: utf-8 -*-
"""据点编辑 / 据点情报的共用流程（同一个窗）。

弹窗内的可点链接（[[c:...]] 人物 / [[f:...]] 势力 / [[n:...]] 据点）
由 _make_link_handler 处理；点击时临时释放本弹窗 grab，开新窗，关闭后抢回。
"""

import logging
import tkinter as tk

logger = logging.getLogger(__name__)


def _official_link(world, region_id):
    """外官 → '官名-[[c:id|姓名]]' 或 None。"""
    item = world.official_of(region_id)
    if not item:
        return None
    cid = item.get("character_id")
    ch = world.character(cid) if cid else None
    label = item.get("name", "")
    if ch is None:
        return label
    if ch.name and ch.name in label:
        return label.replace(ch.name, "[[c:%s|%s]]" % (ch.id, ch.name), 1)
    return "%s [[c:%s|%s]]" % (label, ch.id, ch.name)


def node_info_sections(world, node):
    """据点情报的只读信息块：(标题, 文本) 列表。"""
    return [
        ("据点", _summary(world, node)),
        ("外官（县）", _official_link(world, node.id) or "（无）"),
        ("所属州郡", "\n".join(_region_lines(world, node))),
        ("州郡外官的实际控制", "\n".join(_control_lines(world, node))),
        ("本郡其它据点（%s）" % world.county_name(node.county_id),
         "\n".join(_other_holder_lines(world, node))),
        ("宣称权冲突", _claim_line(world, node)),
    ]


def _faction_of_official(world, item):
    if not item:
        return None
    ch = world.character(item.get("character_id"))
    if ch is None:
        return None
    return ch.faction or ch.id


def _summary(world, node):
    owner = "无主"
    if node.owner:
        f = world.faction(node.owner)
        owner = "[[f:%s|%s]]" % (f.id, f.name) if f is not None \
            else "无主（脏数据）"
    kind = "郡治" if node.is_capital else node.type
    persons = len([c for c in world.characters.values()
                   if c.node == node.id and c.appeared])
    return ("%s · %s · %s（%s） · 等级 %d · %s\n"
            "编号 %s · 势力 %s · 登场人物 %d · 驻军 %s"
            % (world.state_name(node.state_id),
               world.county_name(node.county_id), node.name, node.id,
               node.level, kind, node.id, owner, persons,
               f"{node.troops:,}"))


def _region_lines(world, node):
    lines = []
    for name, rid in (("州", node.state_id), ("郡", node.county_id)):
        region = (world.state_name(rid) if name == "州"
                  else world.county_name(rid))
        link = _official_link(world, rid)
        lines.append(f"{name}：{region}（{rid}）" +
                     (f" · 外官 {link}" if link else " · 外官（无）"))
    return lines


def _control_lines(world, node):
    lines = []
    for name, rid in (("州", node.state_id), ("郡", node.county_id)):
        item = world.official_of(rid)
        if not item:
            lines.append(f"{name}外官：（无）")
            continue
        fid = _faction_of_official(world, item)
        label = _official_link(world, rid) or world.official_label(rid)
        if fid is None:
            lines.append(f"{label}：人物不在剧本中")
            continue
        in_state = [n for n in world.nodes.values()
                    if n.owner == fid and n.id[:2] == node.state_id[:2]]
        total = [n for n in world.nodes.values() if n.owner == fid]
        f = world.faction(fid)
        f_display = "[[f:%s|%s]]" % (f.id, f.name) if f is not None else "—"
        lines.append(f"{label}（势力 {f_display}）："
                     f"本州 {len(in_state)} 个据点 / 全部 {len(total)} 个据点")
    return lines


def _other_holder_lines(world, node):
    county_id = node.county_id
    ref = (world.official_of(county_id) or world.official_of(node.state_id))
    ref_fid = _faction_of_official(world, ref)

    buckets = {}   # (显示文本, 排序key) → [据点名, ...]
    for n in world.nodes.values():
        if n.id[:4] != county_id or n.owner == ref_fid:
            continue
        if n.owner:
            f = world.faction(n.owner)
            if f is not None:
                key = "[[f:%s|%s]]" % (f.id, f.name)
                sort_key = f.name
            else:
                key = f"脏数据（{n.owner}）"
                sort_key = "~脏数据"
        else:
            key = "无主"
            sort_key = "~无主"
        buckets.setdefault((key, sort_key), []).append(n.name)

    if not buckets:
        return ["（本郡据点在上述外官治下）"]
    lines = []
    for pair in sorted(buckets,
                       key=lambda k: (-len(buckets[k]), k[1])):
        names = buckets[pair]
        shown = "、".join(names[:3])
        more = f" 等 {len(names)} 个" if len(names) > 3 else ""
        lines.append(f"{pair[0]}：{len(names)} 个 —— {shown}{more}")
    return lines


def _claim_line(world, node):
    owner = node.owner if (node.owner and world.faction(node.owner)) else None
    county_owners = {n.owner for n in world.nodes.values()
                     if n.id[:4] == node.county_id and n.owner}

    rows = []
    for name, rid in (("县", node.id), ("郡", node.county_id),
                      ("州", node.state_id)):
        item = world.official_of(rid)
        if not item:
            rows.append((name, None, None))
            continue
        fid = _faction_of_official(world, item)
        if fid == owner:
            level = 0
        elif fid in county_owners:
            level = 1
        else:
            level = 2
        rows.append((name, _official_link(world, rid), level))

    levels = [lv for _n, _label, lv in rows if lv is not None]
    worst = max(levels) if levels else 0
    verdict = {0: "无冲突", 1: "宣称权小冲突", 2: "宣称权大冲突"}[worst]
    tag = {0: "在实控范围内", 1: "小冲突", 2: "大冲突"}
    parts = [f"{n}外官 {label}（{tag[lv]}）" if lv is not None
             else f"{n}外官（无）" for n, label, lv in rows]
    return f"{verdict} → " + "；".join(parts)


# ============================================================
# 链接点击：临时释放外层 grab → 开新窗 → 抢回 grab
# ============================================================
def _make_link_handler(parent, world):
    root = parent.winfo_toplevel()      # ★ 主窗口，而不是外层弹窗 / panel

    def _open_and_wait(fac):
        dlg = fac()
        try:
            root.wait_window(dlg)
        except tk.TclError:
            pass
        return dlg

    def _handler(kind, entity_id):
        if kind == "c":
            ch = world.characters.get(entity_id)
            if ch is None:
                return
            from game.ui.character_info_window import CharacterInfoWindow
            win = CharacterInfoWindow(root, ch, world=world, session=None)
            try:
                root.wait_window(win)
            except tk.TclError:
                pass
        elif kind == "f":
            f = world.factions.get(entity_id)
            if f is None:
                return
            from game.ui.dialogs.faction_edit import edit_faction
            edit_faction(root, world, f, None, _open_and_wait)
        elif kind == "n":
            n = world.nodes.get(entity_id)
            if n is None:
                return
            edit_node(root, world, n, None, _open_and_wait)
    return _handler

def edit_node(parent, world, node, session, open_dialog):
    """打开据点编辑弹窗并执行编辑。"""
    if world is None or node is None:
        return False
    readonly = session is None
    logger.debug("%s据点：%s %s", "查看" if readonly else "编辑",
                 node.id, node.name)

    from tkinter import messagebox

    from game.ui.dialogs.edit_dialog import EditDialog
    from game.ui.dialogs.node_fields import node_fields, node_sections
    from game.core.edit_commands import NodeEditCommand
    from game.core.edit_session import CompositeCommand

    fields = node_fields(world)
    sections = node_sections(fields, info=node_info_sections(world, node))
    title = "据点情报" if readonly else "编辑据点"
    dlg = open_dialog(lambda: EditDialog(
        parent, fields, node, world=world, title=title,
        readonly=readonly, sections=sections, scroll=True,
        on_link_click=_make_link_handler(parent, world)))
    if dlg is None or readonly or not dlg.ok:
        return False

    new_values, old_values = dlg.get_changed()
    if not new_values:
        return False

    cmds = []
    if new_values.get("is_capital") is True:
        for other in world.nodes.values():
            if other.id == node.id or other.county_id != node.county_id:
                continue
            if not other.is_capital:
                continue
            logger.info("郡治互斥：%s(%s) → 非郡治，本县 %s 设为郡治",
                        other.name, other.id, node.name)
            ans = messagebox.askyesno(
                "郡治冲突",
                f"{other.name} 已是本郡郡治。\n"
                f"确定将其改为非郡治，本县设为郡治？",
                parent=parent,
            )
            if not ans:
                logger.info("用户放弃郡治互斥，整体取消编辑")
                return False
            cmds.append(NodeEditCommand(
                other.id, {"is_capital": True}, {"is_capital": False}))
            break

    cmds.append(NodeEditCommand(node.id, old_values, new_values))
    cmd = cmds[0] if len(cmds) == 1 else CompositeCommand(cmds, "设置郡治")
    session.execute(cmd)
    return True