# -*- coding: utf-8 -*-
"""具体命令：据点编辑、势力编辑、人物编辑。

约定：old_values / new_values 都是 {field: value} dict，只含真正变化的字段。
"""

from game.core.edit_session import Command


class NodeEditCommand(Command):
    def __init__(self, node_id, old_values: dict, new_values: dict):
        self.node_id = node_id
        self.old_values = dict(old_values)
        self.new_values = dict(new_values)

    def do(self, world):
        n = world.nodes[self.node_id]
        for k, v in self.new_values.items():
            setattr(n, k, v)

    def undo(self, world):
        n = world.nodes[self.node_id]
        for k, v in self.old_values.items():
            setattr(n, k, v)

    def label(self):
        return f"编辑据点 {self.node_id}"


class FactionEditCommand(Command):
    """势力静态字段编辑。同构 NodeEditCommand，操作 world.factions。"""
    def __init__(self, faction_id, old_values: dict, new_values: dict):
        self.faction_id = faction_id
        self.old_values = dict(old_values)
        self.new_values = dict(new_values)

    def do(self, world):
        f = world.factions[self.faction_id]
        for k, v in self.new_values.items():
            setattr(f, k, v)

    def undo(self, world):
        f = world.factions[self.faction_id]
        for k, v in self.old_values.items():
            setattr(f, k, v)

    def label(self):
        return f"编辑势力 {self.faction_id}"


class CharacterEditCommand(Command):
    """人物字段编辑。同构 NodeEditCommand，操作 world.characters。

    当前用于「设为登场 / 设为未登场」开关（new_values = {"appeared": bool}），
    将来的完整人物编辑沿用同一个命令。
    """
    def __init__(self, character_id, old_values: dict, new_values: dict):
        self.character_id = character_id
        self.old_values = dict(old_values)
        self.new_values = dict(new_values)

    def do(self, world):
        c = world.characters[self.character_id]
        for k, v in self.new_values.items():
            setattr(c, k, v)

    def undo(self, world):
        c = world.characters[self.character_id]
        for k, v in self.old_values.items():
            setattr(c, k, v)

    def label(self):
        return f"编辑人物 {self.character_id}"


class FactionCreateCommand(Command):
    """新建势力：只负责容器 + 引用注入。

    级联（君主 faction / node / location、都城 owner）由调用方包进
    CompositeCommand —— 这里只管势力本身，undo 就是把它摘掉。
    """
    def __init__(self, faction_id, values: dict):
        self.faction_id = faction_id
        self.values = dict(values)

    def do(self, world):
        from game.core.faction import Faction
        world.add_faction(Faction.from_dict(self.faction_id, self.values))

    def undo(self, world):
        world.remove_faction(self.faction_id)

    def label(self):
        return f"新建势力 {self.faction_id}"


class FactionDeleteCommand(Command):
    """删除势力：摘容器 + 清 player_faction_id（都还原得回来）。

    级联（据点改无主、人物下野、外官摘除）由调用方包进 CompositeCommand。
    """
    def __init__(self, faction_id):
        self.faction_id = faction_id
        self._values = None             # do 时抓，供 undo 复原
        self._player_faction_id = None

    def do(self, world):
        faction = world.factions.get(self.faction_id)
        self._values = faction.to_dict() if faction is not None else None
        self._player_faction_id = world.player_faction_id
        world.remove_faction(self.faction_id)
        if world.player_faction_id == self.faction_id:
            world.player_faction_id = None

    def undo(self, world):
        from game.core.faction import Faction
        if self._values is not None:
            world.add_faction(Faction.from_dict(self.faction_id, self._values))
        world.player_faction_id = self._player_faction_id

    def label(self):
        return f"删除势力 {self.faction_id}"


class OfficialSetCommand(Command):
    """设置 / 替换某行政区的外官（一区一官：new 覆盖 old）。

    old_item 为 None 表示该区原本没有外官（undo 时删掉即可）。
    """
    def __init__(self, region_id, old_item, new_item):
        self.region_id = region_id
        self.old_item = dict(old_item) if old_item else None
        self.new_item = dict(new_item)

    def do(self, world):
        world.officials[self.region_id] = dict(self.new_item)

    def undo(self, world):
        if self.old_item is None:
            world.officials.pop(self.region_id, None)
        else:
            world.officials[self.region_id] = dict(self.old_item)

    def label(self):
        return f"设置外官 {self.region_id}"


class OfficialRemoveCommand(Command):
    """删除某行政区的外官。"""
    def __init__(self, region_id, old_item):
        self.region_id = region_id
        self.old_item = dict(old_item)

    def do(self, world):
        world.officials.pop(self.region_id, None)

    def undo(self, world):
        world.officials[self.region_id] = dict(self.old_item)

    def label(self):
        return f"删除外官 {self.region_id}"


def build_vassal_commands(world, faction, old_values: dict, new_values: dict):
    """势力编辑 → 独立/附庸联动的命令列表（需求 §3.9）。

    自身那条永远在首位；随后按「独立 → 附庸」补级联：

        独立 → 附庸（宗主 = B）：该势力原有附庸的 overlord_id 全部改为 B，
                                各附庸的 vassal_value 不变。
        附庸 → 独立：只改自身（overlord_id=None / vassal_value=0 由弹窗给出），
                    原有附庸不自动处理。

    返回的列表由调用方包 CompositeCommand（1 条时可直接 execute）。
    """
    cmds = [FactionEditCommand(faction.id, old_values, new_values)]

    new_independent = new_values.get("independent", faction.independent)
    new_overlord = new_values.get("overlord_id", faction.overlord_id)
    if new_independent is False and new_overlord:
        followers = [f for f in world.factions.values()
                     if f.id != faction.id
                     and not getattr(f, "independent", True)
                     and f.overlord_id == faction.id]
        for follower in sorted(followers, key=lambda f: f.id):
            cmds.append(FactionEditCommand(
                follower.id,
                {"overlord_id": follower.overlord_id},
                {"overlord_id": new_overlord},
            ))
    return cmds


# TODO(phase2): NodeEditCommand 的 owner 级联（现由 CompositeCommand 组合）
