# -*- coding: utf-8 -*-
"""据点编辑弹窗的字段表。

owner 是 `choice`：选项（势力列表 + 无主）在运行期由 `node_fields(world)` 填，
因为势力是可变数据，不能写成模块级常量。
"""

from .field_spec import Field, FieldGroup


NODE_FIELDS = (
    Field("id",         "编号", "readonly"),
    Field("name",       "县名", "readonly"),
    Field("coords",     "坐标", "readonly",
          display_fn=lambda v, w: f"({v[0]:.2f}, {v[1]:.2f})" if v else "—"),
    # options 由 node_fields(world) 运行期补：无主 + 各势力
    Field("owner",      "势力", "choice", options=()),
    Field("type",       "类型", "choice",
          options=(("城", "城"), ("关隘", "关隘"), ("渡口", "渡口"))),
    Field("level",      "规模", "int", min=1, max=10),
    Field("is_capital", "郡治", "bool"),
    Field("troops",     "兵力", "int", min=0),
    Field("gold",       "金钱", "int", min=0),
    Field("food",       "军粮", "int", min=0),
)


def owner_options(world):
    """(value, label)：无主 + 全部势力（按名排序）。"""
    options = [(None, "无主")]
    if world is not None:
        options += [(f.id, f.name) for f in
                    sorted(world.factions.values(), key=lambda f: f.name)]
    return tuple(options)


def node_fields(world=None):
    """据点编辑字段表；owner 的选项按当前 World 现算。"""
    options = owner_options(world)
    return tuple(
        Field("owner", "势力", "choice", options=options)
        if f.key == "owner" else f
        for f in NODE_FIELDS
    )


# 分组（需求 §3.11）
NODE_SECTIONS = (
    ("基本情况",
     ("id", "name", "coords", "type", "level", "is_capital")),
    ("归属与资源",
     ("owner", "troops", "gold", "food")),
)


def node_sections(fields, info=()):
    """字段表 → 分组（FieldGroup 元组）；据点情报的只读信息块并入「基本情况」。"""
    by_key = {f.key: f for f in fields}
    groups = []
    for index, (title, keys) in enumerate(NODE_SECTIONS):
        groups.append(FieldGroup(
            title=title,
            fields=tuple(by_key[k] for k in keys if k in by_key),
            info=tuple(info) if index == 0 else (),
        ))
    return tuple(groups)
