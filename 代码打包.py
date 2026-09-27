# pack_for_review.py —— 放在项目根目录，python pack_for_review.py 直接运行
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_BASE = ROOT / "review_pack"
MAX_SINGLE = 300 * 1024
VOL_TARGET = 90 * 1024

CODE_FILES = [
    # game/core
    "game/core/world.py",
    "game/core/faction.py",
    "game/core/character.py",
    "game/core/node.py",
    "game/core/scenario.py",
    "game/core/official_title.py",
    "game/core/edit_session.py",
    "game/core/edit_commands.py",
    "game/core/scenario_writer.py",
    # game/ui
    "game/ui/main_window.py",
    "game/ui/top_bar.py",
    "game/ui/side_panel.py",
    "game/ui/character_info_window.py",
    "game/ui/node_info_window.py",
    "game/ui/dialogs/field_spec.py",
    "game/ui/dialogs/edit_dialog.py",
    "game/ui/dialogs/node_fields.py",
    "game/ui/dialogs/faction_fields.py",
    "game/ui/dialogs/node_edit.py",
    "game/ui/dialogs/faction_edit.py",
    "game/ui/dialogs/move_to_node.py",
    # game/ui/panels
    "game/ui/panels/list/panel.py",
    "game/ui/panels/list/columns.py",
    "game/ui/panels/list/context_menu.py",
    "game/ui/panels/list/model.py",
    "game/ui/panels/node_panel.py",
    "game/ui/panels/character_panel.py",
    "game/ui/panels/faction_panel.py",
    # game/config
    "game/config/constants.py",
    "game/config/style.py",
    "game/config/settings_schema.py",
    "game/config/settings_manager.py",
]


def load_text(rel):
    p = ROOT / rel
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"[读取失败] {e}"


def slice_characters_json():
    p = ROOT / "assets" / "characters.json"
    if not p.exists():
        return "[缺] assets/characters.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return f"[解析失败] {e}"
    out = {}
    for k in ("version", "source", "count"):
        if k in d:
            out[k] = d[k]
    if "_name_index" in d:
        out["_name_index_sample"] = dict(list(d["_name_index"].items())[:3])
    if "_ambiguous_names" in d:
        out["_ambiguous_names"] = d["_ambiguous_names"]
    if "_missing_refs" in d:
        out["_missing_refs"] = d["_missing_refs"]
    chars = d.get("characters", {})
    out["characters_sample"] = dict(list(chars.items())[:3])
    return json.dumps(out, ensure_ascii=False, indent=2)


def slice_scenario_json():
    p = ROOT / "scenarios" / "default.json"
    if not p.exists():
        return "[缺] scenarios/default.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return f"[解析失败] {e}"
    out = {}
    for k in ("version", "id", "name", "desc", "start",
              "player_faction", "character_id_range"):
        if k in d:
            out[k] = d[k]
    for sec, n in (("factions", 3), ("characters", 3), ("nodes", 3), ("officials", 5)):
        s = d.get(sec, {})
        out[sec + "_sample"] = dict(list(s.items())[:n]) if isinstance(s, dict) else s
    return json.dumps(out, ensure_ascii=False, indent=2)


def slice_map_geojson():
    p = ROOT / "assets" / "map.geojson"
    if not p.exists():
        return "[缺] assets/map.geojson"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return f"[解析失败] {e}"
    states = d.get("states", [])
    if not states:
        return json.dumps(d, ensure_ascii=False, indent=2)[:2000]
    s0 = states[0]
    meta = {k: s0.get(k) for k in s0 if k not in ("counties", "boundary")}
    counties = s0.get("counties", [])[:2]
    c_out = []
    for c in counties:
        cm = {k: c.get(k) for k in c if k not in ("cities", "boundary", "name_coords")}
        cities = c.get("cities", [])[:1]
        cm["cities_sample"] = cities
        c_out.append(cm)
    meta["counties_sample"] = c_out
    out = {"states_count": len(states), "state_sample": meta}
    return json.dumps(out, ensure_ascii=False, indent=2)


def main():
    blocks = []
    missing = []

    for rel in CODE_FILES:
        txt = load_text(rel)
        if txt is None:
            missing.append(rel)
            blocks.append(f"### {rel}\n\n[缺] {rel}\n")
            continue
        ext = os.path.splitext(rel)[1].lstrip(".") or "text"
        if ext == "py":
            fence = "python"
        else:
            fence = ext
        blocks.append(f"### {rel}\n\n```{fence}\n{txt}\n```\n")

    blocks.append("### assets/characters.json（截取）\n\n```json\n"
                  + slice_characters_json() + "\n```\n")
    blocks.append("### scenarios/default.json（截取）\n\n```json\n"
                  + slice_scenario_json() + "\n```\n")
    blocks.append("### assets/map.geojson（截取）\n\n```json\n"
                  + slice_map_geojson() + "\n```\n")

    full = "\n".join(blocks)
    total = len(full.encode("utf-8"))

    OUT_BASE.mkdir(exist_ok=True)
    if total <= MAX_SINGLE:
        out = OUT_BASE / "review_pack.txt"
        out.write_text(full, encoding="utf-8")
        outs = [out]
    else:
        outs = []
        cur = []
        cur_size = 0
        idx = 1
        for b in blocks:
            sz = len(b.encode("utf-8"))
            if cur and cur_size + sz > VOL_TARGET:
                out = OUT_BASE / f"review_pack_{idx:02d}.txt"
                out.write_text("\n".join(cur), encoding="utf-8")
                outs.append(out)
                cur = []
                cur_size = 0
                idx += 1
            cur.append(b)
            cur_size += sz
        if cur:
            out = OUT_BASE / f"review_pack_{idx:02d}.txt"
            out.write_text("\n".join(cur), encoding="utf-8")
            outs.append(out)

    print("输出：")
    for o in outs:
        print(f"  {o}  ({o.stat().st_size / 1024:.1f} KB)")
    if missing:
        print("缺失文件：")
        for m in missing:
            print(f"  [缺] {m}")
    print("请把 review_pack 目录下的文件贴回对话。")
    print(f"共 {len(outs)} 个文件。")


if __name__ == "__main__":
    main()