# -*- coding: utf-8 -*-
"""据点编辑的共用流程。

面板右键「编辑」与地图右键「编辑据点」共用这一套：
    弹窗 → 取变更 → 郡治互斥 → 执行 Command。
调用方负责后续刷新（面板 / 地图）。
"""


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
    if session is None or world is None or node is None:
        return False

    from tkinter import messagebox

    from game.ui.dialogs.edit_dialog import EditDialog
    from game.ui.dialogs.node_fields import NODE_FIELDS
    from game.core.edit_commands import NodeEditCommand
    from game.core.edit_session import CompositeCommand

    dlg = open_dialog(lambda: EditDialog(
        parent, NODE_FIELDS, node, world=world, title="编辑据点"))
    if dlg is None or not dlg.ok:
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
            ans = messagebox.askyesno(
                "郡治冲突",
                f"{other.name} 已是本郡郡治。\n"
                f"确定将其改为非郡治，本县设为郡治？",
                parent=parent,
            )
            if not ans:
                return False
            cmds.append(NodeEditCommand(
                other.id, {"is_capital": True}, {"is_capital": False}))
            break

    cmds.append(NodeEditCommand(node.id, old_values, new_values))
    cmd = cmds[0] if len(cmds) == 1 else CompositeCommand(cmds, "设置郡治")
    session.execute(cmd)
    return True
