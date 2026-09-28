# 需求评审代码包

项目根：C:\Users\杨尧\Desktop\san9edit

文件数：4（缺 0）

### game/config/rules.py

```python
# -*- coding: utf-8 -*-
"""游戏运行策略常量（★ 唯一调参入口）。

**只放数据，不放逻辑**：想调整数值 / 表结构，改这个文件即可，
不需要动 core/ 下的任何代码。

本模块刻意不 import 任何 game.* 模块（纯字面量），
因此 core / ui / tools / tests 都可以安全引用，不会产生循环导入。

目录：
    一、武官（荣誉头衔）      MILITARY_TITLES / UNIQUE_MAX_RANK
    二、外官位阶（行政区分等）SI_* / RANK_* / COUNTY_RANK_* / CITY_RANK_*
    三、人物五维缺省值        DEFAULT_STAT
    四、势力附庸值范围        VASSAL_VALUE_MIN / VASSAL_VALUE_MAX
    五、势力显示色派生参数    DONGZHUO_* / DEFAULT_COLOR / HUE_STEP / MAX_HUE_SHIFT

★ 不在这里的东西：行政区 id 位数约定的「州 / 郡 / 县」与据点类型
  「城 / 关隘 / 渡口」—— 那是 geo_data 的**结构标签**（值与数据文件里的字面量
  一一对应），不是可调策略，仍留在 core/official_title.py。
"""

# ============================================================
# 一、武官（荣誉头衔）
# ============================================================
# 与行政区外官（见下方第二节）**独立**：外官是行政职位，武官是荣誉头衔。
# 一人最多一个武官（Character.military_title）。
#
# {rank: (官名, ...)}。rank 数字越小越尊贵。
MILITARY_TITLES = {
    1:  ("大将军",),
    2:  ("骠骑将军",),
    3:  ("车骑将军",),
    4:  ("卫将军",),
    5:  ("前将军",),
    6:  ("左将军",),
    7:  ("右将军",),
    8:  ("后将军",),
    9:  ("征东将军", "征南将军", "征西将军", "征北将军"),
    10: ("镇东将军", "镇南将军", "镇西将军", "镇北将军"),
    11: ("安东将军", "安南将军", "安西将军", "安北将军"),
    12: ("平东将军", "平南将军", "平西将军", "平北将军"),
    13: ("度辽将军", "伏波将军", "征虏将军"),
    14: ("虎牙将军", "横野将军", "捕虏将军", "奋威将军"),
    15: ("扬威将军", "振威将军", "建威将军", "建武将军"),
    16: ("奋武将军", "破虏将军", "讨虏将军", "荡寇将军"),
    17: ("讨逆将军", "安远将军", "平狄将军", "游击将军"),
    18: ("五官中郎将", "左中郎将", "右中郎将"),
    19: ("虎贲中郎将", "羽林中郎将", "使匈奴中郎将"),
    20: ("北中郎将", "东中郎将", "南中郎将", "西中郎将"),
    21: ("军师中郎将", "建威中郎将", "荡寇中郎将", "横野中郎将"),
    22: ("骑都尉", "奉车都尉", "驸马都尉"),
    23: ("屯骑校尉", "越骑校尉", "步兵校尉", "长水校尉", "射声校尉"),
    24: ("上军校尉", "中军校尉", "下军校尉", "典军校尉",
         "助军左校尉", "助军右校尉", "左校尉", "右校尉"),
    25: ("护乌桓校尉", "护鲜卑校尉", "护羌校尉", "戊己校尉"),
    26: ("军司马",),
    27: ("军假司马",),
    28: ("军曲候",),
    29: ("假候",),
    30: ("屯长",),
    31: ("队率",),
    32: ("什长",),
}

# 分界线：rank < UNIQUE_MAX_RANK 的官名在**同一势力内**唯一
# （同一势力里一个官名同一时刻只能属于一个人）；≥ 此值（军司马及以下）不限量。
#
# ★ 将来语义（本轮不实现，仅约定）：若两个势力分别有人物持有相同的武官
#   title（rank < UNIQUE_MAX_RANK），会导致这两个势力的外交关系严重对立。
UNIQUE_MAX_RANK = 26


# ============================================================
# 二、外官位阶（行政区分等）
# ============================================================
# 外官 rank 范围 1–32，数字越小越尊贵。
# 官名生成规则（州 / 郡 / 县 的取名后缀）见 core/official_title.py；
# 这里只放**分等 / 阈值**这类可调数据。

# --- 州级（2 位行政区 id）---
SI_STATE_ID = "07"          # 司州
SI_TITLE = "司隶校尉"        # 司州的固定官名（不走「州名 + 牧 / 刺史」规则）

RANK_SILI = 10              # 司隶校尉
RANK_MU = 11                # 州牧
RANK_CI_SHI = 12            # 州刺史

# ★ 用「州牧」而非「州刺史」的州 id 集合（其余州一律「刺史」）。
#   由剧本生成（tools/build_scenario_190.py）与「官职体系」窗口共用同一份。
MU_STATES = {"02", "08", "11", "12"}

# --- 郡级（4 位行政区 id）---
# 固定特例：脱离分数查表，直接点名（key = 郡 id）
COUNTY_RANK_FIXED = {
    "0707": 14,             # 河南尹
    "0703": 15,             # 京兆尹
}
RANK_SHUGUO_DUWEI = 21      # 属国都尉

# ★ 郡级金字塔：按分数查表（分数越高越重要，从高到低匹配，命中即止）
#   郡分数 = Σ(11 − 县.level)，县 level 1 贡献 10 分、level 10 贡献 1 分。
#   想调金字塔结构，改这张表即可。
COUNTY_RANK_THRESHOLDS = (
    (85, 16),               # 一等郡：分数 ≥ 85
    (60, 17),               # 二等郡：分数 ≥ 60
    (45, 18),               # 三等郡：分数 ≥ 45
    (28, 19),               # 四等郡：分数 ≥ 30
    (0,  20),               # 五等郡：分数 <  30
)

# --- 县级（6 位行政区 id）---
# 官名后缀：「城」按 level 分「令 / 长」，「关隘」按 level 分「都尉 / 障尉」。
CITY_LEVEL_LING = 9         # 城：level ≥ 此值用「长」，否则「令」
PASS_LEVEL_DUWEI = 6        # 关隘：level ≥ 此值用「障尉」，否则「都尉」

# 县 rank：按县 level 直接映射（城 / 关隘 / 渡口一视同仁）
CITY_RANK_BY_LEVEL = {
    1: 23, 2: 24, 3: 25, 4: 26, 5: 27, 6: 28,
    7: 29, 8: 30, 9: 31, 10: 32,
}


# ============================================================
# 三、人物五维及其能力属性
# ============================================================
# 统率 / 武力 / 智力 / 政治 / 魅力 的缺省值（字段缺失或非法时兜底）
DEFAULT_STAT = 50
# --- 根据统率值计算人物的兵力上限---
SOLDIERS_CAP_BASE_LEADERSHIP = 50      # 基准统率
SOLDIERS_CAP_BASE_FORCE      = 1000    # 基准统率对应的兵力上限
SOLDIERS_CAP_MIN_FORCE       = 200     # 兵力下限
SOLDIERS_CAP_EXPONENT        = 2.2     # 曲线陡度
def max_number_soldiers(leadership) -> int:
    """按统率给出兵力上限。"""
    L = max(1, min(100, int(leadership)))
    return max(SOLDIERS_CAP_MIN_FORCE,
               int(SOLDIERS_CAP_BASE_FORCE
                   * (L / SOLDIERS_CAP_BASE_LEADERSHIP) ** SOLDIERS_CAP_EXPONENT))


# ============================================================
# 四、势力附庸值
# ============================================================
# vassal_value 附庸值合法区间（越大越听从宗主）；独立势力恒为 0
VASSAL_VALUE_MIN = 1
VASSAL_VALUE_MAX = 99


# ============================================================
# 五、势力显示色派生参数
# ============================================================
# 显示色是**派生值**，不写回 Faction.color（详见 core/faction_color.py）。
DONGZHUO_NAME = "董卓"       # 按势力名识别（势力 id 由剧本决定，不写死）
DONGZHUO_COLOR = "#5C4033"   # 深棕，董卓的固定显示色
DEFAULT_COLOR = "#888888"    # 势力缺失 / 无色时的兜底

HUE_STEP = 5.0               # 同宗主相邻附庸的色相偏移步长（度）
MAX_HUE_SHIFT = 30.0         # 色相偏移上限，避免偏出可辨认范围

```

### game/core/military_title.py

```python
# -*- coding: utf-8 -*-
"""武官官名体系（荣誉头衔）。

★ 官名表 MILITARY_TITLES 与唯一性分界 UNIQUE_MAX_RANK 是**可调策略常量**，
  放在 game/config/rules.py；本模块只剩反查与校验逻辑。

- 与行政区外官（core/official_title.py）**独立**：外官是行政职位，武官是荣誉头衔。
- 一人最多一个武官（Character.military_title）。
- Rank 1–25（军司马之上）**势力内唯一**：同一个势力里，一个官名同一时刻
  只能属于一个人；不同势力之间**可以**有同名武官。
  ★ 将来语义（本轮不实现，仅约定）：若两个势力分别有人物持有相同的武官
    title（rank < UNIQUE_MAX_RANK），会导致这两个势力的外交关系严重对立。
- Rank 26–32（军司马及以下）不限量，同一个势力里可以有多人。
- 本轮只做常量表 + 反查，不做编辑、不进序列化。

校验接口（供将来的编辑层用）：
    is_unique(title)                    → 该官名是否属于 rank < UNIQUE_MAX_RANK
    is_title_free(world, title, faction_id, exclude_cid=None)
                                        → 该势力内该官名是否还没被占用
    is_title_free_global(world, title, exclude_cid=None)
                                        → 全剧本内该官名是否还没被占用（跨势力）

                                        
"""

from typing import Optional

# ★ 官名表与唯一性分界是**可调策略常量**，统一放在 game/config/rules.py
from game.config.rules import MILITARY_TITLES, UNIQUE_MAX_RANK


# 反查表（模块导入时构建一次）
_RANK_BY_TITLE = {}
for _r, _titles in MILITARY_TITLES.items():
    for _t in _titles:
        _RANK_BY_TITLE[_t] = _r
del _r, _titles, _t

def all_titles() -> tuple:
    """全部武官官名（按 rank 升序）。"""
    out = []
    for rank in sorted(MILITARY_TITLES):
        out.extend(MILITARY_TITLES[rank])
    return tuple(out)

def rank_of(title) -> Optional[int]:
    """官名 → rank；未知官名 → None。"""
    if not title:
        return None
    return _RANK_BY_TITLE.get(title)

def is_unique(title) -> bool:
    """该官名是否「势力内唯一」（rank < UNIQUE_MAX_RANK）。未知官名 → False。

    仅判断官名自身的性质；「在某个具体势力里是否已被占用」见 is_title_free。
    """
    r = _RANK_BY_TITLE.get(title)
    return r is not None and r < UNIQUE_MAX_RANK

def is_title_free(world, title, faction_id, exclude_cid=None) -> bool:
    """该势力内该官名是否还没被占用。

    - 官名 rank ≥ UNIQUE_MAX_RANK → 恒 True（不限量）
    - 否则遍历 world.characters，检查 faction == faction_id 的人里
      是否已有人 military_title == title（exclude_cid 用于「编辑自己时排除自己」）

    本轮不消费（编辑层落地后再用）；此处先备好接口。
    """
    if not is_unique(title):
        return True
    if world is None:
        return True
    for c in world.characters.values():
        if exclude_cid is not None and c.id == exclude_cid:
            continue
        if getattr(c, "faction", None) != faction_id:
            continue
        if getattr(c, "military_title", None) == title:
            return False
    return True

def is_title_free_global(world, title, exclude_cid=None) -> bool:
    """全剧本内该官名是否还没被占用（跨势力）。

    - 官名 rank ≥ UNIQUE_MAX_RANK → 恒 True（不限量）
    - 否则遍历 world.characters，检查是否已有人 military_title == title
      （exclude_cid 用于「编辑自己时排除自己」）

    与 is_title_free 的区别：
        is_title_free         只查同一势力内是否重复
        is_title_free_global  查全剧本（190 剧本生成期采用的口径）
    """
    if not is_unique(title):
        return True
    if world is None:
        return True
    for c in world.characters.values():
        if exclude_cid is not None and c.id == exclude_cid:
            continue
        if getattr(c, "military_title", None) == title:
            return False
    return True

def title_label(title) -> str:
    """展示用文本（当前原样返回，将来可加位阶前缀）。"""
    return title or ""
```

### game/core/character.py

```python
# -*- coding: utf-8 -*-
"""人物。

id 为四位数字字符串（"0001"–"1049"），全局唯一。

数据来源：
    静态 assets/characters.json：
        基础信息 / 五维 / 生卒年 / 相性 / 关系（id 引用）/
        个性 / 阵型 / 战法
    动态 剧本 scenarios/*.json 覆盖：
        登场 / 势力 / 所属 / 所在 / 身份

所属 vs 所在（★ 核心概念，勿混）：
    所属（node）     编制上隶属哪个据点，6 位据点 id。
                     除非归属变更，否则不变。
    所在（location） 人当前在哪个据点，6 位据点 id。
                     剧本初始 = 所属；运行时随出征 / 调动 / 流亡变化。
    两者都是据点 id，不是城池名。

武官（military_title）：
    荣誉头衔，独立于行政区外官；常量表见 core/military_title.py。
    本轮只做骨架（加载能读、内存有字段），不进 to_dict / 不参与 diff，
    保存时靠 ScenarioWriter 的 deepcopy(raw) 天然保留剧本里的原值。

五维缺省值等可调常量见 game/config/rules.py。
"""

from game.config.rules import DEFAULT_STAT


def _safe_int(v, default=0):
    """安全转 int：None / 空串 / 非法值 → default。"""
    if v is None or v == "":
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _safe_list(v):
    """安全转 list：None / 空 → []。"""
    return list(v) if v else []


class Character:
    def __init__(
        self,
        cid,
        name,
        # ---------- 基础信息 ----------
        family_name="",           # 字（表字），如「云长」
        sex="男",                 # 性别：「男」/「女」
        portrait=0,               # 头像编号（用于加载人物立绘）
        # ---------- 五维 ----------
        leadership=DEFAULT_STAT,   # 统率：带兵打仗的能力
        might=DEFAULT_STAT,        # 武力：个人武艺 / 单挑能力
        intelligence=DEFAULT_STAT, # 智力：谋略 / 计策能力
        politics=DEFAULT_STAT,     # 政治：内政 / 外交能力
        charisma=DEFAULT_STAT,     # 魅力：人格魅力 / 招揽人心
        # ---------- 时间 ----------
        appear_year=0,            # 登场年：首次出现在游戏中的年份
        birth_year=0,             # 出生年：历史出生年份
        death_year=0,             # 死亡年：历史去世年份
        # ---------- 相性 ----------
        affinity=0,               # 相性：0–149 的圆形值，决定势力间天然亲疏
        # ---------- 关系（id 引用） ----------
        blood="",                 # 血缘：家族 / 氏族标签（如「阿会喃」「袁绍」），非人名引用
        father=None,              # 父亲：人物 id，无则 None
        mother=None,              # 母亲：人物 id，无则 None
        generation=1,             # 世代：家族辈分，1 = 第一代，2 = 第二代…
        spouse=None,              # 配偶：人物 id，无则 None
        sworn_brothers=None,      # 义兄弟：人物 id 列表
        liked=None,               # 亲爱武将：人物 id 列表（关系好的人）
        disliked=None,            # 厌恶武将：人物 id 列表（关系差的人）
        # ---------- 系统字段 ----------
        start_official=0,         # 开始仕官年：0 = 未出仕；251 = 251 年（游戏起始年）
        traits=None,              # 个性：字符串列表，如 ["神眼", "疾走"]
        formations=None,          # 阵型：字符串列表，如 ["鱼鳞", "锋矢"]
        tactics=None,             # 战法：字符串列表，如 ["突击", "牵制"]
        # ---------- 剧本动态字段 ----------
        appeared=True,            # 登场：在本剧本中是否已登场（False = 未登场）
        faction=None,             # 势力 id（= 君主人物 id），None = 在野
        node=None,                # 所属：编制上隶属的据点 id（六位），None = 无所属
        location=None,            # 所在：人物当前所在地的据点 id（六位）
                                  #       初始 = 所属；运行时随出征 / 调动变化，不改所属
        role=None,                # 身份：「君主」/「一般」/「太守」等
        military_title=None,      # 武官（荣誉头衔）；见 core/military_title.py

    ):
        # ---------------- 标识 ----------------
        self.id = cid                       # 人物 id，四位字符串，如 "0147"
        self.name = name                    # 姓名，如「关羽」
        self.family_name = family_name      # 字，如「云长」
        self.sex = sex                      # 性别
        self.portrait = _safe_int(portrait, 0)   # 头像编号

        # ---------------- 五维 ----------------
        self.leadership = _safe_int(leadership, DEFAULT_STAT)       # 统率
        self.might = _safe_int(might, DEFAULT_STAT)                 # 武力
        self.intelligence = _safe_int(intelligence, DEFAULT_STAT)   # 智力
        self.politics = _safe_int(politics, DEFAULT_STAT)           # 政治
        self.charisma = _safe_int(charisma, DEFAULT_STAT)           # 魅力

        # ---------------- 时间 ----------------
        self.appear_year = _safe_int(appear_year, 0)   # 登场年
        self.birth_year = _safe_int(birth_year, 0)     # 出生年
        self.death_year = _safe_int(death_year, 0)     # 死亡年

        # ---------------- 相性 ----------------
        self.affinity = _safe_int(affinity, 0)         # 相性（0–149）

        # ---------------- 关系（id 引用） ----------------
        self.blood = blood                             # 血缘家族标签
        self.father = father                           # 父亲 id
        self.mother = mother                           # 母亲 id
        self.generation = _safe_int(generation, 1)     # 世代
        self.spouse = spouse                           # 配偶 id
        self.sworn_brothers = _safe_list(sworn_brothers)   # 义兄弟 id 列表
        self.liked = _safe_list(liked)                     # 亲爱武将 id 列表
        self.disliked = _safe_list(disliked)               # 厌恶武将 id 列表

        # ---------------- 系统字段 ----------------
        self.start_official = _safe_int(start_official, 0)   # 开始仕官年
        self.traits = _safe_list(traits)                     # 个性列表
        self.formations = _safe_list(formations)             # 阵型列表
        self.tactics = _safe_list(tactics)                   # 战法列表

        # ---------------- 剧本动态字段 ----------------
        self.appeared = bool(appeared)       # 登场：False = 未登场
        self.faction = faction               # 势力 id
        self.node = node                     # 所属（据点 id）
        self.location = location             # 所在（据点 id）
        self.role = role                     # 身份
        self.military_title = military_title # 武官（荣誉头衔）；本轮骨架

    # ============================================================
    # 语义方法
    # ============================================================
    def is_ruler(self):
        """是否为其所属势力的君主（约定：势力 id = 君主 id）。"""
        return self.faction is not None and self.faction == self.id

    def is_free(self):
        """是否在野（无所属势力）。"""
        return self.faction is None

    def is_appeared(self, year):
        """该年份是否已登场（按 appear_year 推算）。

        与剧本动态字段 appeared 并存：appeared 是剧本生成期一次算死的
        登场状态，本方法只做「appear_year <= year」的纯推算，不读 appeared。
        """
        return self.appear_year <= year

    def is_alive(self, year):
        """该年份是否健在（生卒年缺失时不作为约束）。"""
        if self.birth_year and year < self.birth_year:
            return False
        if self.death_year and year > self.death_year:
            return False
        return True

    def display_name(self):
        """带表字的展示名，如「关羽（云长）」。"""
        if self.family_name:
            return f"{self.name}（{self.family_name}）"
        return self.name

    # ============================================================
    # 工厂 / 序列化
    # ============================================================
    @classmethod
    def from_dict(cls, cid, d):
        """从 characters.json / 剧本里的一条 dict 构造。"""
        return cls(
            cid=cid,
            name=d.get("name", cid),                          # 姓名
            family_name=d.get("family_name", ""),             # 字
            sex=d.get("sex", "男"),                           # 性别
            portrait=d.get("portrait", 0),                    # 头像编号
            leadership=d.get("leadership", DEFAULT_STAT),    # 统率
            might=d.get("might", DEFAULT_STAT),              # 武力
            intelligence=d.get("intelligence", DEFAULT_STAT),# 智力
            politics=d.get("politics", DEFAULT_STAT),        # 政治
            charisma=d.get("charisma", DEFAULT_STAT),        # 魅力
            appear_year=d.get("appear_year", 0),              # 登场年
            birth_year=d.get("birth_year", 0),                # 出生年
            death_year=d.get("death_year", 0),                # 死亡年
            affinity=d.get("affinity", 0),                    # 相性
            blood=d.get("blood", ""),                         # 血缘家族
            father=d.get("father"),                           # 父亲 id
            mother=d.get("mother"),                           # 母亲 id
            generation=d.get("generation", 1),                # 世代
            spouse=d.get("spouse"),                           # 配偶 id
            sworn_brothers=d.get("sworn_brothers"),           # 义兄弟 id 列表
            liked=d.get("liked"),                             # 亲爱武将 id 列表
            disliked=d.get("disliked"),                       # 厌恶武将 id 列表
            start_official=d.get("start_official", 0),        # 开始仕官年
            traits=d.get("traits"),                           # 个性列表
            formations=d.get("formations"),                   # 阵型列表
            tactics=d.get("tactics"),                         # 战法列表
            appeared=d.get("appeared", True),                 # 登场（老剧本无此字段 → True）
            faction=d.get("faction"),                         # 势力 id
            node=d.get("node"),                               # 所属
            location=d.get("location"),                       # 所在
            role=d.get("role"),                               # 身份
            military_title=d.get("military_title"),           # 武官（老剧本无 → None）
        )

    def to_dict(self):
        """转回 dict（存档 / 调试用）。

        ★ 本轮不含 military_title：不进序列化，不参与 diff，不写回剧本。
          保存时剧本里原有的 military_title 由 ScenarioWriter 的 deepcopy(raw)
          天然保留。
        """
        return {
            "name": self.name,                                # 姓名
            "family_name": self.family_name,                  # 字
            "sex": self.sex,                                  # 性别
            "portrait": self.portrait,                        # 头像编号
            "leadership": self.leadership,                    # 统率
            "might": self.might,                              # 武力
            "intelligence": self.intelligence,                # 智力
            "politics": self.politics,                        # 政治
            "charisma": self.charisma,                        # 魅力
            "appear_year": self.appear_year,                  # 登场年
            "birth_year": self.birth_year,                    # 出生年
            "death_year": self.death_year,                    # 死亡年
            "affinity": self.affinity,                        # 相性
            "blood": self.blood,                              # 血缘家族
            "father": self.father,                            # 父亲 id
            "mother": self.mother,                            # 母亲 id
            "generation": self.generation,                    # 世代
            "spouse": self.spouse,                            # 配偶 id
            "sworn_brothers": list(self.sworn_brothers),      # 义兄弟 id 列表
            "liked": list(self.liked),                        # 亲爱武将 id 列表
            "disliked": list(self.disliked),                  # 厌恶武将 id 列表
            "start_official": self.start_official,            # 开始仕官年
            "traits": list(self.traits),                      # 个性列表
            "formations": list(self.formations),              # 阵型列表
            "tactics": list(self.tactics),                    # 战法列表
            "appeared": self.appeared,                        # 登场
            "faction": self.faction,                          # 势力 id
            "node": self.node,                                # 所属
            "location": self.location,                        # 所在
            "role": self.role,                                # 身份
        }

    def apply_override(self, data):
        """用剧本 dict 覆盖已存在的字段。

        - 只覆盖 data 中明确出现的 key
        - 本对象没有的 key 忽略（防脏数据）
        - military_title 已加入 __init__，因此 hasattr 为 True：
          剧本里显式写了 military_title 时会被加载进内存（本次改动目标之一）
        """
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self):
        return f"<Character {self.id} {self.name}>"
```

### game/ui/panels/character_panel.py

```python
# -*- coding: utf-8 -*-
"""人物面板（纯配置，玩家势力置顶）。"""

import logging
from dataclasses import dataclass
from tkinter import messagebox
from typing import Optional

from game.config.rules import max_number_soldiers

from .list.panel import GenericListPanel
from .list.columns import Column
from .list.context_menu import MenuItem

logger = logging.getLogger(__name__)

# 未登场行整行文字色（含名称列 #0）
UNAPPEARED_FG = "#888888"
ROW_TAG_UNAPPEARED = "unappeared"


@dataclass(frozen=True)
class CharacterRow:
    id: str
    name: str
    family_name: str
    sex: str
    faction_id: Optional[str]
    faction_name: str
    node_id: Optional[str]
    node_name: str
    role: Optional[str]
    appeared: bool
    leadership: int
    might: int
    intelligence: int
    politics: int
    charisma: int
    coords: Optional[tuple]
    official_text: str = ""      # ★ 外官官职（多个用「、」连接；无 → 空）
    soldiers_cap: int = 0        # ★ 兵力上限（由统率派生，见 config/rules.py）

    @property
    def display_name(self):
        if self.family_name:
            return f"{self.name}（{self.family_name}）"
        return self.name

    @classmethod
    def from_character(cls, ch, world):
        faction_name = "—"
        if ch.faction and world:
            f = world.faction(ch.faction)
            if f is not None:
                faction_name = f.name

        node_name = "—"
        coords = None
        if ch.node and world:
            n = world.node(ch.node)
            if n is not None:
                node_name = n.name
                coords = n.coords

        return cls(
            id=ch.id,
            name=ch.name,
            family_name=ch.family_name,
            sex=ch.sex,
            faction_id=ch.faction,
            faction_name=faction_name,
            node_id=ch.node,
            node_name=node_name,
            role=ch.role,
            appeared=bool(ch.appeared),
            leadership=ch.leadership,
            might=ch.might,
            intelligence=ch.intelligence,
            politics=ch.politics,
            charisma=ch.charisma,
            coords=coords,
            official_text=cls._official_text(ch, world),
            soldiers_cap=max_number_soldiers(ch.leadership),
        )

    @staticmethod
    def _official_text(ch, world):
        """该人物的全部外官官名（按行政区 id 排序，用「、」连接）；无 → 空串。"""
        if world is None:
            return ""
        return "、".join(o.get("name", "")
                         for o in world.officials_of_character(ch.id))


COLUMNS = (
    Column("faction", "势力", 60, "center", lambda r: r.faction_name),
    Column("node",    "所在", 76, "center", lambda r: r.node_name),
    Column("role",    "身份", 48, "center", lambda r: r.role or "—"),
    # 官职：外官官名（无 → 留空）。声明序在「身份」后
    Column("official", "官职", 76, "center", lambda r: r.official_text),
    Column("lead",    "统",   34, "center", lambda r: r.leadership,   sort_numeric=True),
    Column("might",   "武",   34, "center", lambda r: r.might,        sort_numeric=True),
    Column("int",     "智",   34, "center", lambda r: r.intelligence, sort_numeric=True),
    Column("pol",     "政",   34, "center", lambda r: r.politics,     sort_numeric=True),
    Column("cha",     "魅",   34, "center", lambda r: r.charisma,     sort_numeric=True),
    # 登场：显示 ✓/✗，排序按 bool（升序 = ✓ 在前）。声明序最后一位
    # 兵力上限：由统率派生的只读值（见 config/rules.py）。声明序在「登场」前
    Column("soldiers", "兵力上限", 68, "center",
           lambda r: r.soldiers_cap, sort_numeric=True),
    Column("appeared", "登场", 50, "center",
           lambda r: "✓" if r.appeared else "✗",
           sort_numeric=True,
           sort_key=lambda r: 0 if r.appeared else 1),
)

NAME_COLUMN = Column("name", "姓名", 110, "w", lambda r: r.name)

GROUP_DIMS = {
    "faction": ("势力", lambda r: r.faction_name or "在野"),
    "node":    ("所在", lambda r: r.node_name or "（无）"),
    "role":    ("身份", lambda r: r.role or "（无）"),
    "sex":     ("性别", lambda r: r.sex or "（未知）"),
    # 固定组序：已登场在前（不依赖中文字符串排序）
    "appear":  ("登场", lambda r: "已登场" if r.appeared else "未登场",
                ("已登场", "未登场")),
}


class CharacterPanel(GenericListPanel):
    PANEL_KEY = "character"
    COLUMNS = COLUMNS
    NAME_COLUMN = NAME_COLUMN
    GROUP_DIMS = GROUP_DIMS
    DEFAULT_GROUP = ("faction",)
    KEEP_VIEW_ON_EDIT = True      # ★ 登场开关后走就地刷新（保滚动 / 选中 / 展开）

    def fetch_rows(self):
        world = getattr(self.game_state, "world", None)
        if world is None:
            return []
        return [CharacterRow.from_character(c, world)
                for c in world.characters.values()]

    def row_key(self, row):
        return row.id

    # ------------------------------------------------------------
    # 行着色 / 组内排序
    # ------------------------------------------------------------
    def _configure_tags(self):
        # 未登场整行深灰（含名称列 #0）
        self.tree.tag_configure(ROW_TAG_UNAPPEARED, foreground=UNAPPEARED_FG)

    def row_tags(self, row):
        if not row.appeared:
            return (ROW_TAG_UNAPPEARED,)
        return ()

    def row_priority(self, group_keys):
        """分组含「势力」时：君主置顶 → 登场在前 → 未登场在后。

        组内子分组（如「势力 > 所在」）内同样生效——未登场后置在
        「势力 > 登场」的叶子组里是常量，不会打乱子分组。
        其他分组路径不加任何优先键。
        """
        if "faction" not in group_keys:
            return None
        return lambda r: (0 if r.faction_id == r.id else 1,
                          0 if r.appeared else 1)

    def priority_name(self):
        """玩家势力名（用于置顶）。"""
        world = getattr(self.game_state, "world", None)
        if world is None:
            return None
        pfid = getattr(world, "player_faction_id", None)
        if not pfid:
            return None
        f = world.faction(pfid)
        return f.name if f else None

    def context_menu_items(self, ctx):
        row = ctx.right_click_row
        return [
            MenuItem(row.display_name, enabled=False),
            MenuItem.sep(),
            MenuItem("编辑人物" if self.edit_session is not None else "人物情报",
                     lambda: self._open_info_window(row)),
            MenuItem("复制编号", lambda: self._copy_id(row.id)),
            MenuItem.sep(),
            # 目标状态写在标签里（符号在前），对**整个选中集**生效
            # edit=True：非编辑模式由 build_menu 统一置灰（§8.3 第 40 条）
            MenuItem("✓ 设为登场",
                     lambda: self._set_appeared(ctx.selected_rows, True),
                     edit=True),
            MenuItem("✗ 设为未登场",
                     lambda: self._set_appeared(ctx.selected_rows, False),
                     edit=True),
            MenuItem("移动到据点",
                     lambda: self._move_to_node(ctx.selected_rows), edit=True),
            MenuItem.sep(),
            MenuItem("定位到据点", lambda: self.locate_on_map(row)),
            MenuItem.sep(),
            MenuItem("全部展开", lambda: self._toggle_all(True)),
            MenuItem("全部折叠", lambda: self._toggle_all(False)),
        ]

    def _open_info_window(self, row):
        from game.ui.character_info_window import CharacterInfoWindow
        world = getattr(self.game_state, "world", None)
        if world is None:
            return
        ch = world.character(row.id)
        if ch is None:
            return
        top = self.winfo_toplevel()
        font_family = getattr(top, "font_family", "TkDefaultFont")
        logger.debug("人物情报：%s %s", ch.id, ch.name)
        # session 有值 → 窗口进入「编辑人物」形态（MODE_GAME 传 None 即只读）
        CharacterInfoWindow(self, ch, world=world, font_family=font_family,
                            session=self.edit_session,
                            on_saved=self._notify_edit)

    def _set_appeared(self, rows, target):
        """批量设为登场 / 未登场：对选中集统一设置目标状态。

        只改 appeared，**不碰** faction / node / location / role ——
        「设为登场」后仍是「在野」，「设为未登场」保留已有归属（可逆）。
        君主不能设为未登场（跳过 + 提示），其余行照常提交。
        只对状态与目标不同的行生成命令：已是目标状态的行不产生多余 dirty。
        """
        session = self.edit_session
        world = getattr(self.game_state, "world", None)
        if session is None or world is None:
            return

        candidates = list(rows)
        skipped = 0
        if target is False:
            rulers = [r for r in candidates if r.faction_id == r.id]
            if rulers:
                skipped = len(rulers)
                blocked = {id(r) for r in rulers}
                candidates = [r for r in candidates if id(r) not in blocked]
                logger.info("设为未登场跳过君主 %d 人：%s",
                            skipped, "、".join(r.name for r in rulers[:5]))
                messagebox.showwarning(
                    "君主不能设为未登场",
                    "君主必须保持登场状态。\n\n"
                    "需先解散势力，才能修改该人物的登场状态。\n\n"
                    "已跳过：%s" % "、".join(r.name for r in rulers[:5]),
                )

        from game.core.edit_commands import CharacterEditCommand
        from game.core.edit_session import CompositeCommand

        cmds = []
        for r in candidates:
            ch = world.character(r.id)
            if ch is None:
                logger.warning("人物不存在：%s", r.id)
                continue
            current = bool(ch.appeared)
            if current == target:
                continue
            cmds.append(CharacterEditCommand(
                ch.id, {"appeared": current}, {"appeared": target},
            ))

        if len(cmds) == 1:
            session.execute(cmds[0])
        elif cmds:
            session.execute(CompositeCommand(cmds, "批量设置登场"))
        logger.info("批量设置登场：命中 %d 人 / 跳过 %d 人 → %s",
                    len(cmds), skipped, target)
        if cmds:
            self._notify_edit(keep_view=True)

    def _move_to_node(self, rows):
        """移动到据点：弹窗选目标据点 → 命令变更 node / location / faction。"""
        world = getattr(self.game_state, "world", None)
        if self.edit_session is None or world is None or not rows:
            return
        logger.debug("移动到据点：人数=%d", len(rows))
        from game.ui.dialogs.move_to_node import move_characters
        if move_characters(self, world, rows, self.edit_session,
                           self._open_dialog):
            self._notify_edit(keep_view=True)

    def _copy_id(self, cid):
        try:
            self.clipboard_clear()
            self.clipboard_append(cid)
            logger.debug("复制人物编号：%s", cid)
        except Exception:
            logger.warning("复制编号失败：%s", cid, exc_info=True)

```
