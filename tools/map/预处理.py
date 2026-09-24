import json
from pathlib import Path

# 当前脚本所在目录
BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "map.geojson"
OUTPUT_FILE = BASE_DIR / "map_processed.geojson"

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    states = data.get("states", [])

    print("=" * 70)
    print("统计信息（县类型改为城、渡口/津改为渡口之前）")
    print("=" * 70)

    no_capital_counties = []  # 记录没有郡治的郡

    for state in states:
        state_name = state.get("name")
        counties = state.get("counties", [])
        print(f"\n州：{state_name}，郡数：{len(counties)}")

        for county in counties:
            county_name = county.get("name")
            cities = county.get("cities", [])

            # 1. 过滤 cities：保留 type 为 "县"、"关隘"、"渡口/津"
            filtered_cities = [
                c for c in cities
                if c.get("type") in ["县", "关隘", "渡口/津"]
            ]
            county["cities"] = filtered_cities

            # 2. 统计县的数量（原始 type == "县"）
            county_count = sum(1 for c in filtered_cities if c.get("type") == "县")

            # 3. 判断是否有郡治
            capital = county.get("capital")
            capital_id = county.get("capital_id")
            has_capital_field = capital is not None and capital_id is not None
            has_capital_city = any(c.get("is_capital") is True for c in filtered_cities)
            has_capital = has_capital_field  # 以郡的 capital 字段为准

            if not has_capital:
                no_capital_counties.append(f"{state_name} - {county_name}")

            # 输出郡级统计
            print(f"  郡：{county_name}，县数量：{county_count}，有郡治：{'是' if has_capital else '否'}")
            if has_capital_field != has_capital_city:
                print(f"    注意：{county_name} 郡治字段与城市标记不一致 "
                      f"(capital字段={has_capital_field}, 城市标记={has_capital_city})")

            # 4. 类型转换：县 -> 城，渡口/津 -> 渡口
            for c in filtered_cities:
                if c.get("type") == "县":
                    c["type"] = "城"
                elif c.get("type") == "渡口/津":
                    c["type"] = "渡口"

    # 汇总没有郡治的郡
    print("\n" + "=" * 70)
    if no_capital_counties:
        print("以下郡没有郡治：")
        for item in no_capital_counties:
            print(f"  - {item}")
    else:
        print("所有郡都有郡治。")

    # 保存修改后的 JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n处理完成，已保存到：{OUTPUT_FILE}")

if __name__ == "__main__":
    main()