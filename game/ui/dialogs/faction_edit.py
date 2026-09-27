# -*- coding: utf-8 -*-
"""势力编辑 / 势力情报的共用流程（同一个窗）。

弹窗内的可点链接（[[c:...]] 人物 / [[f:...]] 势力 / [[n:...]] 据点）
由 _make_link_handler 处理；点击时临时释放本弹窗 grab，开新窗，关闭后抢回。
"""

import logging
import tkinter as tk

logger = logging.getLogger(__name__)


def faction_info_sections(world, faction):
    """势力情报的只读信息块：(标题, 文本) 列表。"""
    fid = faction.id
    ruler = world.character(fid)
    if ruler is not None:
        ruler_text = ("[[c:%s|%s]]（%s）"
                      % (ruler.id, ruler.display_name(), ruler.id))
        ruler_text += ("　所属：%s　所在：%s"
                       % (world.node(ruler.node).name
                          if world.node(ruler.node) else "—",
                          world.node(ruler.location).name
                          if world.node(ruler.location) else "—"))
    else:
        ruler_text = "（人物不在剧本中）"

    nodes = [n for n in world.nodes.values() if n.owner == fid]
    node_text = "、".join("[[n:%s|%s]]（%s）" % (n.id, n.name, n.id)
                          for n in sorted(nodes, key=lambda n: n.id)[:12])
    if len(nodes) > 12:
        node_text += " 等 %d 个" % len(nodes)

    chars = [c for c in world.characters.values() if c.faction == fid]
    char_text = "、".join("[[c:%s|%s]]" % (c.id, c.name)
                          for c in sorted(chars, key=lambda c: c.id)[:12])
    if len(chars) > 12:
        char_text += " 等 %d 人" % len(chars)

    officials = []
    for c in chars:
        for item in world.officials_of_character(c.id):
            officials.append("%s-[[c:%s|%s]]（%s）"
                             % (item['name'], c.id, c.name,
                                item['region_id']))
    return [
        ("君主", ruler_text),
        ("据点（%d）" % len(nodes), node_text or "（无）"),
        ("人物（%d）" % len(chars), char_text or "（无）"),
        ("本势力人物的外官（%d）" % len(officials),
         "、".join(officials) or "（无）"),
    ]


def _make_link_handler(parent, world):
    root = parent.winfo_toplevel()      # ★ 主窗口

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
            edit_faction(root, world, f, None, _open_and_wait)
        elif kind == "n":
            n = world.nodes.get(entity_id)
            if n is None:
                return
            from game.ui.dialogs.node_edit import edit_node
            edit_node(root, world, n, None, _open_and_wait)
    return _handler

def edit_faction(parent, world, faction, session, open_dialog):
    """打开势力编辑 / 势力情报弹窗。"""
    if world is None or faction is None:
        return False
    readonly = session is None
    logger.debug("%s势力：%s %s", "查看" if readonly else "编辑",
                 faction.id, faction.name)

    from tkinter import messagebox

    from game.ui.dialogs.edit_dialog import EditDialog
    from game.ui.dialogs.faction_fields import faction_fields, faction_sections
    from game.core.edit_commands import build_vassal_commands
    from game.core.edit_session import CompositeCommand
    from game.ui.portrait import portrait_path

    ruler = world.character(faction.id)
    portrait = (portrait_path(ruler.id, ruler.name)
                if ruler is not None else None)
    if ruler is not None:
        node = world.node(ruler.node)
        loc = world.node(ruler.location)
        node_name = node.name if node is not None else "—"
        loc_name = loc.name if loc is not None else "—"
        caption = (f"{ruler.display_name()}（{ruler.id}）\n"
                   f"所属：{node_name}；所在：{loc_name}")
    else:
        caption = "（君主不在剧本中）"

    info = [it for it in faction_info_sections(world, faction)
            if it[0] != "君主"]
    fields = faction_fields(world, faction)
    sections = faction_sections(fields, info=info,
                                side_image=portrait, side_caption=caption)

    title = "势力情报" if readonly else "编辑势力"
    dlg = open_dialog(lambda: EditDialog(
        parent, fields, faction, world=world, title=title,
        readonly=readonly, sections=sections, scroll=True,
        on_change=None if readonly else _make_linkage(fields),
        on_link_click=_make_link_handler(parent, world)))
    if dlg is None or readonly or not dlg.ok:
        return False

    new_values, old_values = dlg.get_changed()
    if not new_values:
        return False

    final_independent = new_values.get("independent", faction.independent)
    final_overlord = new_values.get("overlord_id", faction.overlord_id)
    if final_independent is False and not final_overlord:
        messagebox.showwarning(
            "独立/附庸",
            "附庸势力必须选择一个宗主势力（只能是独立势力）。",
            parent=parent)
        logger.warning("势力 %s 设为附庸但未选宗主，已取消编辑", faction.id)
        return False

    cmds = build_vassal_commands(world, faction, old_values, new_values)
    session.execute(cmds[0] if len(cmds) == 1
                    else CompositeCommand(cmds, "编辑势力"))
    return True


# ============================================================
# 独立 / 附庸联动
# ============================================================
DEFAULT_VASSAL_VALUE = 50


def _make_linkage(fields):
    """构造 on_change 联动回调：勾掉「独立」才允许填宗主与附庸值。"""
    candidates = []
    for f in fields:
        if f.key == "overlord_id":
            candidates = [v for v, _label in f.options if v]
            break

    def _on_change(key, value, dlg):
        if key != "independent":
            return
        if bool(value):
            dlg.set_field_value("overlord_id", None)
            dlg.set_field_value("vassal_value", "0")
            dlg.set_field_enabled("overlord_id", False)
            dlg.set_field_enabled("vassal_value", False)
            return
        dlg.set_field_enabled("overlord_id", True)
        dlg.set_field_enabled("vassal_value", True)
        if dlg.field_value("overlord_id") in (None, ""):
            if candidates:
                dlg.set_field_value("overlord_id", candidates[0])
        if str(dlg.field_value("vassal_value") or "").strip() in ("", "0"):
            dlg.set_field_value("vassal_value", str(DEFAULT_VASSAL_VALUE))

    return _on_change