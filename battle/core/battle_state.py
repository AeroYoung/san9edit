# -*- coding: utf-8 -*-
"""战斗状态容器（纯逻辑，**不** import pygame）。

持有全部部队，并提供：
- 按 id / 阵营 / 轴向坐标查询
- 视口轴向矩形内的单位迭代（供部队层裁剪，不遍历全表）
- 从部队 JSON 载入并校验（见 `battle/docs/步骤02需求.md` §4）
"""

import json
import logging
from pathlib import Path

from battle.core import unit_types
from battle.core.unit import Unit

logger = logging.getLogger("battle.core.battle_state")


class BattleState:
    """units 容器 + 两套索引（按坐标 / 按列）。"""

    def __init__(self, cols=0, rows=0):
        self.cols = int(cols)
        self.rows = int(rows)

        self.units = {}        # id → Unit
        self._by_pos = {}      # (q, r) → Unit
        self._by_col = {}      # q → list[Unit]（插入序；矩形筛选靠 r 比较）

    # ============================================================
    # 查询
    # ============================================================
    def unit(self, uid):
        """按 id 取单位；不存在 → None。"""
        return self.units.get(uid)

    def units_of(self, side):
        """某一方的全部单位（按 id 升序）。"""
        return sorted((u for u in self.units.values() if u.side == side),
                      key=lambda u: u.id)

    def unit_at(self, q, r):
        """按**轴向坐标**取单位；该格为空 → None。"""
        return self._by_pos.get((q, r))

    def all_units(self):
        """全部单位（按 id 升序）。"""
        return sorted(self.units.values(), key=lambda u: u.id)

    def units_in_axial_rect(self, q_lo, q_hi, r_lo, r_hi):
        """轴向矩形内的单位。

        只遍历**命中矩形覆盖的列**及其列内单位，不遍历全表 —— 视口裁剪专用。
        """
        out = []
        for q in range(q_lo, q_hi + 1):
            for u in self._by_col.get(q, ()):
                if r_lo <= u.r <= r_hi:
                    out.append(u)
        return out

    # ============================================================
    # 载入
    # ============================================================
    def from_json(self, path, side):
        """读一个阵营的部队 JSON 并入本状态。

        两侧各调一次（同方 / 跨方的坐标重复都在这里拦）。
        返回成功并入的单位数；文件缺失 / 损坏 → 记 WARNING 并返回 0，不抛。
        """
        path = Path(path)
        name = path.name

        if not path.exists():
            logger.warning("部队数据文件不存在：%s（该方按 0 支部队处理）", path)
            return 0

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.warning("部队数据文件无法解析：%s（%s）", path, exc)
            return 0

        if not isinstance(raw, dict):
            logger.warning("部队数据顶层不是对象：%s", path)
            return 0

        entries = raw.get("units")
        if not isinstance(entries, list):
            logger.warning("部队数据缺少 units 数组：%s", path)
            return 0

        added = 0
        for index, entry in enumerate(entries):
            unit = self._parse_entry(entry, side, name, index)
            if unit is not None and self._add(unit, name):
                added += 1

        logger.info("部队数据载入：%s（side=%s，%s/%s 支）",
                    name, side, added, len(entries))
        return added

    # ============================================================
    # 内部：逐条校验
    # ============================================================
    def _parse_entry(self, entry, side, name, index):
        """校验一条 JSON 记录；不合法 → 记 WARNING 并返回 None。"""
        if not isinstance(entry, dict):
            logger.warning("%s 第 %s 条不是对象，丢弃", name, index)
            return None

        for key in ("id", "type", "col", "row"):
            if entry.get(key) is None:
                logger.warning("%s 第 %s 条缺字段 %s，丢弃（id=%s）",
                               name, index, key, entry.get("id"))
                return None

        type_key = str(entry["type"])
        if not unit_types.exists(type_key):
            logger.warning("%s 的兵种不在兵种表：%s（id=%s），丢弃",
                           name, type_key, entry.get("id"))
            return None

        coords = self._parse_coords(entry)
        if coords is None:
            logger.warning("%s 的坐标不是整数：col=%r row=%r（id=%s），丢弃",
                           name, entry.get("col"), entry.get("row"),
                           entry.get("id"))
            return None
        col, row = coords
        if not (0 <= col < self.cols and 0 <= row < self.rows):
            logger.warning("%s 的坐标越界：(col=%s, row=%s) 不在 %s×%s 内（id=%s），丢弃",
                           name, col, row, self.cols, self.rows, entry.get("id"))
            return None

        troops = self._clamp_troops(entry, type_key, name)
        if troops is None:
            return None

        morale, stamina = self._clamp_bars(entry)
        facing = self._mod_facing(entry)

        data = {
            "id": entry["id"], "type": type_key, "col": col, "row": row,
            "troops": troops, "morale": morale, "stamina": stamina,
            "facing": facing, "general_id": entry.get("general_id"),
        }
        return Unit.from_dict(data, side)

    def _parse_coords(self, entry):
        try:
            return int(entry["col"]), int(entry["row"])
        except (TypeError, ValueError):
            return None

    def _clamp_troops(self, entry, type_key, name):
        """兵力：缺 → 兵种表上限；越界 → 钳制 + WARNING；非数字 → 丢弃。"""
        t = unit_types.get(type_key)
        cap = t["troops_max"]
        raw = entry.get("troops")
        if raw is None:
            return cap
        try:
            value = int(raw)
        except (TypeError, ValueError):
            logger.warning("%s 的兵力不是整数：%r（id=%s），丢弃",
                           name, raw, entry.get("id"))
            return None
        if value < 0:
            logger.warning("%s 的兵力为负：%s（id=%s），钳制到 0",
                           name, value, entry.get("id"))
            return 0
        if value > cap:
            logger.warning("%s 的兵力超上限：%s > %s（id=%s），钳制到上限",
                           name, value, cap, entry.get("id"))
            return cap
        return value

    def _clamp_bars(self, entry):
        """士气 / 体力：缺省 100.0，钳制到 1–100。"""
        out = []
        for key in ("morale", "stamina"):
            try:
                value = float(entry.get(key, 100.0))
            except (TypeError, ValueError):
                value = 100.0
            out.append(max(1.0, min(100.0, value)))
        return out[0], out[1]

    def _mod_facing(self, entry):
        try:
            return int(entry.get("facing", 0)) % 6
        except (TypeError, ValueError):
            return 0

    # ============================================================
    # 内部：入库（(q,r) 唯一）
    # ============================================================
    def _add(self, unit, name):
        """加入索引；该格已被占（同方或跨方）→ 后到者丢弃 + WARNING。"""
        key = (unit.q, unit.r)
        if key in self._by_pos:
            other = self._by_pos[key]
            logger.warning("%s 的 (col=%s, row=%s) 已被 %s 占用（%s），丢弃 %s",
                           name, *unit.offset(), other.id, other.side, unit.id)
            return False

        self.units[unit.id] = unit
        self._by_pos[key] = unit
        self._by_col.setdefault(unit.q, []).append(unit)
        return True
