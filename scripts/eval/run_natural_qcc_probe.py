#!/usr/bin/env python3
"""Run baseline QA and a lightweight trainable caption probe on natural QCC data.

This is a small, dependency-free pilot for the reviewed natural balanced8 set.
It does not replace GPU QCC training; it checks whether the new data construction
can be evaluated as evidence captions and whether a train/eval caption interface
can be exercised before scaling to a larger reviewer-positive pool.
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
DEFAULT_DATA = (
    ROOT
    / ".research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/"
    / "natural_qcc_probe_positive.jsonl"
)
DEFAULT_OUT_DIR = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/probe_eval"

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def option_pairs(row: dict[str, Any]) -> list[tuple[str, str]]:
    pairs = []
    for option in row.get("options", []):
        if ". " not in option:
            continue
        letter, label = option.split(". ", 1)
        pairs.append((letter.strip(), label.strip()))
    return pairs


def answer_from_caption(row: dict[str, Any], caption: str) -> tuple[str, str, str]:
    text = normalize(caption)
    answer_label_match = re.search(r"answer label:\s*([^.;]+)", caption, flags=re.IGNORECASE)
    if answer_label_match:
        label_text = answer_label_match.group(1).strip()
        for letter, label in option_pairs(row):
            if normalize(label) == normalize(label_text):
                return letter, label, "explicit_answer_label"
        if normalize(str(row.get("answer_label", ""))) == normalize(label_text):
            return str(row.get("answer", "")), str(row.get("answer_label", "")), "explicit_gold_answer_label"
    pairs = option_pairs(row)
    for letter, label in sorted(pairs, key=lambda item: len(item[1]), reverse=True):
        if normalize(label) in text:
            return letter, label, "option_label_text"
    gold = normalize(str(row.get("answer_label", "")))
    if gold and gold in text:
        return str(row.get("answer", "")), str(row.get("answer_label", "")), "gold_label_text"
    return "", "", "no_label_match"


def caption_for_condition(row: dict[str, Any], condition: str) -> str:
    if condition == "natural_oracle":
        return str(row.get("oracle_evidence_caption", ""))
    if condition == "natural_evidence_no_label":
        return str(row.get("natural_evidence_caption", ""))
    if condition == "generic_caption":
        return str(row.get("generic_caption", ""))
    if condition == "statistical_caption":
        return str(row.get("statistical_caption", ""))
    if condition == "question_only":
        return str(row.get("question", ""))
    raise ValueError(condition)


def summarize_predictions(preds: list[dict[str, Any]]) -> dict[str, Any]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pred in preds:
        by_source[pred["source"]].append(pred)
        by_split[pred["split"]].append(pred)
        by_task[pred["task_family"]].append(pred)

    def acc(items: list[dict[str, Any]]) -> float:
        return round(sum(1 for item in items if item["correct"]) / len(items), 4) if items else 0.0

    return {
        "n": len(preds),
        "accuracy": acc(preds),
        "empty_answer_rate": round(sum(1 for item in preds if not item["pred_answer"]) / len(preds), 4) if preds else 0.0,
        "mean_caption_chars": round(sum(len(item["caption"]) for item in preds) / len(preds), 1) if preds else 0.0,
        "by_source": {
            key: {"n": len(items), "accuracy": acc(items), "empty_answer_rate": round(sum(1 for item in items if not item["pred_answer"]) / len(items), 4)}
            for key, items in sorted(by_source.items())
        },
        "by_split": {key: {"n": len(items), "accuracy": acc(items)} for key, items in sorted(by_split.items())},
        "by_task_family": {key: {"n": len(items), "accuracy": acc(items)} for key, items in sorted(by_task.items())},
        "pred_answer_distribution": dict(Counter(item["pred_answer"] or "EMPTY" for item in preds)),
        "reason_distribution": dict(Counter(item["qa_reason"] for item in preds)),
    }


def evaluate_condition(rows: list[dict[str, Any]], condition: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    preds = []
    for row in rows:
        caption = caption_for_condition(row, condition)
        pred_answer, pred_label, reason = answer_from_caption(row, caption)
        preds.append(
            {
                "id": row["id"],
                "split": row.get("split", ""),
                "source": row.get("merge_source_name", ""),
                "task_family": row["task_family"],
                "condition": condition,
                "caption": caption,
                "pred_answer": pred_answer,
                "pred_answer_label": pred_label,
                "gold_answer": row["answer"],
                "gold_answer_label": row["answer_label"],
                "correct": pred_answer == row["answer"],
                "qa_reason": reason,
            }
        )
    return preds, summarize_predictions(preds)


def numeric_features(row: dict[str, Any]) -> dict[str, float]:
    values = row.get("raw_compact_values") or row.get("values") or []
    if not values:
        return {}
    n = len(values)
    width = max(len(item) for item in values)
    feats: dict[str, float] = {"horizon": float(n), "num_vars": float(width)}
    for j in range(min(width, 4)):
        col = []
        for item in values:
            try:
                value = float(item[j])
            except (IndexError, TypeError, ValueError):
                value = 0.0
            if not math.isfinite(value):
                value = 0.0
            col.append(value)
        mean = sum(col) / len(col)
        var = sum((value - mean) ** 2 for value in col) / len(col)
        feats[f"x{j}_start"] = col[0]
        feats[f"x{j}_end"] = col[-1]
        feats[f"x{j}_delta"] = col[-1] - col[0]
        feats[f"x{j}_mean"] = mean
        feats[f"x{j}_std"] = math.sqrt(var)
        feats[f"x{j}_min"] = min(col)
        feats[f"x{j}_max"] = max(col)
        thirds = [col[: n // 3], col[n // 3 : 2 * n // 3], col[2 * n // 3 :]]
        for idx, part in enumerate(thirds):
            if part:
                pmean = sum(part) / len(part)
                pvar = sum((value - pmean) ** 2 for value in part) / len(part)
                feats[f"x{j}_seg{idx}_mean"] = pmean
                feats[f"x{j}_seg{idx}_std"] = math.sqrt(pvar)
    return feats


def text_features(row: dict[str, Any], *, no_question: bool) -> dict[str, float]:
    feats = {
        f"source={row.get('merge_source_name', '')}": 1.0,
        f"task={row.get('task_family', '')}": 1.0,
    }
    if not no_question:
        text = f"{row.get('scene_en', '')} {row.get('question', '')}"
        for token in TOKEN_RE.findall(text.lower()):
            feats[f"tok={token}"] = feats.get(f"tok={token}", 0.0) + 1.0
    return feats


def featurize(row: dict[str, Any], *, no_question: bool) -> dict[str, float]:
    feats = numeric_features(row)
    feats.update(text_features(row, no_question=no_question))
    return feats


def fit_scaler(train_feats: list[dict[str, float]]) -> tuple[dict[str, float], dict[str, float]]:
    keys = sorted({key for feats in train_feats for key in feats})
    means: dict[str, float] = {}
    scales: dict[str, float] = {}
    for key in keys:
        values = [feats.get(key, 0.0) for feats in train_feats]
        mean = sum(values) / len(values)
        var = sum((value - mean) ** 2 for value in values) / len(values)
        means[key] = mean
        scales[key] = math.sqrt(var) or 1.0
    return means, scales


def distance(a: dict[str, float], b: dict[str, float], means: dict[str, float], scales: dict[str, float]) -> float:
    keys = set(a) | set(b) | set(means)
    total = 0.0
    for key in keys:
        scale = scales.get(key, 1.0)
        av = (a.get(key, 0.0) - means.get(key, 0.0)) / scale
        bv = (b.get(key, 0.0) - means.get(key, 0.0)) / scale
        total += (av - bv) ** 2
    return math.sqrt(total)


def substitute_label(caption: str, old_label: str, new_label: str) -> str:
    if normalize(old_label) == normalize(new_label):
        return caption
    pattern = re.compile(re.escape(old_label), flags=re.IGNORECASE)
    if pattern.search(caption):
        return pattern.sub(new_label, caption, count=1)
    return f"{caption} Predicted answer label: {new_label}."


def nearest_caption(train_rows: list[dict[str, Any]], eval_row: dict[str, Any], *, no_question: bool) -> tuple[str, str, str, float]:
    train_feats = [featurize(row, no_question=no_question) for row in train_rows]
    means, scales = fit_scaler(train_feats)
    eval_feats = featurize(eval_row, no_question=no_question)
    best_idx = min(
        range(len(train_rows)),
        key=lambda idx: distance(train_feats[idx], eval_feats, means, scales),
    )
    neighbor = train_rows[best_idx]
    label = str(neighbor["answer_label"])
    if label not in {option_label for _, option_label in option_pairs(eval_row)}:
        # Fallback to nearest option by exact gold-label availability in train;
        # if unavailable, keep the neighbor label to expose failure in QA.
        label = str(neighbor["answer_label"])
    caption = substitute_label(str(neighbor.get("oracle_evidence_caption", "")), str(neighbor["answer_label"]), label)
    return caption, str(neighbor["id"]), label, distance(train_feats[best_idx], eval_feats, means, scales)


def run_trainable_probe(rows: list[dict[str, Any]], *, train_split: str, eval_split: str, no_question: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    train_rows = [row for row in rows if row.get("split") == train_split]
    eval_rows = [row for row in rows if row.get("split") == eval_split]
    preds = []
    for row in eval_rows:
        caption, neighbor_id, neighbor_label, dist = nearest_caption(train_rows, row, no_question=no_question)
        pred_answer, pred_label, reason = answer_from_caption(row, caption)
        preds.append(
            {
                "id": row["id"],
                "split": row.get("split", ""),
                "source": row.get("merge_source_name", ""),
                "task_family": row["task_family"],
                "condition": "nearest_caption_no_question" if no_question else "nearest_caption_question_conditioned",
                "caption": caption,
                "nearest_train_id": neighbor_id,
                "nearest_train_answer_label": neighbor_label,
                "nearest_distance": round(dist, 4),
                "pred_answer": pred_answer,
                "pred_answer_label": pred_label,
                "gold_answer": row["answer"],
                "gold_answer_label": row["answer_label"],
                "correct": pred_answer == row["answer"],
                "qa_reason": reason,
            }
        )
    summary = summarize_predictions(preds)
    summary["n_train"] = len(train_rows)
    summary["n_eval"] = len(eval_rows)
    summary["train_split"] = train_split
    summary["eval_split"] = eval_split
    return preds, summary


def markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Natural QCC Probe Results（2026-05-19）",
        "",
        "本实验是 reviewed natural balanced8 的首轮闭环验证：检查新构造的数据是否能作为 QCC evidence-caption/QA 接口运行。",
        "",
        "## Baseline QA",
        "",
        "| condition | n | accuracy | empty | mean chars |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for condition, metrics in summary["baselines"].items():
        lines.append(
            f"| `{condition}` | {metrics['n']} | {metrics['accuracy']:.4f} | {metrics['empty_answer_rate']:.4f} | {metrics['mean_caption_chars']:.1f} |"
        )
    lines.extend(
        [
            "",
            "## Trainable Caption Probe",
            "",
            "| condition | train | eval | accuracy | empty |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for condition, metrics in summary["trainable"].items():
        lines.append(
            f"| `{condition}` | {metrics['n_train']} | {metrics['n_eval']} | {metrics['accuracy']:.4f} | {metrics['empty_answer_rate']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `natural_oracle` 是上限检查：自然 evidence caption 被追加 exact answer label 后，应能被 rule-QA 稳定读取。",
            "- `natural_evidence_no_label` 检查自然措辞本身是否已经包含评估器可识别的答案语义；如果低于 oracle，说明需要升级 QA evaluator 或统一自然 option label。",
            "- `generic_caption` / `statistical_caption` / `question_only` 是接口对照。",
            "- `nearest_caption_*` 是依赖 train split 的轻量 captioner 探针，不是最终 QCC 模型。当前 balanced8 没有 train split，只能做 dev->test 小样本 sanity check。",
            "",
            "## Caveats",
            "",
            "- 样本只有 43 条 reviewer-positive，且 split 不均衡；AIOpsLab 正例只有 test，没有 dev 训练样本。",
            "- 该探针验证的是数据接口和弱训练信号，不足以证明正式 QCC 训练收益。",
            "- 下一步需要每域 50-100 条 reviewer-positive 样本，形成 train/dev/test 后再跑 TSLLM/Qwen caption SFT。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--train_split", default="dev")
    parser.add_argument("--eval_split", default="test")
    args = parser.parse_args()

    rows = load_jsonl(args.data)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    baseline_conditions = [
        "natural_oracle",
        "natural_evidence_no_label",
        "generic_caption",
        "statistical_caption",
        "question_only",
    ]
    summary: dict[str, Any] = {
        "data": str(args.data.relative_to(ROOT)),
        "n_rows": len(rows),
        "by_split": dict(Counter(row.get("split", "") for row in rows)),
        "by_source": dict(Counter(row.get("merge_source_name", "") for row in rows)),
        "baselines": {},
        "trainable": {},
    }
    for condition in baseline_conditions:
        preds, metrics = evaluate_condition(rows, condition)
        write_jsonl(args.out_dir / f"{condition}_predictions.jsonl", preds)
        summary["baselines"][condition] = metrics

    for no_question in (False, True):
        condition = "nearest_caption_no_question" if no_question else "nearest_caption_question_conditioned"
        preds, metrics = run_trainable_probe(
            rows,
            train_split=args.train_split,
            eval_split=args.eval_split,
            no_question=no_question,
        )
        write_jsonl(args.out_dir / f"{condition}_predictions.jsonl", preds)
        summary["trainable"][condition] = metrics

    (args.out_dir / "natural_qcc_probe_results.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (args.out_dir / "NATURAL_QCC_PROBE_RESULTS_20260519_ZH.md").write_text(
        markdown(summary),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
