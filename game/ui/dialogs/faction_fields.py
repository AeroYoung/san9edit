# -*- coding: utf-8 -*-
"""势力编辑弹窗的字段表。"""

from .field_spec import Field


FACTION_FIELDS = (
    Field("id",       "编号",  "readonly"),
    Field("name",     "势力名", "str"),
    Field("color",    "颜色",  "color"),
    Field("prestige", "威望",  "int", min=0),
    Field("stance",   "关系",  "int", min=-100, max=100),
    Field("gold",     "金钱",  "readonly"),
    Field("food",     "军粮",  "readonly"),
    Field("troops",   "兵力",  "readonly"),   # ★ 派生值（名下据点求和）
)