# ts_caption/claims/lexicon_zh.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List
import random

def pick(rng: random.Random, xs: List[str]) -> str:
    return xs[rng.randrange(len(xs))] if xs else ""

@dataclass
class LexiconZH:
    # 连接词/结构词
    openers: List[str]
    then_words: List[str]
    note_words: List[str]
    end_words: List[str]
    contrast_words: List[str]
    soften_words: List[str]      # “大致/约/接近/附近/左右”
    range_words: List[str]       # “区间/范围/主要落在”

    # 趋势动词短语
    up_words: List[str]
    down_words: List[str]
    flat_words: List[str]
    fluctuate_words: List[str]
    recover_words: List[str]
    jump_down_words: List[str]
    jump_up_words: List[str]

    # 变量介绍
    intro_templates: List[str]   # 我将如何描述（宏观指令）
    vars_templates_single: List[str]    # 变量列表句式
    vars_templates_multi: List[str]    # 变量列表句式

    # 段落模板池（核心：扩充所有描述句式）
    overview_templates: List[str]
    phase_lead_templates: List[str]
    phase_templates: List[str]
    events_lead_templates: List[str]
    event_one_peak_templates: List[str]
    event_one_valley_templates: List[str]
    event_group_peak_templates: List[str]
    event_group_valley_templates: List[str]
    ending_templates: List[str]
    seasonality_has_templates: List[str]
    seasonality_none_templates: List[str]
    relations_lead_templates: List[str]
    relation_pos_templates: List[str]
    relation_neg_templates: List[str]
    relation_stable_suffix: List[str]
    relation_unstable_suffix: List[str]

def default_lexicon() -> LexiconZH:
    return LexiconZH(
        openers=[
            "整体来看", "总体而言", "从全局上看", "就整段序列而言", "先看整体走势",
            "先从大方向说起", "概括一下", "整体轮廓上", "先给一个总览",
        ],
        then_words=[
            "随后", "接着", "之后", "继而", "并且", "同时", "紧接着", "其后", "再往后", "再往下看",
        ],
        note_words=[
            "值得注意的是", "其中比较突出的点在于", "中间更显眼的是", "需要特别提到的是",
            "局部细节里", "放大到局部", "如果只看几个关键时刻", "比较醒目的事件包括",
        ],
        end_words=[
            "总体上", "归纳来说", "最后总结一下", "综合来看", "总的来说",
            "收个尾", "一句话概括", "整体可以归纳为",
        ],
        contrast_words=[
            "但", "不过", "然而", "与此同时", "相较之下", "反过来", "另一方面", "尽管如此",
        ],
        soften_words=[
            "大致", "约", "接近", "附近", "左右", "大概", "基本", "整体上", "通常", "多半",
        ],
        range_words=[
            "区间大致在", "大多落在", "主要分布在", "整体波动范围是", "多数时间处在",
            "通常围绕", "整体范围约为", "波动带主要是",
        ],

        up_words=[
            "逐步上行", "稳步抬升", "持续走高", "缓慢回升", "明显上升", "一路走高", "整体抬升", "渐渐上移",
        ],
        down_words=[
            "快速下探", "持续回落", "明显下行", "缓慢下滑", "一路走低", "明显走弱", "整体下移", "逐步走低",
        ],
        flat_words=[
            "大体平稳", "整体较为平缓", "没有明显单边趋势", "整体变化不大", "主要是震荡",
        ],
        fluctuate_words=[
            "在区间内来回波动", "呈震荡走势", "上下起伏", "波动为主", "围绕某一水平反复摆动",
            "在一个带宽里反复拉扯", "反复抖动但方向不强",
        ],
        recover_words=[
            "随后回到", "很快恢复到", "回升至", "重新回到", "回到", "拉回到", "修复到",
        ],
        jump_down_words=[
            "出现一次短促的跳水", "发生断崖式下跌", "突然下挫", "出现急跌", "瞬间跌落",
        ],
        jump_up_words=[
            "出现一次陡峭上冲", "突然拉升", "出现急涨", "短时间冲高", "瞬间抬升",
        ],

        intro_templates=[
            "{opener}，我主要描述 {target}{target_meaning_clause} 在 {t0}–{t1} 的变化，并补充关键阶段与局部事件。",
            "{opener}，下面我围绕 {target}{target_meaning_clause} 在 {t0}–{t1} 的走势做整体+局部的串讲。",
            "{opener}，我会按时间推进说明 {target}{target_meaning_clause} 的阶段变化、峰谷与震荡区间。",
            "{opener}，我将先给出全局轮廓，再把中间的关键波动段和显眼的局部点补齐。",
            "{opener}，我把这段序列拆成若干阶段来讲，并在合适位置穿插峰谷与回撤/反弹等细节。",
        ],

        # ✅ 变量介绍句式：按单变量/多变量分开，避免“其余0个变量”
        vars_templates_single=[
            "该窗口仅包含一个变量：{vars_str}。以下将围绕 {target}{target_meaning_clause} 的变化进行描述。",
            "本样本只有 {target}{target_meaning_clause} 一条序列（{vars_str}），我将重点讲它的整体走势与局部波动。",
            "这一窗口只观测到 {target}{target_meaning_clause}（{vars_str}）。下文从全局到局部概述其变化特征。",
            "变量维度为 1（{vars_str}）。我将依次说明 {target}{target_meaning_clause} 的阶段变化与关键节点。",
            "本窗口只包含 {target}{target_meaning_clause}（{vars_str}），因此描述将完全聚焦于该序列本身。",
        ],

        vars_templates_multi=[
            "该窗口包含 {n_vars} 个变量：{vars_str}。我重点关注 {target}{target_meaning_clause}，其余变量只在出现明显联动时提及。",
            "本样本记录的变量包括：{vars_str}（共 {n_vars} 个）。其中以 {target}{target_meaning_clause} 为主线展开描述。",
            "变量维度为 {n_vars}：{vars_str}。下文以 {target}{target_meaning_clause} 为主，辅以其它变量作对照。",
            "这一窗口里同时有 {n_vars} 条序列（{vars_str}）。我先讲 {target}{target_meaning_clause} 的起伏，再视情况补充其它变量的同步/反向变化。",
            "我将把 {target}{target_meaning_clause} 作为主要观察对象；其余 {n_vars_minus1} 个变量更多用于理解背景与联动：{vars_str}。",
            "该段数据涉及 {n_vars} 个观测量：{vars_str}。我会先给 {target}{target_meaning_clause} 的总览，再逐段补充细节。",
            "窗口内包含 {vars_str}。以下重点放在 {target}{target_meaning_clause}，其它变量只在关键节点处带一下。",
            "这里记录了多个指标（共 {n_vars} 个）：{vars_str}。我主要追踪 {target}{target_meaning_clause} 的走势与关键转折点。",
            "本窗口的变量集合为：{vars_str}。我以 {target}{target_meaning_clause} 为核心，描述其趋势、阶段与局部极值。",
        ],

        # ✅ overview：整体句式（多模板）
        overview_templates=[
            "{opener}，{target} 覆盖 {t0}–{t1}，开头在 {sv} 附近，结束在 {ev} 附近。",
            "{opener}，从 {t0} 到 {t1}，{target} 大体从 {sv} 走到 {ev}，整体轮廓清晰可分阶段理解。",
            "{opener}，{target} 在 {t0}–{t1} 这段时间里，起点约 {sv}，终点约 {ev}，中间伴随多次震荡与回撤。",
            "{opener}，如果只看首尾，{target} 从 {sv} 到 {ev}；但中间波动更值得展开。",
            "{opener}，这段 {target} 的整体走势可以概括为：从 {sv} 出发，经历一段波动后，最终落在 {ev} 附近。",
            "{opener}，{target} 在 {t0}–{t1} 的变化呈“阶段性推进”，首尾分别在 {sv} 与 {ev} 附近。",
            "{opener}，{target} 的主线是从 {sv} 起步并走向 {ev}，过程中穿插若干局部峰谷。",
            "{opener}，在 {t0}–{t1} 内，{target} 的整体水平由 {sv} 附近过渡到 {ev} 附近，并呈现多段震荡。",
        ],

        # ✅ phases：阶段引导 + 阶段句式（多模板）
        phase_lead_templates=[
            "分阶段看：", "按时间段展开：", "把序列拆开来讲：", "如果按阶段梳理：", "沿时间线逐段看：", "把它切成几段来看：",
        ],
        phase_templates=[
            # 模板 1：趋势 + 起止 + 区间
            "在 {ts}–{te}，{target} 主要{trend_phrase}，由 {sv} 走到 {ev}，{range_word} [{mn}, {mx}]。",
            # 模板 2：先区间再起止
            "在 {ts}–{te} 这段，{target} {range_word} [{mn}, {mx}]，整体从 {sv} 过渡到 {ev}，表现为{trend_phrase}。",
            # 模板 3：更口语
            "{ts}–{te} 这段里，{target} 基本是{trend_phrase}：从 {sv} 附近走到 {ev}，区间大概在 [{mn}, {mx}]。",
            # 模板 4：强调“先…后…/回撤/修复”用在 up/down 也可
            "在 {ts}–{te}，{target} 呈现{trend_phrase}的主导走势，期间在 [{mn}, {mx}] 之间反复摆动，最终落在 {ev} 附近。",
            # 模板 5：更像报告
            "阶段 {ts}–{te}：{target} 的主导方向为{trend_phrase}，起止值约为 {sv}→{ev}，范围约 [{mn}, {mx}]。",
        ],

        # ✅ events：事件引导 + 单事件模板（峰/谷）+ 分组模板
        events_lead_templates=[
            "局部事件方面：", "关键节点包括：", "更显眼的局部波动是：", "挑几个关键时刻看：", "值得单独拎出来的点有：",
        ],
        event_one_peak_templates=[
            "在 {t} 附近，{target} {peak_word}，到 {v} 左右。",
            "{t} 左右，{target} 一度{peak_word}至 {v} 附近。",
            "到 {t} 时，{target} 短暂{peak_word}，触到 {v} 左右后又回到区间内。",
            "{t} 附近可见一个向上“尖点”，{target} 触到 {v} 左右。",
            "在 {t} 这一点前后，{target} 明显冲高，{peak_word}到 {v} 附近。",
        ],
        event_one_valley_templates=[
            "在 {t} 附近，{target} {valley_word}，到 {v} 左右。",
            "{t} 左右，{target} 一度{valley_word}至 {v} 附近。",
            "到 {t} 时，{target} 短暂{valley_word}，落到 {v} 左右后又回到区间内。",
            "{t} 附近可见一个向下“尖点”，{target} 探到 {v} 左右。",
            "在 {t} 这一点前后，{target} 明显走弱，{valley_word}到 {v} 附近。",
        ],
        event_group_peak_templates=[
            "{target} 的几个局部高位主要出现在：{items}。",
            "{target} 在以下时刻更容易冲高：{items}。",
            "如果按时间列出较高点：{items}。",
        ],
        event_group_valley_templates=[
            "{target} 的几个局部低位主要出现在：{items}。",
            "{target} 在以下时刻更容易触底：{items}。",
            "如果按时间列出较低点：{items}。",
        ],

        # ✅ ending：收尾模板
        ending_templates=[
            "{end_word}，末段 {target} 收在 {ev} 附近，并在 [{mn}, {mx}] 的带宽里震荡。",
            "{end_word}，临近 {te} 时 {target} 仍在区间内起伏，最后落在 {ev} 左右。",
            "{end_word}，尾部没有出现持续单边，{target} 以区间震荡为主，收于 {ev} 附近。",
            "{end_word}，在最后一段时间里，{target} 基本维持在 [{mn}, {mx}] 之间，最终停在 {ev} 左右。",
            "{end_word}，整体看完后可以说：{target} 经历多段起伏后，在末段回到并维持在较高区间，最终收于 {ev} 附近。",
        ],

        # ✅ seasonality：有/无周期模板
        seasonality_has_templates=[
            "另外，序列隐约呈现重复节奏，大约每 {period} 个时间步会出现一次相似起伏。",
            "另外，{target} 的波动里能看到弱周期重复，间隔大致在 {period} 个时间步左右。",
            "此外，观察到一定周期性迹象，典型重复间隔约为 {period} 个时间步。",
            "补充一点：整体起伏里存在较弱的周期重复，尺度大约是 {period} 个时间步。",
        ],
        seasonality_none_templates=[
            "另外，未见稳定的周期重复结构。",
            "另外，整体上看不出特别稳定的周期节奏。",
            "此外，周期性并不突出，更像是非周期的震荡与阶段变化。",
        ],

        # ✅ relations：联动关系模板（只输出“同向/反向 + 稳定性”，不输出ρ/lag）
        relations_lead_templates=[
            "多变量关系上：", "就联动关系而言：", "结合其他变量来看：", "从变量联动角度：", "把其它变量一起放进来：",
        ],
        relation_pos_templates=[
            "{var} 与 {target} 的变化多半同向", "{var} 和 {target} 往往一起涨跌", "{var} 与 {target} 的走势整体较一致",
            "{var} 的起伏在不少阶段与 {target} 同步",
        ],
        relation_neg_templates=[
            "{var} 与 {target} 的变化多半反向", "{var} 上去时 {target} 往往下来", "{var} 与 {target} 经常呈相反方向",
            "{var} 的起伏在不少阶段与 {target} 相背",
        ],
        relation_stable_suffix=[
            "，且在不同阶段较为一致。", "，整体表现相对稳定。", "，在子区间里也比较一致。", "，整体一致性不错。",
        ],
        relation_unstable_suffix=[
            "，但这种关系在不同阶段并不稳定。", "，不过在不同区间一致性较弱。", "，但阶段间表现不够一致。", "，整体一致性一般。",
        ],
    )
