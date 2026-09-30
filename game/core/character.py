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
    荣誉头衔，独立于行政区外官；常量表见 config/rules.py（MILITARY_TITLES）。
    本轮只做骨架（加载能读、内存有字段），不进 to_dict / 不参与 diff，
    保存时靠 ScenarioWriter 的 deepcopy(raw) 天然保留剧本里的原值。

五维缺省值 / 兵力上限曲线常量见 game/config/rules.py。
"""

from game.config.rules import (
    DEFAULT_STAT,
    SOLDIERS_CAP_BASE_LEADERSHIP,
    SOLDIERS_CAP_BASE_FORCE,
    SOLDIERS_CAP_MIN_FORCE,
    SOLDIERS_CAP_EXPONENT,
    SOLDIERS_CAP_NO_TITLE_FACTOR,
)


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
    # 派生属性（只读，不进 to_dict / 不参与 diff）
    # ============================================================
    @staticmethod
    def compute_soldiers_cap(leadership, military_title=None) -> int:
        """纯函数：按统率 + 武官给出兵力上限。

        property（soldiers_cap）与「编辑人物」窗口的实时预览共用此逻辑，
        避免两处各写一份公式。

        曲线与系数常量见 config/rules.py：
            - SOLDIERS_CAP_BASE_LEADERSHIP / BASE_FORCE / MIN_FORCE / EXPONENT
            - MILITARY_TITLES[rank][0] 为该 rank 的系数
            - SOLDIERS_CAP_NO_TITLE_FACTOR 为无武官 / 未知 rank 的兜底系数
        """
        L = max(1, min(100, int(leadership)))
        base = (SOLDIERS_CAP_BASE_FORCE
                * (L / SOLDIERS_CAP_BASE_LEADERSHIP) ** SOLDIERS_CAP_EXPONENT)
        # 延迟 import：避免 core 模块间的导入期耦合。
        from game.core import military_title as mt
        factor = mt.factor_of_title(military_title)
        if factor is None:
            factor = SOLDIERS_CAP_NO_TITLE_FACTOR
        return max(SOLDIERS_CAP_MIN_FORCE, int(base * factor))

    @property
    def soldiers_cap(self) -> int:
        """按统率 + 武官 rank 系数给出的兵力上限（只读派生值）。

        修改 leadership 或 military_title 后自动反映（下次读取时现算）。
        """
        return self.compute_soldiers_cap(self.leadership, self.military_title)

    def job_label(self, world) -> str:
        """武官 + 外官串联的官职标签（只读派生，不进序列化）。

        规则（需求）：
            - 外官按 rank 升序（最尊贵在前）；rank 未知的排最后。
            - 无外官 → 只显示武官。
            - 无武官 → 外官直接用「、」连接，不套连接词。
            - 两者都有 → 武官与**第一个**外官之间按 rank 选连接词
              （武<外 → 领；武=外 → 兼；武>外 → 行），其余外官用「、」。
            - rank 无法判定（world 缺失 / 数据不全）→ 退化为「／」连接。
            - 两者皆无 → ""。
        """
        mil = self.military_title or ""
        offs = self._officials_with_rank(world)
        off_titles = [t for t, _r in offs]

        if not mil and not off_titles:
            return ""
        if not mil:
            return "、".join(off_titles)
        if not off_titles:
            return mil

        from game.core import military_title as mt
        mil_rank = mt.rank_of(mil)
        first_title, first_rank = offs[0]
        if mil_rank is None or first_rank is None:
            conn = "／"
        elif mil_rank < first_rank:
            conn = "、领"
        elif mil_rank == first_rank:
            conn = "、兼"
        else:
            conn = "行"
        return f"{mil}{conn}{first_title}" + \
               ("".join("、" + t for t in off_titles[1:]))

    def _officials_with_rank(self, world):
        """返回 [(官名, 数字 rank), ...]，按 rank 升序（None 排最后）。

        约定「一个人可有多个外官」——一条不命中返回 []；world 为 None → []。
        rank 不可判定时保留该条（排在末尾）。
        """
        if world is None or not getattr(world, "officials", None):
            return []
        from game.core.official_title import (
            compute_county_ranks, official_rank_of_title, city_rank_by_level,
        )
        # 郡级 rank 需要郡分数：全量扫一遍县点，缓存到 world 上。
        # 注意：编辑 node.level 后此缓存会过期；本轮只读派生，暂不主动失效
        # （与 job_system_window 构造时算一次的口径一致）。
        county_ranks = getattr(world, "_county_ranks_cache", None)
        if county_ranks is None:
            county_ranks = compute_county_ranks(world.nodes.values())
            try:
                world._county_ranks_cache = county_ranks
            except Exception:
                pass

        out = []
        for rid, item in world.officials.items():
            if item.get("character_id") != self.id:
                continue
            title = item.get("name") or ""
            if not title:
                continue
            n = len(rid or "")
            if n == 2:
                r = official_rank_of_title(title, rid)
            elif n == 4:
                r = official_rank_of_title(title, rid, county_ranks)
            elif n == 6:
                node = world.node(rid)
                r = city_rank_by_level(node.level) if node is not None else None
            else:
                r = None
            out.append((title, r))

        # rank 升序；None 排最后
        out.sort(key=lambda x: (x[1] is None, x[1] if x[1] is not None else 0))
        return out

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

        ★ military_title 已进序列化（与 appeared / faction / node / location / role 同构）。
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
            "military_title": self.military_title,            # ★ 武官（本轮进序列化）
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