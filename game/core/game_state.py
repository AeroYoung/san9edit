# -*- coding: utf-8 -*-
"""游戏状态：回合、日期、玩家势力、资源。

后续要加武将池、城市数据库、外交关系等，都在这里扩展。
UI 通过 get_display_items() 拿到信息栏要显示的内容，
改 UI 时不用动这个文件。
"""

from game.config import constants as C


class GameState:
    def __init__(self):
        self.year = C.INITIAL_YEAR
        self.month = C.INITIAL_MONTH
        self.xun = C.INITIAL_XUN       # 1=上旬 2=中旬 3=下旬

        self.player_faction = C.INITIAL_FACTION
        self.prestige = C.INITIAL_PRESTIGE
        self.gold = C.INITIAL_GOLD
        self.food = C.INITIAL_FOOD

    # ---------- 日期 ----------
    def date_text(self):
        xun_name = ("上", "中", "下")[self.xun - 1]
        return f"{self.year}年 {self.month}月{xun_name}旬"

    def advance_turn(self):
        """推进一旬。一个月三旬，三个月一季度。"""
        self.xun += 1
        if self.xun > 3:
            self.xun = 1
            self.month += 1
            if self.month > 12:
                self.month = 1
                self.year += 1

    # ---------- 资源 ----------
    def change_gold(self, delta):
        self.gold = max(0, self.gold + delta)

    def change_food(self, delta):
        self.food = max(0, self.food + delta)

    def change_prestige(self, delta):
        self.prestige = max(0, self.prestige + delta)

    # ---------- 信息栏数据源 ----------
    def get_display_items(self):
        """返回 [(key, 标签, 值)]，信息栏按顺序渲染。

        想加新信息项（比如"兵力"、"士气"），在这里加一行即可，
        信息栏会自动多出一个可点击的项目。
        """
        return [
            ("date",     "日期", self.date_text()),
            ("faction",  "势力", self.player_faction),
            ("prestige", "威望", f"{self.prestige:,}"),
            ("gold",     "金钱", f"{self.gold:,}"),
            ("food",     "军粮", f"{self.food:,}"),
        ]