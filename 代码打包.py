# -*- coding: utf-8 -*-
"""收集「职官面板 + 外官 rank 表」所需的代码与数据，输出可上传的 markdown。

用法：
    python pack_for_review.py

输出：review_pack.txt（<300KB）；超过时自动分卷 review_pack_01.txt …
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_PREFIX = "review_pack"
MAX_SINGLE = 300 * 1024
VOLUME_SIZE = 90 * 1024


# ============================================================
# 完整读取的代码文件
# ============================================================
CODE_FILES = [
    # ---- 官名 / 数据层 ----
    "game/core/official_title.py",
    "game/core/military_title.py",
    "game/core/character.py",
    "game/core/world.py",
    # ---- 配置 ----
    "game/config/style.py",
    "game/config/settings_schema.py",
    # ---- 面板框架 ----
    "game/ui/panels/list/panel.py",
    "game/ui/panels/list/columns.py",
    # ---- 4 个现有面板（作为模板）----
    "game/ui/panels/faction_panel.py",
    "game/ui/panels/character_panel.py",
    "game/ui/panels/node_panel.py",
    "game/ui/panels/troop_panel.py",
    # ---- 面板注册 / 装配 ----
    "game/ui/side_panel.py",
    "game/ui/main_window.py",
]


# ============================================================
# 数据文件截取（不给全量）
# ============================================================
def slice_map_geojson(path):
    """map.geojson 截取：顶层键 + 1 个完整州（含前 2 郡，每郡前 2 县）"""
    raw = json.loads(path.read_text(encoding="utf-8"))
    states = raw.get("states") or []
    out = {"__top_keys__": list(raw.keys()), "states_count": len(states)}
    if states:
        s = states[0]
        state_sample = {
            k: (v if k not in ("counties", "boundary", "name_coords")
                else f"<{len(v)} items 省略>" if isinstance(v, list) else v)
            for k, v in s.items()
        }
        counties = s.get("counties") or []
        county_samples = []
        for c in counties[:2]:
            cs = {k: (v if k not in ("cities", "boundary")
                      else f"<{len(v)} items 省略>")
                  for k, v in c.items()}
            city_samples = []
            for city in (c.get("cities") or [])[:2]:
                city_samples.append({
                    k: (v if k != "boundary" else f"<{len(v)} rings 省略>")
                    for k, v in city.items()
                })
            cs["cities_sample"] = city_samples
            county_samples.append(cs)
        state_sample["counties_sample"] = county_samples
        out["first_state"] = state_sample
    return json.dumps(out, ensure_ascii=False, indent=2)


def slice_characters(path):
    """characters.json：顶层元字段 + characters 前 3 条"""
    raw = json.loads(path.read_text(encoding="utf-8"))
    top = {k: v for k, v in raw.items() if k != "characters"}
    chars = raw.get("characters") or {}
    sample = dict(list(chars.items())[:3])
    return json.dumps({"__top__": top, "__sample_characters__": sample},
                      ensure_ascii=False, indent=2)


def slice_default(path):
    """default.json：顶层 + 每段前若干条"""
    raw = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for k, v in raw.items():
        if isinstance(v, dict):
            sample_n = 5 if k == "officials" else 3
            out[k] = dict(list(v.items())[:sample_n])
            out[k + "__total__"] = len(v)
        else:
            out[k] = v
    return json.dumps(out, ensure_ascii=False, indent=2)


JSON_SLICES = [
    ("assets/map.geojson", slice_map_geojson),
    ("assets/characters.json", slice_characters),
    ("scenarios/default.json", slice_default),
]


# ============================================================
# 打包
# ============================================================
def read_code(rel):
    p = ROOT / rel
    if not p.exists():
        return f"### {rel}\n[缺] {rel}\n"
    try:
        text = p.read_text(encoding="utf-8")
    except Exception as e:
        return f"### {rel}\n[读取失败] {e}\n"
    return f"### {rel}\n```python\n{text}\n```\n"


def read_slice(rel, fn):
    p = ROOT / rel
    if not p.exists():
        return f"### {rel}\n[缺] {rel}\n"
    try:
        body = fn(p)
    except Exception as e:
        return f"### {rel}\n[解析失败] {e}\n"
    return f"### {rel}\n```json\n{body}\n```\n"


def main():
    sections = []

    sections.append("## 一、代码文件（完整）\n")
    for rel in CODE_FILES:
        sections.append(read_code(rel))

    sections.append("\n## 二、数据文件（截取）\n")
    for rel, fn in JSON_SLICES:
        sections.append(read_slice(rel, fn))

    full = "\n".join(sections)
    total = len(full.encode("utf-8"))

    if total <= MAX_SINGLE:
        out = ROOT / f"{OUT_PREFIX}.txt"
        out.write_text(full, encoding="utf-8")
        print(f"输出：{out}  （{total/1024:.1f} KB）")
        print("请把整个文件内容贴回对话。")
        return

    volumes, current, cur_size = [], [], 0
    for sec in sections:
        sz = len(sec.encode("utf-8"))
        if current and cur_size + sz > VOLUME_SIZE:
            volumes.append("\n".join(current))
            current, cur_size = [], 0
        current.append(sec)
        cur_size += sz
    if current:
        volumes.append("\n".join(current))

    for i, vol in enumerate(volumes, 1):
        out = ROOT / f"{OUT_PREFIX}_{i:02d}.txt"
        out.write_text(vol, encoding="utf-8")
        size_kb = len(vol.encode("utf-8")) / 1024
        print(f"输出：{out}  （{size_kb:.1f} KB）")
    print(f"共 {len(volumes)} 卷，请依次全部贴回对话。")


if __name__ == "__main__":
    main()