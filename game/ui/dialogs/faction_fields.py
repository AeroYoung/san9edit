# -*- coding: utf-8 -*-
"""势力编辑弹窗的字段表 + 分组表（需求 §3.8）。

- 可落盘字段：name / color / prestige / stance + independent / overlord_id /
  vassal_value（需求 §3.1）。
- gold / food / troops 是派生值，只读（§8.3 第 44 条）。
- 「显示色」是运行时派生色（§3.4），只读展示，不落盘、不改 Faction.color。
- overlord_id 的选项与「显示色」随当前 World 现算 → 模块级常量给形状，
  运行期由 faction_fields(world, faction) 补齐（与 node_fields(world) 同构）。
"""

from game.core.faction_color import faction_display_color

from .field_spec import Field, FieldGroup


FACTION_FIELDS = (
    Field("id",       "编号",  "readonly"),
    Field("name",     "势力名", "str"),
    Field("color",    "颜色",  "color"),
    # 运行时派生色（只读）：附庸按宗主混色、董卓固定深棕
    Field("display_color", "显示色", "readonly"),
    Field("prestige", "威望",  "int", min=0),
    Field("stance",   "关系",  "int", min=-100, max=100),
    Field("gold",     "金钱",  "readonly"),
    Field("food",     "军粮",  "readonly"),
    Field("troops",   "兵力",  "readonly"),   # ★ 派生值（名下据点求和）
    Field("independent",  "独立",     "bool"),
    # options 由 faction_fields(world, faction) 运行期补：仅列独立势力
    Field("overlord_id",  "宗主势力", "choice", options=()),
    Field("vassal_value", "附庸值",   "int", min=1, max=99),
)

# 分组：(标题, 字段 key 元组, 组说明)。第一条的只读信息块由运行期补。
FACTION_SECTIONS = (
    ("基本情况",
     ("id",),
     "（只读；若要修改，请到对应编辑窗体中修改）"),
    ("可编辑信息",
     ("name", "color", "display_color", "prestige", "stance",
      "gold", "food", "troops"),
     "（金钱 / 军粮 / 兵力是派生值，只读）"),
    ("独立/附庸",
     ("independent", "overlord_id", "vassal_value"),
     "（独立时宗主与附庸值自动归零；附庸值越大越听从宗主）"),
)


def overlord_options(world, faction=None):
    """(value, label)：未选择 + 全部**独立**势力（排除自己）。"""
    options = [(None, "（未选择）")]
    if world is not None:
        for f in sorted(world.factions.values(), key=lambda f: f.name):
            if faction is not None and f.id == faction.id:
                continue
            if not getattr(f, "independent", True):
                continue
            options.append((f.id, f.name))
    return tuple(options)


def _display_color_fn(faction):
    """只读「显示色」的取值函数（签名同 Field.display_fn）。"""
    def _fn(_value, world):
        factions = getattr(world, "factions", None) or {}
        return faction_display_color(faction, factions)
    return _fn


def faction_fields(world=None, faction=None):
    """势力编辑字段表；宗主选项与显示色按当前 World / 势力现算。"""
    options = overlord_options(world, faction)
    return tuple(
        f._replace(options=options) if f.key == "overlord_id"
        else f._replace(display_fn=_display_color_fn(faction))
        if f.key == "display_color"
        else f
        for f in FACTION_FIELDS
    )


def faction_sections(fields, info=()):
    """字段表 → 分组（FieldGroup 元组）；只读信息块并入「基本情况」组。"""
    by_key = {f.key: f for f in fields}
    groups = []
    for index, (title, keys, desc) in enumerate(FACTION_SECTIONS):
        groups.append(FieldGroup(
            title=title,
            fields=tuple(by_key[k] for k in keys if k in by_key),
            desc=desc,
            info=tuple(info) if index == 0 else (),
        ))
    return tuple(groups)
