# -*- coding: utf-8 -*-
"""据点编辑弹窗的字段表。"""

from .field_spec import Field


NODE_FIELDS = (
    Field("id",         "编号", "readonly"),
    Field("name",       "县名", "readonly"),
    Field("coords",     "坐标", "readonly",
          display_fn=lambda v, w: f"({v[0]:.2f}, {v[1]:.2f})" if v else "—"),
    Field("owner",      "势力", "readonly",
          display_fn=lambda v, w: (w.faction(v).name if v and w and w.faction(v)
                                   else "无主")),
    Field("type",       "类型", "choice",
          options=(("城", "城"), ("关隘", "关隘"), ("渡口", "渡口"))),
    Field("level",      "规模", "int", min=1, max=10),
    Field("is_capital", "郡治", "bool"),
    Field("troops",     "兵力", "int", min=0),
    Field("gold",       "金钱", "int", min=0),
    Field("food",       "军粮", "int", min=0),
)
