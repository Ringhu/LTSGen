#!/usr/bin/env python3
"""Run a local Natural-QCC seed smoke loop over the repaired 72-row seed set.

This is a dependency-free local proxy, not a Qwen/TS-RLM training result.  It
checks whether the repaired seed data, prompts, caption targets, qcond/no-question
controls, and caption-quality metrics can run end-to-end before spending GPU time.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / ".research/general-qcc-captioner-20260515"
DEFAULT_SELF_ROWS = BASE / "self_contained_reasoning_qa_v3_20260521/self_contained_reasoning_tsqa.jsonl"
DEFAULT_CASE_ROWS = BASE / "natural_qcc_case_quality_v2_20260521/natural_qcc_case_quality_v2.jsonl"
DEFAULT_OUT_DIR = BASE / "natural_qcc_seed_smoke_v1_20260521"

TOKEN_RE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?|[A-Za-z_][A-Za-z0-9_%-]*|[\u4e00-\u9fff]")
NUM_RE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?%?")
STOPWORDS = {
    "the",
    "and",
    "or",
    "is",
    "are",
    "a",
    "an",
    "to",
    "of",
    "in",
    "for",
    "with",
    "this",
    "that",
    "these",
    "those",
    "under",
    "about",
    "from",
    "than",
    "while",
    "which",
    "into",
    "it",
    "has",
    "have",
    "be",
    "by",
    "as",
    "on",
    "at",
    "值",
    "约",
    "为",
    "是",
    "的",
    "和",
    "与",
    "在",
    "这",
    "段",
    "窗口",
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(str(text or ""))


def normalize_num(token: str) -> str:
    return token.replace(",", "").rstrip("%")


def numbers(text: str) -> list[str]:
    return [normalize_num(tok) for tok in NUM_RE.findall(str(text or ""))]


def content_tokens(text: str) -> list[str]:
    toks = [tok.lower() for tok in tokenize(text) if not NUM_RE.fullmatch(tok)]
    return [tok for tok in toks if tok not in STOPWORDS and len(tok) > 1]


def source_name(row: dict[str, Any]) -> str:
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    return str(row.get("merge_source_name") or meta.get("merge_source_name") or "unknown")


def prompt_control(row: dict[str, Any], *, no_question: bool) -> str:
    if not no_question:
        return str(row.get("prompt", ""))
    prompt = str(row.get("prompt", ""))
    prompt = re.sub(r"^Question:\s*.*$", "", prompt, flags=re.MULTILINE)
    prompt = re.sub(r"^Options:\s*.*$", "", prompt, flags=re.MULTILINE)
    prompt = re.sub(r"\n{3,}", "\n\n", prompt).strip()
    return (
        "You are a time-series evidence captioner. Given the scene and variables, "
        "write one concise generic caption about the most salient time-series pattern. "
        "Do not choose an option letter and do not answer a hidden downstream question.\n\n"
        f"{prompt}"
    ).strip()


def sft_row(row: dict[str, Any], *, no_question: bool) -> dict[str, Any]:
    meta = dict(row.get("meta") or {})
    meta.update(
        {
            "prompt_control": "no_question" if no_question else "qcond",
            "question_conditioned": not no_question,
            "merge_source_name": source_name(row),
            "task_family": row.get("task_family", ""),
            "answer": row.get("answer", ""),
            "answer_label": row.get("answer_label", ""),
        }
    )
    return {
        "id": row["id"],
        "values": row.get("values") or [],
        "prompt": prompt_control(row, no_question=no_question),
        "output": row.get("target_caption") or row.get("output") or row.get("caption_en") or "",
        "target_caption": row.get("target_caption") or row.get("output") or row.get("caption_en") or "",
        "meta": meta,
    }


def token_budget_row(row: dict[str, Any], *, max_text_length: int, max_prompt_length: int, add_eos: bool) -> dict[str, Any]:
    prompt_full = tokenize(row.get("prompt", ""))
    output_full = tokenize(row.get("output", ""))
    prompt_kept = prompt_full[:max_prompt_length]
    reserve = 1 + len(prompt_kept) + (1 if add_eos else 0)
    output_budget = max(max_text_length - reserve, 0)
    output_kept = output_full[:output_budget]
    preview = " ".join(output_kept[:40])
    return {
        "id": row.get("id", ""),
        "prompt_full_tokens": len(prompt_full),
        "prompt_kept_tokens": len(prompt_kept),
        "prompt_truncated": len(prompt_full) > len(prompt_kept),
        "output_full_tokens": len(output_full),
        "output_kept_tokens": len(output_kept),
        "output_truncated": len(output_kept) < len(output_full),
        "labels_non_ignored": len(output_kept) + (1 if add_eos else 0),
        "needed_tokens": 1 + len(prompt_full) + len(output_full) + (1 if add_eos else 0),
        "supervised_text_preview": preview,
    }


def summarize_preflight(rows: list[dict[str, Any]], *, max_text_length: int, max_prompt_length: int) -> dict[str, Any]:
    items = [
        token_budget_row(row, max_text_length=max_text_length, max_prompt_length=max_prompt_length, add_eos=True)
        for row in rows
    ]
    zero = [item for item in items if item["output_kept_tokens"] == 0]
    out_trunc = [item for item in items if item["output_truncated"]]
    prompt_trunc = [item for item in items if item["prompt_truncated"]]
    eos_only = [item for item in items if not item["supervised_text_preview"]]
    bad_phrase_counts = {
        phrase: sum(1 for row in rows if phrase.lower() in str(row.get("output", "")).lower())
        for phrase in ("Answer label", "the rule maps this to", "supports the answer")
    }
    return {
        "tokenizer": "local_regex_proxy",
        "max_text_length": max_text_length,
        "max_prompt_length": max_prompt_length,
        "n": len(rows),
        "zero_output_kept": len(zero),
        "output_truncated": len(out_trunc),
        "prompt_truncated": len(prompt_trunc),
        "eos_only_supervision": len(eos_only),
        "min_output_kept_tokens": min(item["output_kept_tokens"] for item in items) if items else 0,
        "max_needed_tokens": max(item["needed_tokens"] for item in items) if items else 0,
        "mean_prompt_tokens": round(sum(item["prompt_full_tokens"] for item in items) / len(items), 2) if items else 0.0,
        "mean_output_tokens": round(sum(item["output_full_tokens"] for item in items) / len(items), 2) if items else 0.0,
        "bad_phrase_counts": bad_phrase_counts,
        "gate_pass": not zero and not out_trunc and not prompt_trunc and not eos_only and all(v == 0 for v in bad_phrase_counts.values()),
        "examples": items[:5],
        "zero_output_examples": zero[:5],
        "output_truncated_examples": out_trunc[:5],
        "prompt_truncated_examples": prompt_trunc[:5],
    }


class MemoryCaptioner:
    def __init__(self, captions_by_id: dict[str, str] | None = None) -> None:
        self.captions_by_id = captions_by_id or {}

    def fit(self, rows: list[dict[str, Any]]) -> None:
        self.captions_by_id = {row["id"]: str(row.get("target_caption") or row.get("output") or "") for row in rows}

    def predict(self, row: dict[str, Any]) -> str:
        return self.captions_by_id.get(row["id"], "")

    def save(self, path: Path) -> None:
        write_json(path, {"model_type": "local_memory_captioner", "captions_by_id": self.captions_by_id})

    @classmethod
    def load(cls, path: Path) -> "MemoryCaptioner":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(captions_by_id={str(k): str(v) for k, v in data.get("captions_by_id", {}).items()})


def flatten_numeric_values(values: Any) -> list[list[float]]:
    rows = []
    for item in values or []:
        if isinstance(item, list):
            vals = []
            for value in item:
                try:
                    x = float(value)
                except (TypeError, ValueError):
                    continue
                if math.isfinite(x):
                    vals.append(x)
            if vals:
                rows.append(vals)
        else:
            try:
                x = float(item)
            except (TypeError, ValueError):
                continue
            if math.isfinite(x):
                rows.append([x])
    return rows


def generic_no_question_caption(row: dict[str, Any]) -> str:
    vals = flatten_numeric_values(row.get("values") or [])
    domain = source_name(row)
    if not vals:
        return f"The {domain} window is present, but no numeric compact values are available for a generic caption."
    dim = max(len(v) for v in vals)
    parts = []
    for col in range(min(dim, 3)):
        series = [v[col] for v in vals if col < len(v)]
        if not series:
            continue
        mean = sum(series) / len(series)
        parts.append(f"x{col} mean {mean:.2f}, min {min(series):.2f}, max {max(series):.2f}")
    joined = "; ".join(parts)
    return (
        f"The {domain} compact window has {len(vals)} blocks. "
        f"Generic summary: {joined}. This describes the window but does not use a downstream question."
    )


def overlap_recall(target_items: list[str], pred_items: list[str]) -> float:
    if not target_items:
        return 1.0
    pred = Counter(pred_items)
    hit = 0
    for item in target_items:
        if pred.get(item, 0) > 0:
            hit += 1
            pred[item] -= 1
    return round(hit / len(target_items), 4)


def caption_quality(pred_caption: str, target_caption: str) -> dict[str, Any]:
    stripped = pred_caption.strip()
    pred_numbers = numbers(stripped)
    target_numbers = numbers(target_caption)
    pred_words = content_tokens(stripped)
    target_words = content_tokens(target_caption)
    target_number_recall = overlap_recall(target_numbers, pred_numbers)
    target_keyword_recall = overlap_recall(target_words, pred_words)
    answer_label_only = bool(stripped and len(pred_numbers) == 0 and len(pred_words) <= 8)
    evidence_shaped = bool(stripped and len(pred_numbers) > 0 and not answer_label_only and len(stripped) >= 40)
    answer_focused = bool(target_number_recall >= 0.5 and target_keyword_recall >= 0.45)
    return {
        "non_empty": bool(stripped),
        "caption_chars": len(stripped),
        "number_count": len(pred_numbers),
        "target_number_recall": target_number_recall,
        "target_keyword_recall": target_keyword_recall,
        "answer_label_only": answer_label_only,
        "option_letter_leak": bool(re.search(r"\b(?:answer|option|choice)\s*[:=]?\s*[ABCD]\b|\b[ABCD][.)]\s", stripped, re.I)),
        "jsonish_output": stripped.startswith("{") or stripped.startswith("["),
        "too_short": len(stripped) < 40,
        "evidence_shaped": evidence_shaped,
        "answer_focused": answer_focused,
        "quality_pass": evidence_shaped and answer_focused,
    }


def prediction_row(row: dict[str, Any], pred_caption: str, condition: str) -> dict[str, Any]:
    target = str(row.get("target_caption") or row.get("output") or "")
    quality = caption_quality(pred_caption, target)
    return {
        "id": row["id"],
        "condition": condition,
        "merge_source_name": source_name(row),
        "task_family": row.get("task_family", ""),
        "target_caption": target,
        "pred_caption": pred_caption,
        "exact_target_match": pred_caption.strip() == target.strip(),
        **quality,
    }


def summarize_predictions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_domain[row["merge_source_name"]].append(row)

    def rate(key: str, items: list[dict[str, Any]]) -> float:
        return round(sum(1 for item in items if item.get(key)) / len(items), 4) if items else 0.0

    return {
        "n": len(rows),
        "non_empty_rate": rate("non_empty", rows),
        "exact_target_match_rate": rate("exact_target_match", rows),
        "evidence_shape_rate": rate("evidence_shaped", rows),
        "answer_focused_rate": rate("answer_focused", rows),
        "quality_pass_rate": rate("quality_pass", rows),
        "answer_label_only_rate": rate("answer_label_only", rows),
        "option_letter_leak_rate": rate("option_letter_leak", rows),
        "jsonish_output_rate": rate("jsonish_output", rows),
        "mean_caption_chars": round(sum(row["caption_chars"] for row in rows) / len(rows), 1) if rows else 0.0,
        "mean_target_number_recall": round(sum(row["target_number_recall"] for row in rows) / len(rows), 4) if rows else 0.0,
        "mean_target_keyword_recall": round(sum(row["target_keyword_recall"] for row in rows) / len(rows), 4) if rows else 0.0,
        "by_domain": {
            domain: {
                "n": len(items),
                "quality_pass_rate": rate("quality_pass", items),
                "answer_focused_rate": rate("answer_focused", items),
                "mean_target_number_recall": round(sum(row["target_number_recall"] for row in items) / len(items), 4),
            }
            for domain, items in sorted(by_domain.items())
        },
    }


def select_overfit_rows(rows: list[dict[str, Any]], per_domain: int = 4) -> list[dict[str, Any]]:
    selected = []
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_domain[source_name(row)].append(row)
    for domain in sorted(by_domain):
        selected.extend(sorted(by_domain[domain], key=lambda r: r["id"])[:per_domain])
    return selected


def run_overfit(rows: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    model = MemoryCaptioner()
    model.fit(rows)
    before = [prediction_row(row, model.predict(row), "overfit_before_save") for row in rows]
    model_path = out_dir / "local_memory_captioner.json"
    model.save(model_path)
    loaded = MemoryCaptioner.load(model_path)
    after = [prediction_row(row, loaded.predict(row), "overfit_after_load") for row in rows]
    write_jsonl(out_dir / "overfit_predictions_before_save.jsonl", before)
    write_jsonl(out_dir / "overfit_predictions_after_load.jsonl", after)
    before_summary = summarize_predictions(before)
    after_summary = summarize_predictions(after)
    parity = all(b["pred_caption"] == a["pred_caption"] for b, a in zip(before, after))
    report = {
        "model_type": "local_memory_captioner",
        "claim_scope": "overfit/save-load path diagnostic, not generalization",
        "n_train": len(rows),
        "model_path": rel(model_path),
        "before_save": before_summary,
        "after_load": after_summary,
        "save_load_parity": parity,
        "gate_pass": parity
        and before_summary["non_empty_rate"] == 1.0
        and before_summary["quality_pass_rate"] == 1.0
        and after_summary["quality_pass_rate"] == 1.0,
    }
    write_json(out_dir / "overfit_smoke_summary.json", report)
    return report


def run_qcond_no_question(rows: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    model = MemoryCaptioner()
    model.fit(rows)
    qcond = [prediction_row(row, model.predict(row), "qcond_local_oracle_proxy") for row in rows]
    noq = [prediction_row(row, generic_no_question_caption(row), "no_question_generic_proxy") for row in rows]
    write_jsonl(out_dir / "qcond_local_proxy_predictions.jsonl", qcond)
    write_jsonl(out_dir / "no_question_generic_proxy_predictions.jsonl", noq)
    q_summary = summarize_predictions(qcond)
    n_summary = summarize_predictions(noq)
    report = {
        "claim_scope": "local proxy control; validates evaluation chain, not Qwen SFT method performance",
        "qcond": q_summary,
        "no_question": n_summary,
        "qcond_minus_no_question_quality_pass": round(q_summary["quality_pass_rate"] - n_summary["quality_pass_rate"], 4),
        "qcond_minus_no_question_answer_focus": round(q_summary["answer_focused_rate"] - n_summary["answer_focused_rate"], 4),
        "gate_pass": q_summary["quality_pass_rate"] == 1.0 and q_summary["answer_focused_rate"] > n_summary["answer_focused_rate"],
    }
    write_json(out_dir / "qcond_vs_no_question_local_proxy_summary.json", report)
    return report


def svg_bar_chart(path: Path, title: str, bars: list[tuple[str, float, str]], *, ymax: float = 1.0) -> None:
    width, height = 820, 320
    left, top, plot_h = 70, 58, 190
    plot_w = width - left - 42
    bar_w = max(34, min(80, int(plot_w / max(1, len(bars)) * 0.55)))
    gap = (plot_w - bar_w * len(bars)) / max(1, len(bars))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="30" font-family="Arial, sans-serif" font-size="18" font-weight="700" fill="#111827">{title}</text>',
    ]
    for i in range(5):
        y = top + plot_h * i / 4
        value = ymax * (1 - i / 4)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width - 28}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="22" y="{y + 4:.1f}" font-family="Arial, sans-serif" font-size="11" fill="#6b7280">{value:.2f}</text>')
    parts.append(f'<line x1="{left}" y1="{top + plot_h}" x2="{width - 28}" y2="{top + plot_h}" stroke="#374151"/>')
    for i, (label, value, color) in enumerate(bars):
        x = left + gap / 2 + i * (bar_w + gap)
        h = plot_h * min(value, ymax) / ymax if ymax else 0
        y = top + plot_h - h
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w}" height="{h:.1f}" fill="{color}" rx="4"/>')
        parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{y - 7:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#111827">{value:.2f}</text>')
        parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{top + plot_h + 28}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#111827">{label}</text>')
    parts.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8")


def svg_flow(path: Path) -> None:
    width, height = 980, 300
    boxes = [
        (35, 88, 160, 78, "1. Preflight", "token budget\nsupervision"),
        (220, 88, 160, 78, "2. Overfit", "24-row memory\nsave/load"),
        (405, 88, 170, 78, "3. Control", "72-row qcond vs\nno-question"),
        (600, 88, 160, 78, "4. Quality", "evidence shape\nanswer focus"),
        (785, 88, 160, 78, "5. Report", "figures + audit\nnext action"),
    ]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 z" fill="#6b7280"/></marker></defs>',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="35" y="36" font-family="Arial, sans-serif" font-size="20" font-weight="700" fill="#111827">Natural-QCC local seed smoke loop</text>',
        '<text x="35" y="62" font-family="Arial, sans-serif" font-size="12" fill="#6b7280">Local proxy only: it checks the data/evaluation path before remote Qwen SFT.</text>',
    ]
    for x, y, w, h, title, body in boxes:
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#f9fafb" stroke="#d1d5db" rx="6"/>')
        parts.append(f'<text x="{x + 12}" y="{y + 25}" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#111827">{title}</text>')
        for j, line in enumerate(body.split("\\n")):
            parts.append(f'<text x="{x + 12}" y="{y + 48 + j * 15}" font-family="Arial, sans-serif" font-size="12" fill="#4b5563">{line}</text>')
    for i in range(len(boxes) - 1):
        x, y, w, h, *_ = boxes[i]
        nx, ny, *_ = boxes[i + 1]
        parts.append(f'<line x1="{x + w}" y1="{y + h / 2}" x2="{nx}" y2="{ny + h / 2}" stroke="#6b7280" stroke-width="2" marker-end="url(#arrow)"/>')
    parts.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8")


def markdown_report(
    *,
    out_dir: Path,
    rows: list[dict[str, Any]],
    preflight: dict[str, Any],
    overfit: dict[str, Any],
    compare: dict[str, Any],
    environment: dict[str, Any],
) -> str:
    q = compare["qcond"]
    n = compare["no_question"]
    lines = [
        "# Natural-QCC Seed Smoke v1（2026-05-21）",
        "",
        "## 一句话结论",
        "",
        "这轮完成的是本地小闭环 smoke：它验证 repaired seed 的监督信号、overfit/save-load 路径、qcond/no-question 对照和 caption 质量评估链路都能跑通。",
        "这不是 Qwen/TS-RLM 的正式训练结果；当前本地环境没有 `torch`、`transformers` 和远端模型目录，所以这里只能作为上 GPU 前的 local proxy gate。",
        "",
        "![Smoke flow](figures/local_smoke_flow.svg)",
        "",
        "## 1. Token / Collator Preflight",
        "",
        f"- rows: `{preflight['n']}`",
        f"- tokenizer: `{preflight['tokenizer']}`",
        f"- max_text_length / max_prompt_length: `{preflight['max_text_length']}` / `{preflight['max_prompt_length']}`",
        f"- zero output kept: `{preflight['zero_output_kept']}`",
        f"- output truncated: `{preflight['output_truncated']}`",
        f"- prompt truncated: `{preflight['prompt_truncated']}`",
        f"- EOS-only supervision: `{preflight['eos_only_supervision']}`",
        f"- gate pass: `{preflight['gate_pass']}`",
        "",
        "![Preflight](figures/token_preflight.svg)",
        "",
        "## 2. 24-row Overfit Smoke",
        "",
        "这里训练的是一个本地 memory captioner，只用于确认 overfit、保存、重载、生成和质量评估路径能闭环。",
        "",
        f"- overfit rows: `{overfit['n_train']}`",
        f"- before-save quality pass rate: `{overfit['before_save']['quality_pass_rate']}`",
        f"- after-load quality pass rate: `{overfit['after_load']['quality_pass_rate']}`",
        f"- save/load parity: `{overfit['save_load_parity']}`",
        f"- gate pass: `{overfit['gate_pass']}`",
        "",
        "![Overfit](figures/overfit_smoke.svg)",
        "",
        "## 3. 72-row qcond vs no-question Local Proxy",
        "",
        "qcond proxy 输出 answer-focused target caption；no-question proxy 只写 generic time-series summary，不看 downstream question。这个对照不是方法成绩，而是检查评估链路是否能区分 answer-focused evidence 和 generic caption。",
        "",
        "| condition | quality pass | answer focused | number recall | keyword recall |",
        "| --- | ---: | ---: | ---: | ---: |",
        f"| qcond local proxy | {q['quality_pass_rate']:.4f} | {q['answer_focused_rate']:.4f} | {q['mean_target_number_recall']:.4f} | {q['mean_target_keyword_recall']:.4f} |",
        f"| no-question generic proxy | {n['quality_pass_rate']:.4f} | {n['answer_focused_rate']:.4f} | {n['mean_target_number_recall']:.4f} | {n['mean_target_keyword_recall']:.4f} |",
        "",
        "![QCond vs No-question](figures/qcond_vs_no_question.svg)",
        "",
        "## 4. Caption Quality Gate",
        "",
        "质量 gate 同时看非空、数值证据、是否 answer-label-only、是否像 JSON/选项泄漏，以及是否覆盖 target caption 的关键数字和关键词。",
        "",
        "![Quality](figures/caption_quality.svg)",
        "",
        "## 5. 这轮产物",
        "",
        "| artifact | path |",
        "| --- | --- |",
        f"| combined qcond SFT | `{rel(out_dir / 'combined_qcond_sft.jsonl')}` |",
        f"| combined no-question SFT | `{rel(out_dir / 'combined_no_question_sft.jsonl')}` |",
        f"| preflight summary | `{rel(out_dir / 'token_preflight_summary.json')}` |",
        f"| overfit summary | `{rel(out_dir / 'overfit/overfit_smoke_summary.json')}` |",
        f"| qcond/no-question summary | `{rel(out_dir / 'qcond_vs_no_question_local_proxy_summary.json')}` |",
        f"| report | `{rel(out_dir / 'NATURAL_QCC_SEED_SMOKE_V1_REPORT_20260521_ZH.md')}` |",
        "",
        "## 环境说明",
        "",
        f"- torch available: `{environment['torch_available']}`",
        f"- transformers available: `{environment['transformers_available']}`",
        f"- model path exists: `{environment['model_path_exists']}`",
        "",
        "因此下一步真正要做的是把同一批 `combined_qcond_sft.jsonl` / `combined_no_question_sft.jsonl` 搬到 3090/A100 路径，跑真实 Qwen/TS-RLM 12-24 条 overfit 和 72 条 qcond/no-question 训练对照。",
        "",
    ]
    return "\n".join(lines)


def environment_report(model_path: Path) -> dict[str, Any]:
    try:
        import torch  # noqa: F401

        torch_available = True
    except Exception:  # noqa: BLE001
        torch_available = False
    try:
        import transformers  # noqa: F401

        transformers_available = True
    except Exception:  # noqa: BLE001
        transformers_available = False
    return {
        "torch_available": torch_available,
        "transformers_available": transformers_available,
        "model_path": str(model_path),
        "model_path_exists": model_path.exists(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self_rows", type=Path, default=DEFAULT_SELF_ROWS)
    parser.add_argument("--case_rows", type=Path, default=DEFAULT_CASE_ROWS)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--max_text_length", type=int, default=768)
    parser.add_argument("--max_prompt_length", type=int, default=640)
    parser.add_argument("--model_path", type=Path, default=Path("/cluster/home/user1/fenghaoran/model/Qwen3-4B-Instruct-2507"))
    args = parser.parse_args()

    rows = load_jsonl(args.self_rows) + load_jsonl(args.case_rows)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir = args.out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    qcond_sft = [sft_row(row, no_question=False) for row in rows]
    no_question_sft = [sft_row(row, no_question=True) for row in rows]
    write_jsonl(args.out_dir / "combined_seed_rows.jsonl", rows)
    write_jsonl(args.out_dir / "combined_qcond_sft.jsonl", qcond_sft)
    write_jsonl(args.out_dir / "combined_no_question_sft.jsonl", no_question_sft)

    preflight = summarize_preflight(qcond_sft, max_text_length=args.max_text_length, max_prompt_length=args.max_prompt_length)
    write_json(args.out_dir / "token_preflight_summary.json", preflight)

    overfit_rows = select_overfit_rows(qcond_sft, per_domain=4)
    overfit = run_overfit(overfit_rows, args.out_dir / "overfit")
    compare = run_qcond_no_question(qcond_sft, args.out_dir)
    env = environment_report(args.model_path)
    write_json(args.out_dir / "local_environment.json", env)

    svg_flow(fig_dir / "local_smoke_flow.svg")
    svg_bar_chart(
        fig_dir / "token_preflight.svg",
        "Token/collator preflight failure counts",
        [
            ("zero_output", float(preflight["zero_output_kept"]), "#dc2626"),
            ("out_trunc", float(preflight["output_truncated"]), "#f97316"),
            ("prompt_trunc", float(preflight["prompt_truncated"]), "#7c3aed"),
            ("eos_only", float(preflight["eos_only_supervision"]), "#0891b2"),
        ],
        ymax=max(1.0, float(max(preflight["zero_output_kept"], preflight["output_truncated"], preflight["prompt_truncated"], preflight["eos_only_supervision"]))),
    )
    svg_bar_chart(
        fig_dir / "overfit_smoke.svg",
        "24-row overfit smoke",
        [
            ("before quality", overfit["before_save"]["quality_pass_rate"], "#2563eb"),
            ("after quality", overfit["after_load"]["quality_pass_rate"], "#16a34a"),
            ("exact before", overfit["before_save"]["exact_target_match_rate"], "#7c3aed"),
            ("exact after", overfit["after_load"]["exact_target_match_rate"], "#f97316"),
        ],
    )
    svg_bar_chart(
        fig_dir / "qcond_vs_no_question.svg",
        "qcond vs no-question local proxy",
        [
            ("q quality", compare["qcond"]["quality_pass_rate"], "#2563eb"),
            ("nq quality", compare["no_question"]["quality_pass_rate"], "#93c5fd"),
            ("q focus", compare["qcond"]["answer_focused_rate"], "#16a34a"),
            ("nq focus", compare["no_question"]["answer_focused_rate"], "#86efac"),
        ],
    )
    svg_bar_chart(
        fig_dir / "caption_quality.svg",
        "Caption quality submetrics",
        [
            ("q num", compare["qcond"]["mean_target_number_recall"], "#2563eb"),
            ("nq num", compare["no_question"]["mean_target_number_recall"], "#93c5fd"),
            ("q kw", compare["qcond"]["mean_target_keyword_recall"], "#7c3aed"),
            ("nq kw", compare["no_question"]["mean_target_keyword_recall"], "#c4b5fd"),
        ],
    )

    report = {
        "claim_scope": "local_proxy_smoke_not_qwen_sft",
        "inputs": {"self_rows": rel(args.self_rows), "case_rows": rel(args.case_rows)},
        "outputs": {"out_dir": rel(args.out_dir)},
        "n_rows": len(rows),
        "preflight": preflight,
        "overfit": overfit,
        "qcond_vs_no_question": compare,
        "environment": env,
        "gate_pass": bool(preflight["gate_pass"] and overfit["gate_pass"] and compare["gate_pass"]),
    }
    write_json(args.out_dir / "natural_qcc_seed_smoke_v1_summary.json", report)
    md = markdown_report(
        out_dir=args.out_dir,
        rows=rows,
        preflight=preflight,
        overfit=overfit,
        compare=compare,
        environment=env,
    )
    (args.out_dir / "NATURAL_QCC_SEED_SMOKE_V1_REPORT_20260521_ZH.md").write_text(md, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["gate_pass"] else 1)


if __name__ == "__main__":
    main()
