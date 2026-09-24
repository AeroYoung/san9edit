# check_overlap.py
import json
from pathlib import Path
from shapely.geometry import Polygon

BASE = Path(__file__).resolve().parent
SRC = BASE / "map_with_boundaries.geojson"
AREA_TOL = 1e-9
TOP_N = 20

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

    total_pairs = 0
    total_area = 0.0
    per_county = []
    worst = []

    for state in data["states"]:
        for county in state["counties"]:
            polys = []
            for c in county.get("cities", []):
                p = ring_to_poly(c.get("boundary"))
                if p is not None:
                    polys.append((c["name"], p))

            pairs = 0
            area_sum = 0.0
            for i in range(len(polys)):
                for j in range(i + 1, len(polys)):
                    try:
                        inter = polys[i][1].intersection(polys[j][1])
                    except Exception:
                        continue
                    if inter.is_empty:
                        continue
                    a = inter.area
                    if a <= AREA_TOL:
                        continue
                    pairs += 1
                    area_sum += a
                    worst.append((a, state["name"], county["name"],
                                  polys[i][0], polys[j][0]))

            if pairs:
                per_county.append((state["name"], county["name"], pairs, area_sum))
                total_pairs += pairs
                total_area += area_sum

    print(f"重叠县对总数: {total_pairs}")
    print(f"重叠总面积:   {total_area:.6e} 度²\n")

    if per_county:
        print(f"最严重的郡（前 {TOP_N}）:")
        for s, c, n, a in sorted(per_county, key=lambda x: -x[3])[:TOP_N]:
            print(f"  {c} ({s}): {n} 对, 面积 {a:.3e}")

        print(f"\n最严重的县对（前 {TOP_N}）:")
        for a, s, c, na, nb in sorted(worst, key=lambda x: -x[0])[:TOP_N]:
            print(f"  {na} × {nb} ({c}/{s}): 面积 {a:.3e}")
    else:
        print("✓ 零重叠")

if __name__ == "__main__":
    main()