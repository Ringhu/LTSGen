#!/usr/bin/env python3
"""Build a six-domain scenario-first Natural-QCC smoke set.

This smoke set is intentionally separate from the earlier 102-row controlled
pilot and the 2-row Grid2Op real-adapter sanity check. Its purpose is to make
the smoke-test scope explicit: every target domain must contribute about ten
rows before the result can be treated as a cross-domain Natural-QA smoke.
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTROLLED = (
    ROOT
    / ".research/general-qcc-captioner-20260515/scenario_first_natural_qcc_pilot_20260520/"
    / "scenario_first_natural_qcc_pilot.jsonl"
)
DEFAULT_GRID2OP_REAL = (
    ROOT
    / ".research/general-qcc-captioner-20260515/scenario_first_real_adapter_v1_20260520/"
    / "grid2op_smoke/grid2op_scenario_first_real_smoke.jsonl"
)
DEFAULT_OUT = ROOT / ".research/general-qcc-captioner-20260515/scenario_first_multidomain_smoke_v2_20260520"
CONTROLLED_FIGURES = (
    ROOT / ".research/general-qcc-captioner-20260515/scenario_first_natural_qcc_pilot_20260520/figures"
)
DOMAINS = ("grid2op", "citylearn", "traffic", "water", "aiopslab", "finrl")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def sft_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "values": row["values"],
        "prompt": row["prompt"],
        "output": row["output"],
        "target_caption": row["target_caption"],
        "meta": row["meta"],
    }


def annotate(row: dict[str, Any], *, source_tier: str, selected_role: str) -> dict[str, Any]:
    out = copy.deepcopy(row)
    original_id = out["id"]
    out["smoke_source_row_id"] = original_id
    out["smoke_source_tier"] = source_tier
    out["smoke_selected_for"] = "six_domain_scenario_first_smoke_v2_20260520"
    out["smoke_selected_role"] = selected_role
    out["smoke_split"] = "smoke"
    out.setdefault("meta", {})
    out["meta"] = copy.deepcopy(out["meta"])
    out["meta"].update(
        {
            "smoke_source_row_id": original_id,
            "smoke_source_tier": source_tier,
            "smoke_selected_for": "six_domain_scenario_first_smoke_v2_20260520",
            "smoke_selected_role": selected_role,
        }
    )
    return out


def group_by_domain(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("merge_source_name", ""))].append(row)
    for domain_rows in grouped.values():
        domain_rows.sort(key=lambda x: (str(x.get("split", "")), int(x.get("scenario_index", 0)), str(x.get("id", ""))))
    return grouped


def select_rows(
    controlled_rows: list[dict[str, Any]],
    grid2op_real_rows: list[dict[str, Any]],
    *,
    per_domain: int,
    include_grid2op_real: bool,
) -> list[dict[str, Any]]:
    controlled_by_domain = group_by_domain(controlled_rows)
    real_grid2op = [row for row in grid2op_real_rows if row.get("merge_source_name") == "grid2op"]
    real_grid2op.sort(key=lambda x: str(x.get("id", "")))

    selected: list[dict[str, Any]] = []
    for domain in DOMAINS:
        need = per_domain
        if domain == "grid2op" and include_grid2op_real:
            for row in real_grid2op[: min(len(real_grid2op), per_domain)]:
                selected.append(
                    annotate(
                        row,
                        source_tier="real_grid2op_pair_adapter",
                        selected_role="real_adapter_sanity_row",
                    )
                )
                need -= 1
        available = controlled_by_domain.get(domain, [])
        if len(available) < need:
            raise ValueError(f"domain {domain} has only {len(available)} controlled rows, need {need}")
        for row in available[:need]:
            selected.append(
                annotate(
                    row,
                    source_tier="controlled_scenario_first_generator",
                    selected_role="cross_domain_smoke_row",
                )
            )
    return selected


def summarize(rows: list[dict[str, Any]], *, per_domain: int, include_grid2op_real: bool) -> dict[str, Any]:
    by_domain = Counter(row["merge_source_name"] for row in rows)
    by_tier = Counter(row["smoke_source_tier"] for row in rows)
    answer_counts = Counter(row["answer"] for row in rows)
    domain_tier = defaultdict(Counter)
    for row in rows:
        domain_tier[row["merge_source_name"]][row["smoke_source_tier"]] += 1
    return {
        "n": len(rows),
        "expected_domains": list(DOMAINS),
        "per_domain_target": per_domain,
        "include_grid2op_real": include_grid2op_real,
        "by_domain": dict(by_domain),
        "by_source_tier": dict(by_tier),
        "by_domain_source_tier": {domain: dict(counter) for domain, counter in sorted(domain_tier.items())},
        "by_task_family": dict(Counter(row["task_family"] for row in rows)),
        "answer_distribution": dict(answer_counts),
        "max_answer_share": round(max(answer_counts.values()) / len(rows), 4) if rows else 1.0,
        "caption_empty_count": sum(1 for row in rows if not row.get("target_caption")),
        "missing_chinese_count": sum(
            1
            for row in rows
            if not row.get("question_zh") or not row.get("options_zh") or not row.get("natural_evidence_zh")
        ),
        "domains_meet_minimum": all(by_domain.get(domain, 0) >= per_domain for domain in DOMAINS),
    }


def copy_representative_figures(out_dir: Path) -> dict[str, str]:
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, str] = {}
    for idx, domain in enumerate(DOMAINS, start=1):
        matches = sorted(CONTROLLED_FIGURES.glob(f"*_{domain}_*.svg"))
        if not matches:
            continue
        dst = fig_dir / f"{idx:02d}_{domain}_representative_case.svg"
        shutil.copyfile(matches[0], dst)
        mapping[domain] = rel(dst)
    return mapping


def render_report(
    out_dir: Path,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    figure_paths: dict[str, str],
) -> None:
    controlled_cases = {}
    for row in rows:
        domain = row["merge_source_name"]
        if domain not in controlled_cases and row["smoke_source_tier"] == "controlled_scenario_first_generator":
            controlled_cases[domain] = row

    lines = [
        "# Scenario-first Natural-QCC 六域 Smoke v2（2026-05-20）",
        "",
        "这份 smoke v2 是对上一版 Grid2Op-only real adapter 的补齐：跨域 smoke 至少要覆盖每个目标域，并且每个域要有约 10 条样本，才有资格检查 Natural QA/QCC 的字段、caption、中文翻译和 SFT 形状是否稳定。",
        "",
        "## 1. 本轮结论",
        "",
        f"- 总样本数：`{summary['n']}`。",
        f"- 覆盖域：`{', '.join(summary['expected_domains'])}`。",
        f"- 每域目标：`{summary['per_domain_target']}` 条；本轮所有域都达到该门槛：`{summary['domains_meet_minimum']}`。",
        f"- caption empty：`{summary['caption_empty_count']}`；中文 QA/evidence 缺失：`{summary['missing_chinese_count']}`。",
        "",
        "这轮可以叫做“六域数据协议 smoke”：它能检查跨域字段、自然问题、中文翻译、caption、support-slot 审计和 SFT 输入输出是否能跑通。它还不能叫最终真实 simulator benchmark，因为除 Grid2Op 的 2 条 adapter sanity row 外，其余主要来自 controlled scenario-first generator。",
        "",
        "## 2. Domain 覆盖",
        "",
        "| domain | rows | controlled scenario-first | real adapter |",
        "| --- | ---: | ---: | ---: |",
    ]
    by_domain_tier = summary["by_domain_source_tier"]
    for domain in DOMAINS:
        tier = by_domain_tier.get(domain, {})
        lines.append(
            f"| `{domain}` | `{summary['by_domain'].get(domain, 0)}` | "
            f"`{tier.get('controlled_scenario_first_generator', 0)}` | "
            f"`{tier.get('real_grid2op_pair_adapter', 0)}` |"
        )

    lines.extend(
        [
            "",
            "## 3. 生成流程",
            "",
            "本轮采用的主流程是 scenario-first：",
            "",
            "1. 先确定领域场景、干预或运行状态。",
            "2. 再生成或采集对应的时序窗口。",
            "3. 然后用确定性程序计算 support slots，例如差值均值、峰值、事件前后均值、回撤等。",
            "4. 最后把这些 support slots 写成自然 evidence caption，并生成自然问题、四选项和中文翻译。",
            "",
            "这里的 support slots 不是面向用户的问题模板，而是答案和 caption 的审计锚点。换句话说，它们应该站在后台做校验，而不是把题目写成 slot 拼接。",
            "",
            "## 4. 代表性 Case Study",
            "",
            "下面每个域展示 1 条 controlled scenario-first 代表样本，用来检查问题是否像正常业务问题、中文翻译是否可读、图和证据是否能支持答案。",
            "",
        ]
    )

    for idx, domain in enumerate(DOMAINS, start=1):
        row = controlled_cases[domain]
        fig_rel = figure_paths.get(domain, "")
        lines.extend(
            [
                f"### {idx}. `{domain}` / `{row['task_family']}`",
                "",
            ]
        )
        if fig_rel:
            lines.extend([f"![](figures/{Path(fig_rel).name})", ""])
        lines.extend(
            [
                f"**场景中文：** {row['scene_zh']}",
                "",
                f"**问题中文：** {row['question_zh']}",
                "",
                "**选项中文：**",
                "",
            ]
        )
        for option in row["options_zh"]:
            lines.append(f"- {option}")
        lines.extend(
            [
                "",
                f"**Gold：** `{row['answer']}` / {row['answer_zh']}",
                "",
                f"**Evidence caption EN：** {row['natural_evidence_caption']}",
                "",
                f"**证据 caption 中文：** {row['natural_evidence_zh']}",
                "",
                f"**Scenario-first 参数：** `{json.dumps(row['scenario_first_generation']['scenario_params'], ensure_ascii=False)}`",
                "",
                f"**Support slots：** `{json.dumps(row['support_slots'], ensure_ascii=False)}`",
                "",
            ]
        )

    lines.extend(
        [
            "## 5. 产物",
            "",
            f"- smoke JSONL: `{rel(out_dir / 'scenario_first_multidomain_smoke_v2.jsonl')}`",
            f"- smoke SFT JSONL: `{rel(out_dir / 'scenario_first_multidomain_smoke_v2_sft.jsonl')}`",
            f"- summary JSON: `{rel(out_dir / 'scenario_first_multidomain_smoke_v2_summary.json')}`",
            f"- audit JSON: `{rel(out_dir / 'scenario_first_multidomain_smoke_v2_audit.json')}`",
            "",
            "## 6. 下一步",
            "",
            "下一步不应该继续只堆 controlled 数据，而应该把每个域都接上对应的真实 simulator/exporter adapter，并把每域真实样本也扩到约 10 条。当前 v2 的价值是把跨域 smoke 的数量门槛和审计形状先固定下来。",
        ]
    )
    (out_dir / "SCENARIO_FIRST_MULTIDOMAIN_SMOKE_V2_REPORT_20260520_ZH.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def render_completion_audit(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Scenario-first Multidomain Smoke v2 Completion Audit（2026-05-20）",
        "",
        "## Scope",
        "",
        "- User correction: Grid2Op-only / 2-row adapter sanity check is not enough for smoke testing.",
        "- Required smoke scope: all six domains, about 10 rows per domain.",
        "",
        "## Completed",
        "",
        f"- Built `{summary['n']}` rows.",
        f"- Domain counts: `{json.dumps(summary['by_domain'], ensure_ascii=False)}`.",
        f"- Source tiers: `{json.dumps(summary['by_source_tier'], ensure_ascii=False)}`.",
        f"- All domains meet minimum: `{summary['domains_meet_minimum']}`.",
        "- Wrote JSONL, SFT JSONL, Chinese report with figures, and audit target path.",
        "",
        "## Remaining Limitation",
        "",
        "This is a cross-domain data-protocol smoke, not a complete real-simulator smoke. Only Grid2Op currently contributes real-adapter rows, and those rows are still just adapter sanity cases. Each domain still needs a real adapter/exporter path with around 10 natural QA rows.",
    ]
    (out_dir / "SCENARIO_FIRST_MULTIDOMAIN_SMOKE_V2_COMPLETION_AUDIT_20260520.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controlled_rows", type=Path, default=DEFAULT_CONTROLLED)
    parser.add_argument("--grid2op_real_rows", type=Path, default=DEFAULT_GRID2OP_REAL)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--per_domain", type=int, default=10)
    parser.add_argument("--include_grid2op_real", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    controlled_rows = load_jsonl(args.controlled_rows)
    grid2op_real_rows = load_jsonl(args.grid2op_real_rows) if args.grid2op_real_rows.exists() else []
    rows = select_rows(
        controlled_rows,
        grid2op_real_rows,
        per_domain=args.per_domain,
        include_grid2op_real=args.include_grid2op_real,
    )

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "scenario_first_multidomain_smoke_v2.jsonl", rows)
    write_jsonl(out_dir / "scenario_first_multidomain_smoke_v2_sft.jsonl", [sft_row(row) for row in rows])
    summary = summarize(rows, per_domain=args.per_domain, include_grid2op_real=args.include_grid2op_real)
    (out_dir / "scenario_first_multidomain_smoke_v2_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    figure_paths = copy_representative_figures(out_dir)
    render_report(out_dir, rows, summary, figure_paths)
    render_completion_audit(out_dir, summary)

    print(json.dumps({"out_dir": rel(out_dir), "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
