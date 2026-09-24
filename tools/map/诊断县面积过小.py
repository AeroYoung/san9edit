# check_tiny.py —— 找"异常小"的县
import json
from pathlib import Path
from statistics import median
from shapely.geometry import Polygon

BASE = Path(__file__).resolve().parent
SRC = BASE / "map_with_boundaries.geojson"

def ring_to_poly(ring):
    if not ring or len(ring) < 3:
        return None
    p = Polygon([(float(x), float(y)) for x, y in ring])
    if not p.is_valid:
        p = p.buffer(0)
    return p if not p.is_empty else None

def main():
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)

    tiny = []
    for state in data["states"]:
        for county in state["counties"]:
            areas = []
            for c in county.get("cities", []):
                p = ring_to_poly(c.get("boundary"))
                if p is None:
                    tiny.append((0, c["name"], county["name"], state["name"], "no boundary"))
                    continue
                areas.append((c["name"], p.area))
            if not areas:
                continue
            med = median(a for _, a in areas)
            if med <= 0:
                continue
            for name, a in areas:
                if a < med * 0.02:            # 小于同郡中位数的 2%
                    tiny.append((a, name, county["name"], state["name"],
                                 f"同郡中位数 {med:.3e}"))

    print(f"异常小县: {len(tiny)} 个\n")
    for a, city, county, state, note in sorted(tiny, key=lambda x: x[0])[:30]:
        print(f"  {city} ({county}/{state}): {a:.3e}  [{note}]")

if __name__ == "__main__":
    main()