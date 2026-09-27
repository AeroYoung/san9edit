# -*- coding: utf-8 -*-
"""势力。

约定：势力 id 即君主的人物 id（四位数字字符串）。

stance：该势力相对【玩家】的关系值，范围 -100 ~ 100。
    <  0  → 敌对
    > 80  → 盟友
    其余  → 中立
玩家自身的 stance 无意义（永远归在"玩家"组）。

gold / food / troops 为派生值（§6.1）：名下据点求和，不落盘、不可赋值。

独立 / 附庸（需求 §3.1）：
    independent   True = 独立势力；False = 附庸势力
    overlord_id   宗主势力 id；独立势力恒为 None
    vassal_value  附庸值 1–99（越大越听从宗主）；独立势力恒为 0
三者都是**可落盘字段**，to_dict 对所有势力都写、from_dict 容错。
派生显示色见 core/faction_color.py（不写回 color）。
"""

VASSAL_VALUE_MIN = 1
VASSAL_VALUE_MAX = 99


class Faction:
    def __init__(self, fid, name, color="#888888",
                 prestige=0, stance=0,
                 independent=True, overlord_id=None, vassal_value=0):
        self.id = fid                # = 君主人物 id
        self.name = name
        self.color = color
        self.prestige = int(prestige)
        self.stance = int(stance)
        self.independent = bool(independent)
        self.overlord_id = overlord_id or None
        self.vassal_value = int(vassal_value or 0)
        self._nodes_ref = None       # ★ World 注入（world.nodes dict 引用）

    @property
    def ruler_id(self):
        return self.id

    @property
    def gold(self):
        """名下据点金钱求和。无主据点不计。"""
        if self._nodes_ref is None:
            return 0
        return sum(n.gold for n in self._nodes_ref.values()
                   if n.owner == self.id)

    @property
    def food(self):
        """名下据点军粮求和。"""
        if self._nodes_ref is None:
            return 0
        return sum(n.food for n in self._nodes_ref.values()
                   if n.owner == self.id)

    @property
    def troops(self):
        """名下据点兵力求和 + 所属部队兵力求和。

        部队项本轮恒为 0（Troop 模型未建，见 §8.4 / TODO(phase2)）。
        """
        total = 0
        if self._nodes_ref is not None:
            total += sum(n.troops for n in self._nodes_ref.values()
                         if n.owner == self.id)
        # TODO(phase2): Troop 模型落地后，在此追加 self._troops_ref 求和：
        #     if self._troops_ref is not None:
        #         total += sum(t.troops for t in self._troops_ref.values()
        #                      if t.faction_id == self.id)
        return total

    @classmethod
    def from_dict(cls, fid, d):
        """从剧本 dict 构造。不再读 gold / food。

        三个附庸字段容错（需求 §3.1 / §4）：
            independent   缺省 True（老剧本 = 独立）
            overlord_id   缺省 None
            vassal_value  独立强制 0；附庸 clamp 到 1–99（0 → 1，≥100 → 99）
        """
        independent = bool(d.get("independent", True))
        overlord_id = d.get("overlord_id") or None
        try:
            raw_value = int(d.get("vassal_value", 0) or 0)
        except (TypeError, ValueError):
            raw_value = 0
        if independent:
            vassal_value = 0
        else:
            vassal_value = max(VASSAL_VALUE_MIN,
                               min(VASSAL_VALUE_MAX, raw_value))
        return cls(
            fid=fid,
            name=d.get("name", fid),
            color=d.get("color", "#888888"),
            prestige=d.get("prestige", 0),
            stance=d.get("stance", 0),
            independent=independent,
            overlord_id=overlord_id,
            vassal_value=vassal_value,
        )

    def to_dict(self):
        """序列化。不写 gold / food（派生值）；三个附庸字段全写。"""
        return {
            "name": self.name,
            "color": self.color,
            "prestige": self.prestige,
            "stance": self.stance,
            "independent": bool(self.independent),
            "overlord_id": self.overlord_id,
            "vassal_value": int(self.vassal_value),
        }

    def stance_label(self):
        """返回相对玩家的关系标签。"""
        if self.stance < 0:
            return "敌对"
        if self.stance > 80:
            return "盟友"
        return "中立"

    def vassal_label(self, overlord_name=None):
        """「独立 / 附庸」列文本：独立势力 →「独立」，附庸 → 宗主势力名。"""
        if self.independent or not self.overlord_id:
            return "独立"
        return overlord_name or self.overlord_id

    def __repr__(self):
        return f"<Faction {self.id} {self.name} stance={self.stance}>"
