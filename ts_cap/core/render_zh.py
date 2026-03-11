# ts_cap/core/render_zh.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import hashlib
import math
import random
import re

from .claims import Claim


def stable_seed(*parts: Any) -> int:
    s = "|".join([str(p) for p in parts])
    h = hashlib.sha256(s.encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def _fmt(v: Optional[float], nd: int = 2) -> str:
    """
    格式化数值：
    1. 如果是大整数（绝对值>1000 且小数位为0），显示为整数。
    2. 否则保留 nd 位小数。
    """
    if v is None:
        return ""
    try:
        val = float(v)
    except Exception:
        return str(v)
    
    if math.isnan(val) or math.isinf(val):
        return ""
    
    # 修复：大数去尾 (e.g. 387985.0 -> 387985)
    if abs(val) >= 1000 and abs(val - round(val)) < 1e-6:
        return f"{int(val)}"
        
    return f"{val:.{nd}f}"


def _simplify_time(t: str, prev_t: Optional[str] = None) -> str:
    """
    简化时间显示。修复了之前年份丢失的 Bug。
    只有在非常确定的情况下（例如同一天）才省略日期。
    """
    if not t:
        return ""
    if not prev_t:
        return t
    
    # 只有当前缀长度足够且完全匹配时，才省略
    # 1. 只有当年、月、日完全相同时，才省略前缀 (显示 HH:MM)
    # 假设格式 YYYY-MM-DD ...
    if len(t) > 10 and len(prev_t) > 10 and t[:10] == prev_t[:10]:
        return t[11:].strip()
    
    # [保守策略]：只要日期不同（哪怕是同一年），都完整显示，避免用户困惑
    # 比如 "2020-01-01" 到 "2020-04-01"，显示 "04-01" 容易让人以为是同一月。
    # 除非我们要处理的是分钟级数据，否则保留完整日期是最好的。
    
    return t


def _time_range_from_claims(claims: List[Claim]) -> Tuple[Optional[str], Optional[str]]:
    for t in ("global_net_change", "global_trend_label"):
        for c in claims:
            if c.type == t:
                return c.t_start, c.t_end
    for c in claims:
        if c.t_start and c.t_end:
            return c.t_start, c.t_end
    return None, None


def _get_target_meaning(variables: List[Dict[str, Any]], target: str) -> str:
    for v in variables or []:
        if v.get("name") == target:
            return v.get("meaning_zh") or ""
    return ""


def _vars_str(variables: List[Dict[str, Any]], rng: random.Random) -> str:
    items = []
    for v in variables or []:
        name = v.get("name", "")
        meaning = v.get("meaning_zh") or ""
        
        show_meaning = False
        if meaning and meaning != name:
            def normalize(s):
                return re.sub(r"[^\w]", "", s).lower()
            
            n_std = normalize(name)
            m_std = normalize(meaning)
            
            # [新增] 过滤掉包含 "Index ... = ..." 这种技术性定义的 Meaning
            if "index" in m_std and "100" in m_std:
                show_meaning = False
            elif n_std in m_std:
                remainder_len = len(m_std) - len(n_std)
                if remainder_len < 10 or len(name) > 15:
                    show_meaning = False
                else:
                    show_meaning = (rng.random() < 0.6)
            else:
                show_meaning = (rng.random() < 0.8)

        if show_meaning:
            items.append(f"{name}（{meaning}）")
        else:
            items.append(f"{name}")
            
    sep = "、" if rng.random() < 0.7 else ", "
    return sep.join(items)




def _group_claims(claims: List[Claim]) -> Dict[str, List[Claim]]:
    g: Dict[str, List[Claim]] = {}
    for c in claims:
        g.setdefault(c.type, []).append(c)
    return g


def _pick_nd(rng: random.Random, v: float) -> int:
    if v is None:
        return 2
    try:
        v = float(v)
    except Exception:
        return 2
    av = abs(v)
    if av >= 100:
        return 1
    if av >= 10:
        return 2 if rng.random() < 0.7 else 1
    return 2 if rng.random() < 0.6 else 3


def pick(rng: random.Random, xs: List[str]) -> str:
    return xs[rng.randrange(len(xs))] if xs else ""


@dataclass
class LexiconZH:
    openers: List[str]
    then_words: List[str]
    events_lead_templates: List[str]
    
    range_words: List[str]
    up_words: List[str]
    down_words: List[str]
    flat_words: List[str]
    fluctuate_words: List[str]

    continue_up_templates: List[str]
    continue_down_templates: List[str]

    vars_templates_single: List[str]
    vars_templates_multi: List[str]

    overview_templates: List[str]
    phase_lead_templates: List[str]
    phase_templates: List[str]
    phase_spike_templates: List[str]
    phase_dip_templates: List[str]

    event_one_peak_templates: List[str]
    event_one_valley_templates: List[str]
    event_group_peak_templates: List[str]
    event_group_valley_templates: List[str]

    ending_templates: List[str]
    seasonality_has_templates: List[str]
    seasonality_none_templates: List[str]

    relations_lead_templates: List[str]
    relation_pos_group_templates: List[str]
    relation_neg_group_templates: List[str]
    relation_mixed_templates: List[str]


def default_lexicon() -> LexiconZH:
    return LexiconZH(
        # ... (原有的 openers, then_words 等保持不变) ...
        openers=["整体来看", "总体而言", "从全局走势看", "概括一下"],
        then_words=["随后", "接着", "紧接着", "之后"],
        events_lead_templates=["关键的局部事件包括：", "值得注意的极值点有：", "局部波动方面："],
        
        range_words=["区间大致在", "主要落在", "波动范围约", "多数时间处于"],
        up_words=["稳步上行", "震荡走高", "持续抬升", "明显上涨"],
        down_words=["持续回落", "震荡下行", "一路走低", "明显下跌"],
        flat_words=["大体平稳", "变化不大", "横盘震荡"],
        fluctuate_words=["区间震荡", "来回起伏", "上下波动"],

        # [新增] 趋势延续话术
        continue_up_templates=[
            "延续了上行趋势，从 {sv} 进一步升至 {ev}。",
            "涨势未减，继续抬升至 {ev}。",
            "保持上涨态势，由 {sv} 走到 {ev}。",
        ],
        continue_down_templates=[
            "延续了下行趋势，从 {sv} 进一步跌至 {ev}。",
            "跌势未减，继续下探至 {ev}。",
            "保持下跌态势，由 {sv} 滑落至 {ev}。",
        ],

        vars_templates_single=[
            "该窗口仅包含变量 {vars_str}。以下主要描述 {target}{target_meaning_clause} 的变化。",
            "本样本为单变量序列：{target}{target_meaning_clause}。",
        ],
        vars_templates_multi=[
            "该窗口包含 {n_vars} 个变量：{vars_str}。主要关注 {target}{target_meaning_clause}。",
            "变量组包括 {vars_str}。下文重点描述 {target}{target_meaning_clause}，并分析其与其它变量的联动。",
        ],

        overview_templates=[
            "{opener}，{target} 覆盖 {t0} 至 {t1}，整体从 {sv} 变动至 {ev}。",
            "{opener}，时间跨度为 {t0}–{t1}，{target} 首尾分别为 {sv} 和 {ev}。",
        ],
        phase_lead_templates=["分阶段来看：", "沿时间线展开：", "细分来看："],
        phase_templates=[
            "{ts}–{te}，{target} 呈{trend_phrase}态势，由 {sv} 变至 {ev}。",
            "在 {ts}–{te} 期间，{target} {trend_phrase}，从 {sv} 到 {ev}。",
        ],
        phase_spike_templates=[
            "{ts}–{te}，虽然整体由 {sv} 到 {ev}，但期间一度冲高至 {mx}。",
            "在 {ts}–{te} 期间，整体趋势{trend_phrase}，但中间曾明显反弹至 {mx}。",
        ],
        phase_dip_templates=[
            "{ts}–{te}，虽然整体由 {sv} 到 {ev}，但期间一度下探至 {mn}。",
            "在 {ts}–{te} 期间，整体趋势{trend_phrase}，但中间曾深跌至 {mn}。",
        ],

        event_one_peak_templates=["{t} 左右达到局部高点 {v}。"],
        event_one_valley_templates=["{t} 左右触及局部低点 {v}。"],
        event_group_peak_templates=["几个显著高位出现在：{items}。"],
        event_group_valley_templates=["几个显著低位出现在：{items}。"],

        ending_templates=[
            "末段，{target} 收于 {ev} 附近，最后时刻在 [{mn}, {mx}] 区间内波动。",
            "临近 {te}，{target} 仍在震荡，最终落在 {ev} 左右。",
        ],

        seasonality_has_templates=[
            "此外，序列呈现约 {period} 个时间步的周期性律动。",
            "观察到明显的周期性，重复间隔约为 {period} 步。",
        ],
        seasonality_none_templates=[
            "此外，未观察到明显的周期性规律。",
        ],

        relations_lead_templates=["从变量联动角度看：", "关于变量间的相关性："],
        relation_pos_group_templates=[
            "{vars} 均与 {target} 呈现较强的**正相关**，走势较为同步。",
            "{vars} 和 {target} 的变化多半同向。",
        ],
        relation_neg_group_templates=[
            "{vars} 与 {target} 呈现**负相关**，往往此消彼长。",
            "{vars} 和 {target} 的走势多半相反。",
        ],
        relation_mixed_templates=[
            "{var} 与 {target} 存在一定相关性（{rel}），但并不稳定。",
        ],
    )

def _render_overview(rng: random.Random, target: str, t0: str, t1: str, g: Dict[str, List[Claim]]) -> str:
    lex = default_lexicon()
    opener = pick(rng, lex.openers)
    net = g.get("global_net_change", [])
    
    sv, ev = "", ""
    if net and net[0].data:
        d = net[0].data
        sv0 = d.get("start_v")
        ev0 = d.get("end_v")
        sv = _fmt(sv0, _pick_nd(rng, sv0))
        ev = _fmt(ev0, _pick_nd(rng, ev0))
    
    tpl = pick(rng, lex.overview_templates)
    return tpl.format(opener=opener, target=target, t0=t0, t1=t1, sv=sv, ev=ev)


def _render_phases(rng: random.Random, target: str, g: Dict[str, List[Claim]], max_phases: int = 5) -> str:
    lex = default_lexicon()
    phases = g.get("phase", [])
    if not phases:
        return ""

    phases = sorted(phases, key=lambda c: (c.start if c.start is not None else 0))
    if len(phases) > max_phases:
        kept = []
        kept.extend(phases[:2])
        kept.extend(phases[-2:])
        mid = phases[2:-2]
        if mid:
            step = max(1, len(mid) // (max_phases - 4 + 1))
            kept[2:2] = mid[::step]
        phases = sorted(kept, key=lambda c: (c.start if c.start is not None else 0))

    lead = pick(rng, lex.phase_lead_templates)
    chunks = []
    
    prev_label = None # [新增] 记录上一段的趋势

    for i, c in enumerate(phases):
        d = c.data or {}
        
        ts_raw = c.t_start or ""
        te_raw = c.t_end or ""
        ts = ts_raw 
        te = _simplify_time(te_raw, ts_raw) 

        sv0, ev0 = d.get("start_v"), d.get("end_v")
        mn0, mx0 = d.get("min_v"), d.get("max_v")
        
        sv = _fmt(sv0, _pick_nd(rng, sv0))
        ev = _fmt(ev0, _pick_nd(rng, ev0))
        mn = _fmt(mn0, _pick_nd(rng, mn0))
        mx = _fmt(mx0, _pick_nd(rng, mx0))

        lab = (d.get("label") or "").lower()
        if lab == "up":
            trend_phrase = pick(rng, lex.up_words)
        elif lab == "down":
            trend_phrase = pick(rng, lex.down_words)
        else:
            trend_phrase = pick(rng, lex.flat_words)

        is_spike = False
        is_dip = False
        
        if sv0 is not None and ev0 is not None:
            span = abs(ev0 - sv0)
            base_min = min(sv0, ev0)
            base_max = max(sv0, ev0)
            thr = max(span * 1.5, abs(sv0)*0.05) 
            
            if mx0 is not None and mx0 > base_max + thr:
                is_spike = True
            if mn0 is not None and mn0 < base_min - thr:
                is_dip = True

        # [新增] 连续性检测逻辑
        phrase = ""
        # 只有当非突刺/非深蹲，且趋势与上一段完全一致时，才使用“延续”句式
        if i > 0 and not is_spike and not is_dip and lab == prev_label:
            if lab == "up":
                phrase = pick(rng, lex.continue_up_templates).format(sv=sv, ev=ev)
            elif lab == "down":
                phrase = pick(rng, lex.continue_down_templates).format(sv=sv, ev=ev)
            else:
                # 震荡延续
                phrase = f"继续保持震荡，区间在 [{mn}, {mx}]。"
            
            # 加上时间状语
            phrase = f"{ts}–{te}，{phrase}"
        else:
            # 常规逻辑
            if is_dip:
                tpl = pick(rng, lex.phase_dip_templates)
            elif is_spike:
                tpl = pick(rng, lex.phase_spike_templates)
            else:
                tpl = pick(rng, lex.phase_templates)

            phrase = tpl.format(
                ts=ts, te=te, target=target, 
                trend_phrase=trend_phrase, 
                sv=sv, ev=ev, mn=mn, mx=mx
            )
        
        chunks.append(phrase)
        prev_label = lab # 更新 label

    if not chunks:
        return ""
        
    out = chunks[0]
    for i in range(1, len(chunks)):
        conn = pick(rng, lex.then_words)
        out += f" {conn}，{chunks[i]}"
        
    return lead + out

def _render_events(rng: random.Random, target: str, g: Dict[str, List[Claim]], max_each: int = 3) -> str:
    lex = default_lexicon()
    peaks = sorted(g.get("peak", []), key=lambda c: -abs(float((c.data or {}).get("z", 0))))
    valleys = sorted(g.get("valley", []), key=lambda c: -abs(float((c.data or {}).get("z", 0))))
    
    if not peaks and not valleys:
        return ""

    lead = pick(rng, lex.events_lead_templates)
    parts = []
    
    def fmt_ev(c):
        d = c.data or {}
        # 事件时间点也简化一下，如果年月日一致
        t = _simplify_time(c.t_idx or "")
        # 如果简化到空了（罕见），退回 t_idx
        if not t: t = c.t_idx
        v = _fmt(d.get("value"))
        return f"{t}≈{v}"

    if peaks:
        top_p = peaks[:max_each]
        top_p.sort(key=lambda c: c.idx if c.idx else 0)
        items = "；".join([fmt_ev(c) for c in top_p])
        parts.append(pick(rng, lex.event_group_peak_templates).format(target=target, items=items))

    if valleys:
        top_v = valleys[:max_each]
        top_v.sort(key=lambda c: c.idx if c.idx else 0)
        items = "；".join([fmt_ev(c) for c in top_v])
        parts.append(pick(rng, lex.event_group_valley_templates).format(target=target, items=items))

    return lead + " ".join(parts)


def _render_relations(rng: random.Random, target: str, g: Dict[str, List[Claim]]) -> str:
    lex = default_lexicon()
    corrs = g.get("lagged_corr", [])
    if not corrs:
        return ""

    pos_stable = []
    neg_stable = []
    others = []

    for c in corrs:
        d = c.data or {}
        var = d.get("var")
        if not var: continue
        
        corr = float(d.get("corr", 0.0))
        stable = bool(d.get("stable", False))
        
        if stable:
            if corr > 0:
                pos_stable.append(var)
            else:
                neg_stable.append(var)
        else:
            others.append((var, "正" if corr>0 else "负"))

    parts = []
    
    if pos_stable:
        vars_str = "、".join(pos_stable)
        tpl = pick(rng, lex.relation_pos_group_templates)
        parts.append(tpl.format(vars=vars_str, target=target))
        
    if neg_stable:
        vars_str = "、".join(neg_stable)
        tpl = pick(rng, lex.relation_neg_group_templates)
        parts.append(tpl.format(vars=vars_str, target=target))
        
    if others and (len(parts) == 0 or rng.random() < 0.3):
        v, rel = others[0]
        tpl = pick(rng, lex.relation_mixed_templates)
        parts.append(tpl.format(var=v, target=target, rel=rel))

    if not parts:
        return ""
        
    lead = pick(rng, lex.relations_lead_templates)
    return lead + " ".join(parts)


def _render_seasonality(rng: random.Random, target: str, g: Dict[str, List[Claim]]) -> str:
    lex = default_lexicon()
    seas = g.get("seasonality", [])
    if not seas or not seas[0].data:
        return ""
    d = seas[0].data
    has = bool(d.get("has"))
    period = d.get("period")

    if has and period:
        tpl = pick(rng, lex.seasonality_has_templates)
        return tpl.format(target=target, period=int(period))
    else:
        if rng.random() < 0.3:
            return pick(rng, lex.seasonality_none_templates)
        return ""


def _render_ending(rng: random.Random, target: str, g: Dict[str, List[Claim]]) -> str:
    lex = default_lexicon()
    net = g.get("global_net_change", [])
    if not net:
        return ""
    d = net[0].data
    ev = _fmt(d.get("end_v"))
    te = net[0].t_end or "末尾"
    te = _simplify_time(te) # simplify
    
    phases = g.get("phase", [])
    mn, mx = ev, ev
    if phases:
        last_ph = phases[-1]
        if last_ph.data:
            mn = _fmt(last_ph.data.get("min_v"))
            mx = _fmt(last_ph.data.get("max_v"))

    tpl = pick(rng, lex.ending_templates)
    return tpl.format(target=target, te=te, ev=ev, mn=mn, mx=mx)


def render_caption_zh(
    claims: List[Claim],
    variables: List[Dict[str, Any]],
    target_col: str,
    seed: Optional[int] = None,
) -> str:
    t0, t1 = _time_range_from_claims(claims)
    t0 = t0 or ""
    t1 = t1 or ""
    if seed is None:
        seed = stable_seed(target_col, t0, t1)

    rng = random.Random(int(seed))
    lex = default_lexicon()
    g = _group_claims(claims)

    sents: List[str] = []
    
    # 1. Intro
    vars_str = _vars_str(variables, rng)
    n_vars = len(variables or [])
    meaning = _get_target_meaning(variables, target_col)
    
    # 修复：只有当 meaning 有效且不啰嗦时才显示
    target_meaning_clause = ""
    if meaning and meaning != target_col:
        # 如果 meaning 包含 target_col 且长度差距不大，视为重复，不显示
        if target_col in meaning and len(meaning) < len(target_col) + 10:
            pass
        elif rng.random() < 0.7:
            target_meaning_clause = f"（{meaning}）"
    
    tpl_pool = lex.vars_templates_single if n_vars <= 1 else lex.vars_templates_multi
    sents.append(
        pick(rng, tpl_pool).format(
            vars_str=vars_str,
            target=target_col,
            n_vars=n_vars,
            target_meaning_clause=target_meaning_clause,
        )
    )

    # 2. Overview
    sents.append(_render_overview(rng, target_col, t0, t1, g))

    # 3. Phases
    sents.append(_render_phases(rng, target_col, g))

    # 4. Events
    sents.append(_render_events(rng, target_col, g))

    # 5. Correlations
    rel_txt = _render_relations(rng, target_col, g)
    if rel_txt: sents.append(rel_txt)

    # 6. Seasonality
    seas_txt = _render_seasonality(rng, target_col, g)
    if seas_txt: sents.append(seas_txt)

    # 7. Ending
    if rng.random() < 0.5:
        sents.append(_render_ending(rng, target_col, g))

    out = " ".join([x.strip() for x in sents if x and x.strip()])
    out = out.replace("。。", "。").replace("  ", " ")
    return out