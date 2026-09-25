# -*- coding: utf-8 -*-
"""势力编辑的共用流程。

势力面板右键「编辑」与地图右键「编辑势力」共用这一套：
    弹窗 → 取变更 → 执行 Command。
调用方负责后续刷新（面板 / 地图）。
"""

import logging

logger = logging.getLogger(__name__)


def edit_faction(parent, world, faction, session, open_dialog):
    """打开势力编辑弹窗并执行编辑。

    参数与 edit_node 一致：
        parent      父窗口（面板或 root）
        world       World 实例
        faction     目标 Faction
        session     EditSession（None = 非编辑模式，直接返回）
        open_dialog 打开模态弹窗的回调，签名 open_dialog(dlg_factory) -> dlg

    返回 True 表示执行了编辑（调用方据此刷新）。
    """
    if session is None or world is None or faction is None:
        return False
    logger.debug("编辑势力：%s %s", faction.id, faction.name)

    from game.ui.dialogs.edit_dialog import EditDialog
    from game.ui.dialogs.faction_fields import FACTION_FIELDS
    from game.core.edit_commands import FactionEditCommand

    dlg = open_dialog(lambda: EditDialog(
        parent, FACTION_FIELDS, faction, world=world, title="编辑势力"))
    if dlg is None or not dlg.ok:
        return False

    new_values, old_values = dlg.get_changed()
    if not new_values:
        return False

    session.execute(FactionEditCommand(faction.id, old_values, new_values))
    return True