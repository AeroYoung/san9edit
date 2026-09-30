# -*- coding: utf-8 -*-
"""地图 JSON 加载。

纯逻辑，**不** import pygame。

地图文件不存在 / JSON 损坏 / 字段类型非法 → 抛 `MapDataError`，
由 `app.py` 捕获后 ERROR 入日志 + 弹窗 + 退出。
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("battle.core.map_data")


class MapDataError(Exception):
    """地图文件缺失 / 无法解析 / 字段类型非法。"""


@dataclass
class MapData:
    """地图数据容器（字段 = 地图 JSON 的 8 个顶层字段）。"""

    version: int = 1
    id: str = "default"
    name: str = "默认地图"
    cols: int = 400
    rows: int = 300
    hex_size: int = 28
    orientation: str = "flat"
    tiles: list = field(default_factory=list)


def load_map(path) -> MapData:
    """读取地图 JSON 并返回 MapData。失败抛 MapDataError。"""
    p = Path(path)
    if not p.exists():
        raise MapDataError(f"地图文件不存在：{p}")

    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MapDataError(f"地图文件无法解析：{p}（{exc}）") from exc

    if not isinstance(raw, dict):
        raise MapDataError(f"地图文件顶层不是对象：{p}")

    data = MapData(
        version=_as_int(raw, "version", 1, p),
        id=_as_str(raw, "id", "default"),
        name=_as_str(raw, "name", "默认地图"),
        cols=_as_int(raw, "cols", 400, p),
        rows=_as_int(raw, "rows", 300, p),
        hex_size=_as_int(raw, "hex_size", 28, p),
        orientation=_as_str(raw, "orientation", "flat"),
        tiles=_as_tiles(raw, p),
    )

    if data.cols < 1 or data.rows < 1 or data.hex_size < 1:
        raise MapDataError(
            f"地图尺寸非法：cols={data.cols} rows={data.rows} "
            f"hex_size={data.hex_size}（{p}）"
        )

    logger.info(
        "地图加载完成：%s（%s × %s 格，hex_size=%s，orientation=%s，tiles=%s）",
        data.name, data.cols, data.rows, data.hex_size,
        data.orientation, len(data.tiles),
    )
    return data


def _as_int(raw, key, default, path):
    """取整数字段：缺失 → default；非数字 → 尝试 int()，仍失败 → 报错。"""
    if key not in raw or raw[key] is None:
        return default
    value = raw[key]
    if isinstance(value, bool):
        raise MapDataError(f"地图字段 {key} 类型非法：{value!r}（{path}）")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise MapDataError(
            f"地图字段 {key} 无法转为整数：{value!r}（{path}）"
        ) from exc


def _as_str(raw, key, default):
    """取字符串字段：缺失 / 空 → default。"""
    value = raw.get(key)
    return value if isinstance(value, str) and value else default


def _as_tiles(raw, path):
    """取 tiles：缺失 = 全同质（空表）；存在但非 list → 报错。"""
    if "tiles" not in raw or raw["tiles"] is None:
        logger.warning("地图缺少 tiles 字段，按全同质处理：%s", path)
        return []
    tiles = raw["tiles"]
    if not isinstance(tiles, list):
        raise MapDataError(f"地图字段 tiles 类型非法：{type(tiles).__name__}（{path}）")
    return tiles
