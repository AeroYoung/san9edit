# -*- coding: utf-8 -*-
"""战斗模块对主游戏的接入接口。

硬约束：本模块**不依赖 pygame** —— 主游戏接入时不需要先初始化图形环境。

步骤01 只放空 dataclass / 类壳，字段与实现留待后续步骤。
"""

from dataclasses import dataclass


@dataclass
class BattleConfig:
    """主游戏传给 battle 的入参（步骤01 空壳）。

    主游戏侧不直接读 `World`，由主游戏侧组装本对象后传入。
    后续步骤补：参战双方部队、地图 id、随机种子等。
    """


@dataclass
class BattleResult:
    """battle 返回给主游戏的出参（步骤01 空壳）。

    后续步骤补：胜负 / 双方剩余部队 / 伤亡统计 / 耗时 / 消亡原因分类。
    """


class BattleSession:
    """一次战斗会话（步骤01 空壳）。

    同一进程内可连续开多场；不支持并行（单进程单战斗窗口）。
    """

    def run(self, config, map_path=None) -> BattleResult:
        """执行一场战斗并返回结果。"""
        raise NotImplementedError("步骤01 未实现：战斗会话留待后续步骤")
