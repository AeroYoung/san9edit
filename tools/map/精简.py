#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 map_processed.geojson 中剥离所有坐标/点位数据，生成精简版。

移除的字段：
  - states[].name_coords
  - states[].boundary
  - states[].counties[].name_coords
  - states[].counties[].boundary
  - states[].counties[].cities[].coords
  - states[].counties[].cities[].boundary   （若存在）

保留的字段：
  - 州：id, name, counties
  - 郡：id, name, capital, capital_id, cities
  - 城/关隘/渡口：id, name, is_capital, level, type
"""

import json
import os
from pathlib import Path

# 当前脚本所在目录
BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "map_processed.geojson"
OUTPUT_FILE = BASE_DIR / "map_slim.geojson"

def strip_state(state):
    state.pop("name_coords", None)
    state.pop("boundary", None)

    for county in state.get("counties", []):
        strip_county(county)


def strip_county(county):
    county.pop("name_coords", None)
    county.pop("boundary", None)

    for city in county.get("cities", []):
        strip_city(city)


def strip_city(city):
    city.pop("coords", None)
    city.pop("boundary", None)


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"未找到 {INPUT_FILE}")
        return

    in_size = os.path.getsize(INPUT_FILE)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    states = data.get("states", [])
    for state in states:
        strip_state(state)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    out_size = os.path.getsize(OUTPUT_FILE)

    # 统计
    total_counties = 0
    total_cities = 0
    for state in states:
        counties = state.get("counties", [])
        total_counties += len(counties)
        for county in counties:
            total_cities += len(county.get("cities", []))

    print("=" * 50)
    print(f"输入：{INPUT_FILE}  ({human_size(in_size)})")
    print(f"输出：{OUTPUT_FILE}  ({human_size(out_size)})")
    print(f"压缩率：{(1 - out_size / in_size) * 100:.1f}%")
    print("-" * 50)
    print(f"州：  {len(states)}")
    print(f"郡：  {total_counties}")
    print(f"据点：{total_cities}")
    print("=" * 50)


if __name__ == "__main__":
    main()