# -*- coding: utf-8 -*-
"""人物。

id 为四位数字字符串（"0001"–"1049"），全局唯一。

数据来源：
    静态 assets/characters.json：
        基础信息 / 五维 / 生卒年 / 相性 / 关系（id 引用）/
        个性 / 阵型 / 战法
    动态 剧本 scenarios/*.json 覆盖：
        势力 / 据点 / 所在 / 所属 / 身份
"""

_DEFAULT_STAT = 50   # 五维缺省值


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
        leadership=_DEFAULT_STAT,   # 统率：带兵打仗的能力
        might=_DEFAULT_STAT,        # 武力：个人武艺 / 单挑能力
        intelligence=_DEFAULT_STAT, # 智力：谋略 / 计策能力
        politics=_DEFAULT_STAT,     # 政治：内政 / 外交能力
        charisma=_DEFAULT_STAT,     # 魅力：人格魅力 / 招揽人心
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
        faction=None,             # 势力 id（= 君主人物 id），None = 在野
        node=None,                # 据点 id（六位），None = 无所属据点
        location_name=None,       # 所在：城池名（原始表里的文本，供调试 / 展示）
        affiliation=None,         # 所属：所属城池名（原始表里的文本）
        role=None,                # 身份：「君主」/「一般」/「太守」/「未发现」等
    ):
        # ---------------- 标识 ----------------
        self.id = cid                       # 人物 id，四位字符串，如 "0147"
        self.name = name                    # 姓名，如「关羽」
        self.family_name = family_name      # 字，如「云长」
        self.sex = sex                      # 性别
        self.portrait = _safe_int(portrait, 0)   # 头像编号

        # ---------------- 五维 ----------------
        self.leadership = _safe_int(leadership, _DEFAULT_STAT)       # 统率
        self.might = _safe_int(might, _DEFAULT_STAT)                 # 武力
        self.intelligence = _safe_int(intelligence, _DEFAULT_STAT)   # 智力
        self.politics = _safe_int(politics, _DEFAULT_STAT)           # 政治
        self.charisma = _safe_int(charisma, _DEFAULT_STAT)           # 魅力

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
        self.faction = faction               # 势力 id
        self.node = node                     # 据点 id
        self.location_name = location_name   # 所在城池名
        self.affiliation = affiliation       # 所属城池名
        self.role = role                     # 身份

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
        """该年份是否已登场。"""
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
        """从 characters.json 里的一条 dict 构造。"""
        return cls(
            cid=cid,
            name=d.get("name", cid),                          # 姓名
            family_name=d.get("family_name", ""),             # 字
            sex=d.get("sex", "男"),                           # 性别
            portrait=d.get("portrait", 0),                    # 头像编号
            leadership=d.get("leadership", _DEFAULT_STAT),    # 统率
            might=d.get("might", _DEFAULT_STAT),              # 武力
            intelligence=d.get("intelligence", _DEFAULT_STAT),# 智力
            politics=d.get("politics", _DEFAULT_STAT),        # 政治
            charisma=d.get("charisma", _DEFAULT_STAT),        # 魅力
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
            faction=d.get("faction"),                         # 势力 id
            node=d.get("node"),                               # 据点 id
            location_name=d.get("location_name"),             # 所在
            affiliation=d.get("affiliation"),                 # 所属
            role=d.get("role"),                               # 身份
        )

    def to_dict(self):
        """转回 dict（存档 / 调试用）。"""
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
            "faction": self.faction,                          # 势力 id
            "node": self.node,                                # 据点 id
            "location_name": self.location_name,              # 所在
            "affiliation": self.affiliation,                  # 所属
            "role": self.role,                                # 身份
        }

    def apply_override(self, data):
        """用剧本 dict 覆盖已存在的字段。

        - 只覆盖 data 中明确出现的 key
        - 本对象没有的 key 忽略（防脏数据）
        """
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self):
        return f"<Character {self.id} {self.name}>"