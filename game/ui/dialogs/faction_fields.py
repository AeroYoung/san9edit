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


def _basic_section(fields, info, side_image, side_caption):
    """基本情况：左栏 = 头像 + 君主信息；右栏 = 据点 / 人物 / 外官 / 编号。"""
    by_key = {f.key: f for f in fields}
    return FieldGroup(
        title="基本情况",
        fields=(by_key["id"],) if "id" in by_key else (),
        info=tuple(info),
        layout="two_cols",
        left_keys=(),                    # 左栏不放字段
        left_info_titles=("君主",),      # 只有「君主」info 进左栏
        side_image=side_image,
        side_caption=side_caption,
    )


def _editable_section(fields):
    """可编辑信息：左栏 4 项，右栏 4 项。"""
    keys = ("name", "color", "display_color",
            "prestige", "stance", "gold", "food", "troops")
    by_key = {f.key: f for f in fields}
    return FieldGroup(
        title="可编辑信息",
        fields=tuple(by_key[k] for k in keys if k in by_key),
        desc="（金钱 / 军粮 / 兵力是派生值，只读）",
        layout="two_cols",
        left_keys=("name", "color", "display_color", "prestige"),
    )


def _vassal_section(fields):
    """独立/附庸：三个控件排成一行。"""
    keys = ("independent", "overlord_id", "vassal_value")
    by_key = {f.key: f for f in fields}
    return FieldGroup(
        title="独立/附庸",
        fields=tuple(by_key[k] for k in keys if k in by_key),
        desc="（独立时宗主与附庸值自动归零；附庸值越大越听从宗主）",
        layout="inline",
    )


def faction_sections(fields, info=(), side_image=None, side_caption=None):
    """字段表 → 分组（FieldGroup 元组）。头像嵌入「基本情况」组左栏。"""
    return (
        _basic_section(fields, info, side_image, side_caption),
        _editable_section(fields),
        _vassal_section(fields),
    )