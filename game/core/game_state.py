# -*- coding: utf-8 -*-
"""游戏状态：回合、日期、玩家势力、资源。

未加载剧本时处于"未初始化"状态（year=0，各资源=0），信息栏显示 "—"。
剧本加载后 MainWindow 调用 sync_from_world() 注入 World，
信息栏改为显示玩家势力的实时数据。
"""

import logging

logger = logging.getLogger(__name__)


class GameState:
    def __init__(self):
        # 未初始化状态：等剧本/存档注入
        self.year = 0
        self.month = 0
        self.xun = 0

        self.player_faction = None
        self.prestige = 0
        self.gold = 0
        self.food = 0

        self.world = None

    # ---------- 剧本同步 ----------
    def sync_from_world(self, world):
        """剧本加载后调用：绑定 World，并把起始日期同步过来。"""
        self.world = world
        if world is not None:
            self.year = world.year
            self.month = world.month
            self.xun = world.xun
        logger.info("同步 World 到 GameState：%s", self.date_text())

    # ---------- 日期 ----------
    def date_text(self):
        if not self.year:
            return "—"
        xun_name = ("上", "中", "下")[self.xun - 1]
        return f"{self.year}年 {self.month}月{xun_name}旬"

    def advance_turn(self):
        if not self.year:
            return
        self.xun += 1
        if self.xun > 3:
            self.xun = 1
            self.month += 1
            if self.month > 12:
                self.month = 1
                self.year += 1
        logger.info("推进回合 → %s", self.date_text())

    # ---------- 资源（写回玩家势力） ----------
    def change_gold(self, delta):
        pf = self._player_faction()
        if pf is not None:
            # TODO(phase3): GameState.change_gold 需适配派生值
            # Faction.gold 已是 property（名下据点求和，无 setter），此处赋值会报错。
            pf.gold = max(0, pf.gold + delta)
        else:
            self.gold = max(0, self.gold + delta)

    def change_food(self, delta):
        pf = self._player_faction()
        if pf is not None:
            # TODO(phase3): GameState.change_food 需适配派生值
            pf.food = max(0, pf.food + delta)
        else:
            self.food = max(0, self.food + delta)

    def change_prestige(self, delta):
        pf = self._player_faction()
        if pf is not None:
            pf.prestige = max(0, pf.prestige + delta)
        else:
            self.prestige = max(0, self.prestige + delta)

    # ---------- 内部 ----------
    def _player_faction(self):
        if self.world is None:
            return None
        return self.world.player_faction()

    # ---------- 信息栏数据源 ----------
    def get_display_items(self):
        pf = self._player_faction()

        if pf is not None:
            faction_str = pf.name
            prestige_str = f"{pf.prestige:,}"
            gold_str = f"{pf.gold:,}"
            food_str = f"{pf.food:,}"
        else:
            faction_str = "—"
            prestige_str = "—"
            gold_str = "—"
            food_str = "—"

        return [
            ("date",     "日期", self.date_text()),
            ("faction",  "势力", faction_str),
            ("prestige", "威望", prestige_str),
            ("gold",     "金钱", gold_str),
            ("food",     "军粮", food_str),
        ]