# ts_caption/claims/renderer_zh.py
from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
import random
import hashlib
import math

from .schema import Claim
from .lexicon_zh import default_lexicon, pick

def stable_seed(*parts: Any) -> int:
    s = "|".join([str(p) for p in parts])
    h = hashlib.sha256(s.encode("utf-8")).hexdigest()
    return int(h[:8], 16)  # 32-bit

def _fmt(v: Optional[float], nd: int = 2) -> str:
    if v is None:
        return ""
    if isinstance(v, (int,)):
        return str(v)
    if not isinstance(v, (float,)):
        try:
            v = float(v)
        except Exception:
            return str(v)
    if math.isnan(v) or math.isinf(v):
        return ""
    return f"{v:.{nd}f}"

def _time_range_from_claims(claims: List[Claim]) -> Tuple[Optional[str], Optional[str]]:
    # 优先从 global_net_change / global_trend_label 找
    for t in ("global_net_change", "global_trend_label"):
        for c in claims:
            if c.type == t:
                return c.t_start, c.t_end
    # fallback: 找任何带 t_start/t_end 的
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
    # 随机决定是否带中文释义，降低“固定格式同质化”
    show_meaning = rng.random() < 0.65
    items = []
    for v in variables or []:
        name = v.get("name", "")
        meaning = v.get("meaning_zh") or ""
        if show_meaning and meaning:
            items.append(f"{name}（{meaning}）")
        else:
            items.append(f"{name}")
    # 随机分隔符风格
    sep = "、" if rng.random() < 0.7 else ", "
    return sep.join(items)

def _group_claims(claims: List[Claim]) -> Dict[str, List[Claim]]:
    g: Dict[str, List[Claim]] = {}
    for c in claims:
        g.setdefault(c.type, []).append(c)
    return g

def _pick_plan(rng: random.Random) -> List[str]:
    # 多种篇章结构：同一事实不同叙事顺序，显著降低同质化
    plans = [
        ["intro", "overview", "phases", "events", "ending", "seasonality", "relations"],
        ["intro", "events", "overview", "phases", "seasonality", "relations", "ending"],
        ["intro", "overview", "events", "phases", "relations", "seasonality", "ending"],
        ["intro", "overview", "phases", "ending", "events", "relations", "seasonality"],
        ["intro", "phases", "overview", "events", "seasonality", "ending", "relations"],
    ]
    return plans[rng.randrange(len(plans))]


def _pick_nd(rng, v: float) -> int:
    # 小随机：不同样本不同小数位，降低同质化（仍然是原始值的四舍五入）
    # 值越大越少小数
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

def _render_overview(rng, target: str, t0: str, t1: str, g) -> str:
    lex = default_lexicon()
    opener = pick(rng, lex.openers)

    net = g.get("global_net_change", [])
    if net and net[0].data:
        d = net[0].data
        sv0 = d.get("start_v"); ev0 = d.get("end_v")
        sv = _fmt(sv0, _pick_nd(rng, sv0))
        ev = _fmt(ev0, _pick_nd(rng, ev0))

        tpl = pick(rng, lex.overview_templates)
        return tpl.format(opener=opener, target=target, t0=t0, t1=t1, sv=sv, ev=ev)

    return f"{opener}，{target} 覆盖 {t0}–{t1}，整体走势如后所述。"

def _render_phases(rng, target: str, g, max_phases: int = 6) -> str:
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
        rng.shuffle(mid)
        kept.extend(mid[: max(0, max_phases - len(kept))])
        phases = sorted(kept, key=lambda c: (c.start if c.start is not None else 0))

    lead = pick(rng, lex.phase_lead_templates)
    chunks = []
    for c in phases:
        d = c.data or {}
        ts, te = c.t_start or "", c.t_end or ""

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
            # flat 更自然：震荡/平缓/上下起伏
            trend_phrase = pick(rng, lex.fluctuate_words) if rng.random() < 0.7 else pick(rng, lex.flat_words)

        tpl = pick(rng, lex.phase_templates)
        range_word = pick(rng, lex.range_words)
        chunks.append(tpl.format(
            ts=ts, te=te, target=target,
            trend_phrase=trend_phrase,
            sv=sv, ev=ev,
            mn=mn, mx=mx,
            range_word=range_word
        ))

    # 串起来：用不同连接词降低同质化
    if not chunks:
        return ""
    out = chunks[0]
    for s in chunks[1:]:
        out += " " + pick(rng, lex.then_words) + "，" + s
    return lead + out

def _render_events(rng, target: str, g, max_each: int = 3) -> str:
    lex = default_lexicon()
    peaks = sorted(g.get("peak", []), key=lambda c: (c.idx if c.idx is not None else 0))
    valleys = sorted(g.get("valley", []), key=lambda c: (c.idx if c.idx is not None else 0))
    if not peaks and not valleys:
        return ""

    lead = pick(rng, lex.events_lead_templates)

    # 两种组织方式：按时间串讲 / 先列高点再列低点
    if rng.random() < 0.55:
        all_ev = []
        for c in peaks[:max_each]:
            all_ev.append(("peak", c))
        for c in valleys[:max_each]:
            all_ev.append(("valley", c))
        all_ev.sort(key=lambda kv: (kv[1].idx if kv[1].idx is not None else 0))

        parts = []
        for kind, c in all_ev:
            d = c.data or {}
            t = c.t_idx or ""
            v0 = d.get("value")
            v = _fmt(v0, _pick_nd(rng, v0))
            if kind == "peak":
                tpl = pick(rng, lex.event_one_peak_templates)
                parts.append(tpl.format(t=t, target=target, v=v, peak_word=pick(rng, lex.up_words)))
            else:
                tpl = pick(rng, lex.event_one_valley_templates)
                parts.append(tpl.format(t=t, target=target, v=v, valley_word=pick(rng, lex.down_words)))
        return lead + " ".join(parts)

    # 先高后低（或只输出一类）
    parts = []
    if peaks:
        items = []
        for c in peaks[:max_each]:
            v0 = (c.data or {}).get("value")
            v = _fmt(v0, _pick_nd(rng, v0))
            items.append(f"{c.t_idx}≈{v}")
        parts.append(pick(rng, lex.event_group_peak_templates).format(target=target, items="；".join(items)))
    if valleys:
        items = []
        for c in valleys[:max_each]:
            v0 = (c.data or {}).get("value")
            v = _fmt(v0, _pick_nd(rng, v0))
            items.append(f"{c.t_idx}≈{v}")
        parts.append(pick(rng, lex.event_group_valley_templates).format(target=target, items="；".join(items)))
    return lead + " ".join(parts)

def _render_ending(rng, target: str, g) -> str:
    lex = default_lexicon()
    phases = sorted(g.get("phase", []), key=lambda c: (c.end if c.end is not None else -1))
    net = g.get("global_net_change", [])

    te = ""
    ev0 = None
    mn0 = None
    mx0 = None

    if phases:
        last = phases[-1]
        d = last.data or {}
        te = last.t_end or ""
        ev0 = d.get("end_v")
        mn0 = d.get("min_v")
        mx0 = d.get("max_v")
    elif net and net[0].data:
        d = net[0].data
        ev0 = d.get("end_v")

    if ev0 is None:
        return ""

    ev = _fmt(ev0, _pick_nd(rng, ev0))
    mn = _fmt(mn0, _pick_nd(rng, mn0)) if mn0 is not None else ev
    mx = _fmt(mx0, _pick_nd(rng, mx0)) if mx0 is not None else ev

    tpl = pick(rng, lex.ending_templates)
    return tpl.format(end_word=pick(rng, lex.end_words), target=target, te=te, ev=ev, mn=mn, mx=mx)

def _render_seasonality(rng, target: str, g) -> str:
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
        # 不要每条都说“无周期”，否则又同质化：只在少数样本补一句
        if rng.random() < 0.25:
            return pick(rng, lex.seasonality_none_templates)
        return ""

def _render_relations(rng, target: str, g) -> str:
    lex = default_lexicon()
    corrs = g.get("lagged_corr", [])
    if not corrs:
        return ""

    corrs = corrs[:3]
    lead = pick(rng, lex.relations_lead_templates)
    parts = []
    for c in corrs:
        d = c.data or {}
        var = d.get("var")
        corr = d.get("corr")
        stable = bool(d.get("stable"))
        if var is None or corr is None:
            continue
        try:
            corr = float(corr)
        except Exception:
            continue

        core = pick(rng, lex.relation_pos_templates) if corr >= 0 else pick(rng, lex.relation_neg_templates)
        suf = pick(rng, lex.relation_stable_suffix) if stable else pick(rng, lex.relation_unstable_suffix)
        parts.append(core.format(var=var, target=target) + suf)

    if not parts:
        return ""
    return lead + " ".join(parts)

def render_caption_zh(
    claims: List[Claim],
    variables: List[Dict[str, Any]],
    target_col: str,
    seed: Optional[int] = None,
    include_vars_intro: bool = True,
) -> str:
    """
    生成单条中文 caption（每个样本只生成 1 条），但不同样本会自动选择不同叙事结构/措辞。
    """
    t0, t1 = _time_range_from_claims(claims)
    t0 = t0 or ""
    t1 = t1 or ""

    if seed is None:
        # fallback：用时间范围+target做稳定seed（不建议，最好在 pipeline 里用 indices）
        seed = stable_seed(target_col, t0, t1)

    rng = random.Random(int(seed))
    lex = default_lexicon()
    g = _group_claims(claims)

    plan = _pick_plan(rng)

    sents: List[str] = []
    if include_vars_intro:
        vars_str = _vars_str(variables, rng)
        n_vars = len(variables or [])
        meaning = _get_target_meaning(variables, target_col)
        target_meaning_clause = f"（{meaning}）" if meaning and rng.random() < 0.6 else ""
        n_vars_minus1 = max(0, n_vars - 1)
        tpl_pool = lex.vars_templates_single if n_vars <= 1 else lex.vars_templates_multi
        sents.append(
            pick(rng, tpl_pool).format(
                vars_str=vars_str,
                target=target_col,
                n_vars=n_vars,
                n_vars_minus1=n_vars_minus1,
                target_meaning_clause=target_meaning_clause,
            )
        )

    # sections
    section_map = {
        "overview": lambda: _render_overview(rng, target_col, t0, t1, g),
        "phases": lambda: _render_phases(rng, target_col, g),
        "events": lambda: _render_events(rng, target_col, g),
        "ending": lambda: _render_ending(rng, target_col, g),
        "seasonality": lambda: _render_seasonality(rng,target_col, g),
        "relations": lambda: _render_relations(rng, target_col, g),
    }

    for sec in plan:
        if sec == "intro":
            continue
        fn = section_map.get(sec)
        if not fn:
            continue
        txt = fn()
        if txt:
            sents.append(txt)

    # 清理重复空格，合成单段
    out = " ".join([x.strip() for x in sents if x and x.strip()])
    out = out.replace("  ", " ").strip()
    return out
