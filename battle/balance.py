# -*- coding: utf-8 -*-
"""战斗模块数值配置。

三类十种兵种 + 3×3 克制矩阵。改平衡只改这一处。
纯数据，无逻辑、无 pygame。
"""

# ============================================================
# 兵种表：key → 兵种定义
# ============================================================
# category：骑 / 步 / 弓（克制矩阵用它做键）
# symbol_shape：diamond（菱形）/ rect（横长方形 + X）/ square（正方形）
# symbol_fill：solid / top_half / hollow / slash / fill_three /
#              fill_left_right / fill_bottom / upper_left_half
UNIT_TYPES = {
    # ---------------- 骑兵类（菱形） ----------------
    "cataphract": {
        "key": "cataphract", "name": "具装甲骑", "category": "骑",
        "troops_max": 3000, "move_points": 2,
        "attack_melee": 90, "attack_ranged": None, "attack_range": 1,
        "defense": 85,
        "stamina_cost_move": 3.0, "stamina_cost_attack": 8.0,
        "stamina_recover": 1.5, "morale_recover": 1.0,
        "attack_cooldown": 12, "morale_hit": 1.5,
        "morale_kill": 8.0, "morale_rout": 5.0,
        "symbol_shape": "diamond", "symbol_fill": "solid",
    },
    "heavy_cavalry": {
        "key": "heavy_cavalry", "name": "重骑", "category": "骑",
        "troops_max": 2800, "move_points": 3,
        "attack_melee": 80, "attack_ranged": None, "attack_range": 1,
        "defense": 70,
        "stamina_cost_move": 2.5, "stamina_cost_attack": 7.0,
        "stamina_recover": 1.5, "morale_recover": 1.0,
        "attack_cooldown": 10, "morale_hit": 1.5,
        "morale_kill": 8.0, "morale_rout": 5.0,
        "symbol_shape": "diamond", "symbol_fill": "top_half",
    },
    "light_cavalry": {
        "key": "light_cavalry", "name": "轻骑", "category": "骑",
        "troops_max": 2200, "move_points": 4,
        "attack_melee": 60, "attack_ranged": None, "attack_range": 1,
        "defense": 50,
        "stamina_cost_move": 2.0, "stamina_cost_attack": 6.0,
        "stamina_recover": 2.0, "morale_recover": 1.2,
        "attack_cooldown": 8, "morale_hit": 1.2,
        "morale_kill": 8.0, "morale_rout": 5.0,
        "symbol_shape": "diamond", "symbol_fill": "hollow",
    },
    "horse_archer": {
        "key": "horse_archer", "name": "弓骑", "category": "骑",
        "troops_max": 1800, "move_points": 4,
        "attack_melee": 40, "attack_ranged": 55, "attack_range": 3,
        "defense": 40,
        "stamina_cost_move": 2.0, "stamina_cost_attack": 6.0,
        "stamina_recover": 2.0, "morale_recover": 1.2,
        "attack_cooldown": 9, "morale_hit": 1.2,
        "morale_kill": 8.0, "morale_rout": 5.0,
        "symbol_shape": "diamond", "symbol_fill": "slash",
    },

    # ---------------- 步兵类（横长方形 + X） ----------------
    "heavy_armor": {
        "key": "heavy_armor", "name": "重甲", "category": "步",
        "troops_max": 3500, "move_points": 1,
        "attack_melee": 70, "attack_ranged": None, "attack_range": 1,
        "defense": 90,
        "stamina_cost_move": 4.0, "stamina_cost_attack": 8.0,
        "stamina_recover": 1.5, "morale_recover": 1.5,
        "attack_cooldown": 12, "morale_hit": 1.0,
        "morale_kill": 8.0, "morale_rout": 5.0,
        "symbol_shape": "rect", "symbol_fill": "fill_three",
    },
    "armored": {
        "key": "armored", "name": "甲士", "category": "步",
        "troops_max": 3000, "move_points": 2,
        "attack_melee": 60, "attack_ranged": None, "attack_range": 1,
        "defense": 70,
        "stamina_cost_move": 3.0, "stamina_cost_attack": 7.0,
        "stamina_recover": 1.8, "morale_recover": 1.5,
        "attack_cooldown": 10, "morale_hit": 1.0,
        "morale_kill": 8.0, "morale_rout": 5.0,
        "symbol_shape": "rect", "symbol_fill": "fill_left_right",
    },
    "light_armor": {
        "key": "light_armor", "name": "甲兵", "category": "步",
        "troops_max": 2500, "move_points": 2,
        "attack_melee": 50, "attack_ranged": None, "attack_range": 1,
        "defense": 55,
        "stamina_cost_move": 3.0, "stamina_cost_attack": 6.0,
        "stamina_recover": 2.0, "morale_recover": 1.5,
        "attack_cooldown": 9, "morale_hit": 1.0,
        "morale_kill": 8.0, "morale_rout": 5.0,
        "symbol_shape": "rect", "symbol_fill": "fill_bottom",
    },
    "levy": {
        "key": "levy", "name": "徒卒", "category": "步",
        "troops_max": 2000, "move_points": 3,
        "attack_melee": 35, "attack_ranged": None, "attack_range": 1,
        "defense": 40,
        "stamina_cost_move": 2.0, "stamina_cost_attack": 5.0,
        "stamina_recover": 2.5, "morale_recover": 1.5,
        "attack_cooldown": 8, "morale_hit": 1.0,
        "morale_kill": 8.0, "morale_rout": 5.0,
        "symbol_shape": "rect", "symbol_fill": "hollow",
    },

    # ---------------- 弓兵类（正方形） ----------------
    "crossbow": {
        "key": "crossbow", "name": "弩士", "category": "弓",
        "troops_max": 1800, "move_points": 2,
        "attack_melee": 25, "attack_ranged": 90, "attack_range": 4,
        "defense": 35,
        "stamina_cost_move": 3.0, "stamina_cost_attack": 8.0,
        "stamina_recover": 2.0, "morale_recover": 1.2,
        "attack_cooldown": 14, "morale_hit": 1.0,
        "morale_kill": 8.0, "morale_rout": 5.0,
        "symbol_shape": "square", "symbol_fill": "upper_left_half",
    },
    "archer": {
        "key": "archer", "name": "步弓", "category": "弓",
        "troops_max": 1600, "move_points": 3,
        "attack_melee": 30, "attack_ranged": 70, "attack_range": 3,
        "defense": 30,
        "stamina_cost_move": 2.5, "stamina_cost_attack": 7.0,
        "stamina_recover": 2.2, "morale_recover": 1.2,
        "attack_cooldown": 10, "morale_hit": 1.0,
        "morale_kill": 8.0, "morale_rout": 5.0,
        "symbol_shape": "square", "symbol_fill": "hollow",
    },
}

# ============================================================
# 克制矩阵：COUNTER_MATRIX[攻方类别][守方类别] = 倍率（本步只写表不消费）
# ============================================================
COUNTER_MATRIX = {
    "骑": {"骑": 1.0, "步": 0.9, "弓": 1.3},
    "步": {"骑": 1.3, "步": 1.0, "弓": 0.9},
    "弓": {"骑": 0.9, "步": 1.3, "弓": 1.0},
}
