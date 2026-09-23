# -*- coding: utf-8 -*-
"""临时测试脚本，验证 SettingsManager 的基本功能。测完可删。"""

from game.config.settings_manager import SettingsManager
from game.config import style

print("=" * 60)
print("① 创建管理器 + 应用默认值")
print("=" * 60)
sm = SettingsManager()
print("settings 文件路径：", sm.path)
print("是否存在：", sm.path.is_file())
print("初始 MAP_STYLE.point.fill =", style.MAP_STYLE["point"]["fill"])
print("初始 CITY_LEVEL_MIN_SCALE[7] =", style.CITY_LEVEL_MIN_SCALE[7])
print("初始 LAYER_VISIBILITY.water =", style.LAYER_VISIBILITY["water"])


print()
print("=" * 60)
print("② 修改几个值，再 apply，看 style 里的原字典有没有变")
print("=" * 60)
sm.set("MAP_STYLE.point.fill", "#FF0000")
sm.set("CITY_LEVEL_MIN_SCALE.7", 123)
sm.set("LAYER_VISIBILITY.water", True)
sm.set("MAP_STYLE.point.size_divisor", 900)
sm.apply()

print("MAP_STYLE.point.fill           =", style.MAP_STYLE["point"]["fill"],
      "（期望 #FF0000）")
print("CITY_LEVEL_MIN_SCALE[7]        =", style.CITY_LEVEL_MIN_SCALE[7],
      "（期望 123，注意是 int key）")
print("LAYER_VISIBILITY.water         =", style.LAYER_VISIBILITY["water"],
      "（期望 True）")
print("MAP_STYLE.point.size_divisor   =", style.MAP_STYLE["point"]["size_divisor"],
      "（期望 900）")

print()
print("已修改的路径：")
for p in sm.changed_paths():
    print("   ", p)


print()
print("=" * 60)
print("③ 保存到 userdata/settings.json")
print("=" * 60)
sm.save()
print("保存完成，文件内容：")
print(sm.path.read_text(encoding="utf-8"))


print()
print("=" * 60)
print("④ 新建第二个管理器（模拟“重启程序”），看是否读回覆盖值")
print("=" * 60)
sm2 = SettingsManager()
sm2.apply()
print("MAP_STYLE.point.fill  =", style.MAP_STYLE["point"]["fill"],
      "（期望 #FF0000）")
print("CITY_LEVEL_MIN_SCALE[7] =", style.CITY_LEVEL_MIN_SCALE[7],
      "（期望 123）")
print("LAYER_VISIBILITY.water =", style.LAYER_VISIBILITY["water"],
      "（期望 True）")


print()
print("=" * 60)
print("⑤ 恢复全部默认 + apply，看是否回到 style.py 里的原值")
print("=" * 60)
sm2.reset_all()
sm2.apply()
print("MAP_STYLE.point.fill  =", style.MAP_STYLE["point"]["fill"],
      "（期望 #3b2a1a）")
print("CITY_LEVEL_MIN_SCALE[7] =", style.CITY_LEVEL_MIN_SCALE[7],
      "（期望 350）")
print("LAYER_VISIBILITY.water =", style.LAYER_VISIBILITY["water"],
      "（期望 False）")
print("当前 changed_paths =", sm2.changed_paths(),
      "（期望空列表）")


print()
print("=" * 60)
print("⑥ 清理：删掉本地设置文件，让游戏恢复到“无本地配置”状态")
print("=" * 60)
if sm2.path.is_file():
    sm2.path.unlink()
    print("已删除", sm2.path)
else:
    print("没有设置文件可删")

print()
print("全部测试完成。")