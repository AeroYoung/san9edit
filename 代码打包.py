# pack_for_review.py
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "pack_for_review.md"

sections = []

# ---- characters.json ----
p = ROOT / "assets" / "characters.json"
if p.exists():
    d = json.loads(p.read_text(encoding="utf-8"))
    chars = d.get("characters", {})
    L = [f"### characters.json", f"", f"共 {len(chars)} 人", "",
         "| id | name | family_name | birth_year | death_year |",
         "|---|---|---|---|---|"]
    for cid in sorted(chars.keys()):
        c = chars[cid]
        by = c.get("birth_year"); dy = c.get("death_year")
        L.append(f"| {cid} | {c.get('name','')} | {c.get('family_name') or ''} | "
                 f"{by if by is not None else ''} | {dy if dy is not None else ''} |")
    sections.append("\n".join(L))
else:
    sections.append(f"[缺] assets/characters.json")

# ---- map.geojson ----
p = ROOT / "assets" / "map.geojson"
if p.exists():
    d = json.loads(p.read_text(encoding="utf-8"))
    L = ["### map.geojson", "", "州/郡/县 id+name", "",
         "| 级 | id | name | 上级州 | 上级郡 | type | level |",
         "|---|---|---|---|---|---|---|"]
    for st in d.get("states", []):
        L.append(f"| 州 | {st.get('id','')} | {st.get('name','')} | — | — | — | — |")
        for co in st.get("counties", []):
            L.append(f"| 郡 | {co.get('id','')} | {co.get('name','')} | "
                     f"{st.get('name','')} | — | — | — |")
            for ci in co.get("cities", []):
                L.append(f"| 县 | {ci.get('id','')} | {ci.get('name','')} | "
                         f"{st.get('name','')} | {co.get('name','')} | "
                         f"{ci.get('type','')} | {ci.get('level','')} |")
    sections.append("\n".join(L))
else:
    sections.append(f"[缺] assets/map.geojson")

# ---- scenarios/default.json ----
p = ROOT / "scenarios" / "default.json"
if p.exists():
    d = json.loads(p.read_text(encoding="utf-8"))
    L = ["### scenarios/default.json", ""]
    L.append("meta: " + json.dumps(
        {k: d.get(k) for k in ("version","id","name","desc","start",
                               "player_faction","character_id_range")},
        ensure_ascii=False))
    facs = d.get("factions", {})
    L += ["", f"#### factions（{len(facs)} 家）", "",
          "| id | name | color | prestige | stance |", "|---|---|---|---|---|"]
    for fid, f in facs.items():
        L.append(f"| {fid} | {f.get('name','')} | {f.get('color','')} | "
                 f"{f.get('prestige','')} | {f.get('stance','')} |")
    chars = d.get("characters", {})
    L += ["", f"#### characters 段前 5 条（共 {len(chars)}）", "", "```json"]
    for cid in list(chars.keys())[:5]:
        L.append(json.dumps({cid: chars[cid]}, ensure_ascii=False))
    L.append("```")
    nodes = d.get("nodes", {})
    L += ["", f"#### nodes 段前 5 条（共 {len(nodes)}）", "", "```json"]
    for nid in list(nodes.keys())[:5]:
        L.append(json.dumps({nid: nodes[nid]}, ensure_ascii=False))
    L.append("```")
    sections.append("\n".join(L))
else:
    sections.append(f"[缺] scenarios/default.json")

# ---- 输出 ----
text = "# 打包数据（供 190 官员名单任务使用）\n\n" + "\n\n".join(sections)
OUT.write_text(text, encoding="utf-8")
size = OUT.stat().st_size
print(f"输出：{OUT}")
print(f"大小：{size/1024:.1f} KB")
if size > 300 * 1024:
    print("超过 300KB：请把文件按空行分段贴回，或告知我再写分卷逻辑")
else:
    print("请把全文贴回对话。")