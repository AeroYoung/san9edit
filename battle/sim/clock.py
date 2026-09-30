# -*- coding: utf-8 -*-
"""tick 时钟：把真实时间累计成模拟 tick。

纯逻辑，**不** import pygame。
"""

import logging

from battle import config

logger = logging.getLogger("battle.sim.clock")


class Clock:
    """持有累计时间 / 当前 tick 长度 / 暂停位 / 速度档。

    - 暂停期间**不累加**时间，恢复后不补跑
    - 切档立即生效并**清零**累计时间
    - 一帧可推进多次（防卡帧丢 tick）
    """

    def __init__(self, speed=None):
        speed = config.DEFAULT_SPEED if speed is None else speed
        if speed not in config.SPEED_PRESETS:
            logger.warning("未知速度档 %s，回退到 %s", speed, config.DEFAULT_SPEED)
            speed = config.DEFAULT_SPEED
        self.speed = speed
        self.tick_ms = config.SPEED_PRESETS[speed]
        self.paused = False
        self._acc_ms = 0.0

    # ============================================================
    # 控制
    # ============================================================
    def set_speed(self, speed):
        """切换速度档：立即生效 + 清零累计（不把旧档累计带入新档）。"""
        if speed not in config.SPEED_PRESETS:
            logger.warning("忽略未知速度档：%s", speed)
            return False
        self.speed = int(speed)
        self.tick_ms = config.SPEED_PRESETS[self.speed]
        self._acc_ms = 0.0
        logger.debug("速度档切换：%sx（%s ms/tick）", self.speed, self.tick_ms)
        return True

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False
        self._acc_ms = 0.0      # 恢复后不补跑：丢掉暂停前的零头

    def toggle(self):
        """切换暂停 / 继续，返回切换后是否在运行。"""
        if self.paused:
            self.resume()
        else:
            self.pause()
        return not self.paused

    def request_step(self):
        """单步：先进入暂停态（并清零累计），由调用方推进恰好一个 tick。"""
        self.paused = True
        self._acc_ms = 0.0

    # ============================================================
    # 推进
    # ============================================================
    def advance(self, elapsed_ms):
        """累计真实时间，返回本帧应推进的 tick 数（暂停 → 0）。"""
        if self.paused or elapsed_ms <= 0:
            return 0
        self._acc_ms += elapsed_ms
        ticks = int(self._acc_ms // self.tick_ms)
        if ticks:
            self._acc_ms -= ticks * self.tick_ms
        return ticks

    def progress(self):
        """当前 tick 内的进度 0.0–1.0（供渲染插值）；暂停 → 0.0。"""
        if self.paused or self.tick_ms <= 0:
            return 0.0
        return max(0.0, min(1.0, self._acc_ms / float(self.tick_ms)))
