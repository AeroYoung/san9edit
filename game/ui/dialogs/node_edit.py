# -*- coding: utf-8 -*-
"""据点编辑 / 据点情报的共用流程（同一个窗）。

面板右键「编辑据点」与地图右键「编辑据点」共用这一套：
    弹窗（信息块 + 可编辑字段）→ 取变更 → 郡治互斥 → 执行 Command。
非编辑模式（session 为 None）传 readonly：同一个窗只读展示 —— 即原来的「据点情报」，
信息块含外官 / 州郡 / 实际控制 / 宣称权冲突（见 node_info_sections）。

owner 已可编辑（choice：无主 + 势力列表）；改 owner 只动 Node.owner，
级联人物归属走据点面板的「批量修改所属」（node_owner.py）。
调用方负责后续刷新（面板 / 地图）。
"""

import logging

logger = logging.getLogger(__name__)


def node_info_sections(world, node):
    """据点情报的只读信息块：(标题, 文本) 列表。

    内容与原「据点情报」窗口一致：据点基本情况 / 县外官 / 所属州郡 /
    州郡外官的实际控制 / 本郡其它据点 / 宣称权冲突（三级判定）。
    """
    return [
        ("据点", _summary(world, node)),
        ("外官（县）", _official_label(world, node.id) or "（无）"),
        ("所属州郡", "\n".join(_region_lines(world, node))),
        ("州郡外官的实际控制", "\n".join(_control_lines(world, node))),
        ("本郡其它据点（%s）" % world.county_name(node.county_id),
         "\n".join(_other_holder_lines(world, node))),
        ("宣称权冲突", _claim_line(world, node)),
    ]


def _official_label(world, region_id):
    """「官名-姓名」；无外官 → None。"""
    return world.official_label(region_id) or None


def _faction_of_official(world, item):
    """外官的势力 id（君主即 faction == id；无势力 → 人物 id）。"""
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
        owner = f.name if f is not None else "无主（脏数据）"
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
        label = world.official_label(rid)
        lines.append(f"{name}：{region}（{rid}）" +
                     (f" · 外官 {label}" if label else " · 外官（无）"))
    return lines


def _control_lines(world, node):
    lines = []
    for name, rid in (("州", node.state_id), ("郡", node.county_id)):
        item = world.official_of(rid)
        if not item:
            lines.append(f"{name}外官：（无）")
            continue
        fid = _faction_of_official(world, item)
        label = world.official_label(rid)
        if fid is None:
            lines.append(f"{label}：人物不在剧本中")
            continue
        in_state = [n for n in world.nodes.values()
                    if n.owner == fid and n.id[:2] == node.state_id[:2]]
        total = [n for n in world.nodes.values() if n.owner == fid]
        f = world.faction(fid)
        lines.append(f"{label}（势力 {f.name if f is not None else '—'}）："
                     f"本州 {len(in_state)} 个据点 / 全部 {len(total)} 个据点")
    return lines


def _other_holder_lines(world, node):
    """本郡里不被「郡外官（无则州外官）」控制的据点，实际在谁手里。"""
    county_id = node.county_id
    ref = (world.official_of(county_id) or world.official_of(node.state_id))
    ref_fid = _faction_of_official(world, ref)

    buckets = {}
    for n in world.nodes.values():
        if n.id[:4] != county_id or n.owner == ref_fid:
            continue
        if n.owner and world.faction(n.owner) is not None:
            key = world.faction(n.owner).name
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
        shown = "、".join(names[:3])
        more = f" 等 {len(names)} 个" if len(names) > 3 else ""
        lines.append(f"{key}：{len(names)} 个 —— {shown}{more}")
    return lines


def _claim_line(world, node):
    """宣称权冲突分级（需求 §3.5）：无 / 小 / 大。"""
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
            level = 0                      # 在实控范围内
        elif fid in county_owners:
            level = 1                      # 小冲突
        else:
            level = 2                      # 大冲突
        rows.append((name, world.official_label(rid), level))

    levels = [lv for _n, _label, lv in rows if lv is not None]
    worst = max(levels) if levels else 0
    verdict = {0: "无冲突", 1: "宣称权小冲突", 2: "宣称权大冲突"}[worst]
    tag = {0: "在实控范围内", 1: "小冲突", 2: "大冲突"}
    parts = [f"{n}外官 {label}（{tag[lv]}）" if lv is not None
             else f"{n}外官（无）" for n, label, lv in rows]
    return f"{verdict} → " + "；".join(parts)


def edit_node(parent, world, node, session, open_dialog):
    """打开据点编辑弹窗并执行编辑。

    参数：
        parent      父窗口（面板或 root）
        world       World 实例
        node        目标 Node
        session     EditSession（None = 非编辑模式，直接返回）
        open_dialog 打开模态弹窗的回调，签名 open_dialog(dlg_factory) -> dlg

    返回 True 表示执行了编辑（调用方据此刷新）。
    """
    if world is None or node is None:
        return False
    readonly = session is None          # 非编辑模式 → 同一个窗只读（原名「据点情报」）
    logger.debug("%s据点：%s %s", "查看" if readonly else "编辑", node.id, node.name)

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
        readonly=readonly, sections=sections, scroll=True))
    if dlg is None or readonly or not dlg.ok:
        return False

    new_values, old_values = dlg.get_changed()
    if not new_values:
        return False

    # 郡治互斥（§3.3 场景 2）：同郡已有郡治 → 弹窗二选一
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
