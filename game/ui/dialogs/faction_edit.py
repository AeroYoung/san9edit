# -*- coding: utf-8 -*-
"""势力编辑 / 势力情报的共用流程（同一个窗）。

势力面板右键「编辑势力」与地图右键「编辑势力」共用这一套：
    弹窗（信息块 + 可编辑字段）→ 取变更 → 执行 Command。
非编辑模式（session 为 None）传 readonly：同一个窗只读展示 —— 即「势力情报」，
信息块含君主 / 据点 / 人物 / 外官（见 faction_info_sections）。
调用方负责后续刷新（面板 / 地图）。
"""

import logging

logger = logging.getLogger(__name__)


def faction_info_sections(world, faction):
    """势力情报的只读信息块：(标题, 文本) 列表。"""
    fid = faction.id
    ruler = world.character(fid)
    ruler_text = (f"{ruler.display_name()}（{ruler.id}）" if ruler is not None
                  else "（人物不在剧本中）")
    if ruler is not None:
        ruler_text += ("　所属：%s　所在：%s"
                       % (world.node(ruler.node).name if world.node(ruler.node)
                          else "—",
                          world.node(ruler.location).name
                          if world.node(ruler.location) else "—"))

    nodes = [n for n in world.nodes.values() if n.owner == fid]
    node_text = "、".join(f"{n.name}（{n.id}）" for n in
                          sorted(nodes, key=lambda n: n.id)[:12])
    if len(nodes) > 12:
        node_text += " 等 %d 个" % len(nodes)

    chars = [c for c in world.characters.values() if c.faction == fid]
    char_text = "、".join(c.name for c in sorted(chars,
                                                 key=lambda c: c.id)[:12])
    if len(chars) > 12:
        char_text += " 等 %d 人" % len(chars)

    officials = []
    for c in chars:
        for item in world.officials_of_character(c.id):
            officials.append(f"{item['name']}-{c.name}（{item['region_id']}）")
    return [
        ("君主", ruler_text),
        ("据点（%d）" % len(nodes), node_text or "（无）"),
        ("人物（%d）" % len(chars), char_text or "（无）"),
        ("本势力人物的外官（%d）" % len(officials),
         "、".join(officials) or "（无）"),
    ]


def edit_faction(parent, world, faction, session, open_dialog):
    """打开势力编辑 / 势力情报弹窗。

    参数与 edit_node 一致：
        parent      父窗口（面板或 root）
        world       World 实例
        faction     目标 Faction
        session     EditSession（None = 非编辑模式 → 只读展示）
        open_dialog 打开模态弹窗的回调，签名 open_dialog(dlg_factory) -> dlg

    返回 True 表示执行了编辑（调用方据此刷新）。
    """
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

    # 右下角放君主头像（找不到图 → 弹窗自己降级显示占位）
    ruler = world.character(faction.id)
    portrait = (portrait_path(ruler.id, ruler.name)
                if ruler is not None else None)
    caption = (ruler.display_name() if ruler is not None
               else "（君主不在剧本中）")

    info = faction_info_sections(world, faction)
    fields = faction_fields(world, faction)
    sections = faction_sections(fields, info=info)

    title = "势力情报" if readonly else "编辑势力"
    dlg = open_dialog(lambda: EditDialog(
        parent, fields, faction, world=world, title=title,
        readonly=readonly, sections=sections, scroll=True,
        side_image=portrait, side_caption=caption,
        on_change=None if readonly else _make_linkage(fields)))
    if dlg is None or readonly or not dlg.ok:
        return False

    new_values, old_values = dlg.get_changed()
    if not new_values:
        return False

    # 附庸必须有宗主（需求 §3.3：没有宗主的附庸会在下次加载时被判为损坏）
    final_independent = new_values.get("independent", faction.independent)
    final_overlord = new_values.get("overlord_id", faction.overlord_id)
    if final_independent is False and not final_overlord:
        messagebox.showwarning(
            "独立/附庸",
            "附庸势力必须选择一个宗主势力（只能是独立势力）。",
            parent=parent)
        logger.warning("势力 %s 设为附庸但未选宗主，已取消编辑", faction.id)
        return False

    # 独立 → 附庸的级联（原有附庸改指新宗主）由 build_vassal_commands 给出
    cmds = build_vassal_commands(world, faction, old_values, new_values)
    session.execute(cmds[0] if len(cmds) == 1
                    else CompositeCommand(cmds, "编辑势力"))
    return True


# ============================================================
# 独立 / 附庸联动（需求 §3.9）
# ============================================================
DEFAULT_VASSAL_VALUE = 50       # 切到附庸且原值为 0 时的默认附庸值（§3.2）


def _make_linkage(fields):
    """构造 on_change 联动回调：勾掉「独立」才允许填宗主与附庸值。

    - 独立：宗主归 None、附庸值归 0，两个控件禁用（数据层保持一致的写法）
    - 附庸：两个控件启用；宗主为空时预选第一个独立势力，附庸值为 0 时填默认值
    """
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
