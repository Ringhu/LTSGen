#!/usr/bin/env python3
"""Evaluate Public Raw TSQA v4 with OpenAI-compatible chat models.

This evaluator consumes ``llm_text_view.jsonl``. The prompts already use the
natural-task format:

    natural_task_{en,zh} + options + full raw time-series CSV

It intentionally uses only the Python standard library for HTTP calls so it can
run on the A100 side even when the OpenAI Python package is unavailable.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import random
import re
import statistics
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from threading import Lock
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = ROOT / ".research/general-qcc-captioner-20260515/public_raw_tsqa_v4_20260521"
DEFAULT_LLM_VIEW = DEFAULT_DATA_DIR / "llm_text_view.jsonl"
DEFAULT_CANONICAL = DEFAULT_DATA_DIR / "canonical_raw_tsqa_v4.jsonl"
DEFAULT_OUT_BASE = DEFAULT_DATA_DIR / "model_eval_20260521"

PROVIDER_PRESETS = {
    "openai": {
        "api_key_env": "OPENAI_API_KEY",
        "base_url_env": "OPENAI_BASE_URL",
        "default_base_url": "https://api.openai.com/v1",
        "model_env": "OPENAI_MODEL",
        "default_model": "gpt-5.4",
    },
    "linkapi": {
        "api_key_env": "LINKAPI_API_KEY",
        "base_url_env": "LINKAPI_BASE_URL",
        "default_base_url": "https://api.linkapi.org/v1/",
        "model_env": "LINKAPI_MODEL",
        "default_model": "gpt-5.4",
    },
    "qwenlocal": {
        "api_key_env": "QWENLOCAL_API_KEY",
        "base_url_env": "QWENLOCAL_BASE_URL",
        "default_api_key": "EMPTY",
        "default_base_url": "http://127.0.0.1:9411/v1",
        "model_env": "QWENLOCAL_MODEL",
        "default_model": "Qwen/Qwen3-8B",
    },
    "qwen": {
        "api_key_env": "QWEN_API_KEY",
        "base_url_env": "QWEN_BASE_URL",
        "default_base_url": "https://api.linkapi.org/v1/",
        "model_env": "QWEN_MODEL",
        "default_model": "qwen-plus",
    },
}

SYSTEM_PROMPT = (
    "You answer raw time-series multiple-choice questions. "
    "Use only the prompt content. Return JSON only with keys: "
    "answer, answer_label, reason."
)


def load_key_env(root: Path) -> None:
    path = root / "key.env"
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key and value:
            os.environ.setdefault(key, value)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, row: dict[str, Any], lock: Lock) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False) + "\n"
    with lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.flush()


def safe_name(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text.strip())
    return text.strip("_") or "run"


def resolve_provider(args: argparse.Namespace) -> dict[str, str]:
    preset = PROVIDER_PRESETS.get(args.provider)
    if preset is None:
        if not args.api_key or not args.base_url or not args.model:
            raise SystemExit("--api_key, --base_url, and --model are required for custom providers")
        return {"api_key": args.api_key, "base_url": args.base_url, "model": args.model}

    api_key = args.api_key or os.environ.get(preset["api_key_env"]) or preset.get("default_api_key", "")
    base_url = args.base_url or os.environ.get(preset["base_url_env"]) or preset["default_base_url"]
    model = args.model or os.environ.get(preset["model_env"]) or preset["default_model"]
    if not api_key:
        raise SystemExit(f"Missing API key for provider={args.provider}; set {preset['api_key_env']} or pass --api_key")
    return {"api_key": api_key, "base_url": base_url.rstrip("/"), "model": model}


def canonical_by_id(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    return {row["id"]: row for row in load_jsonl(path)}


def merge_rows(llm_rows: list[dict[str, Any]], canonical: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    merged = []
    for row in llm_rows:
        item = dict(row)
        canon = canonical.get(row["source_canonical_id"]) or canonical.get(row["id"]) or {}
        for key in ("answer_label_zh", "options_en", "options_zh", "source_simulator", "reasoning_skill_tags"):
            if key in canon:
                item[key] = canon[key]
        merged.append(item)
    return merged


def select_rows(rows: list[dict[str, Any]], *, max_items: int, per_domain: int, seed: int) -> list[dict[str, Any]]:
    if per_domain > 0:
        selected: list[dict[str, Any]] = []
        by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            by_domain[row["domain"]].append(row)
        rng = random.Random(seed)
        for domain in sorted(by_domain):
            pool = list(by_domain[domain])
            rng.shuffle(pool)
            selected.extend(pool[:per_domain])
        return sorted(selected, key=lambda row: row["id"])

    if max_items <= 0 or max_items >= len(rows):
        return rows

    rng = random.Random(seed)
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[(row["domain"], row["answer"])].append(row)
    for pool in buckets.values():
        rng.shuffle(pool)
    selected = []
    keys = sorted(buckets)
    cursor = 0
    while len(selected) < max_items and any(buckets.values()):
        key = keys[cursor % len(keys)]
        if buckets[key]:
            selected.append(buckets[key].pop())
        cursor += 1
    return sorted(selected, key=lambda row: row["id"])


def build_eval_items(rows: list[dict[str, Any]], languages: list[str]) -> list[dict[str, Any]]:
    items = []
    for row in rows:
        for lang in languages:
            if lang not in {"en", "zh"}:
                raise ValueError(f"unsupported language: {lang}")
            prompt_key = f"prompt_{lang}"
            label_key = "answer_label_zh" if lang == "zh" else "answer_label"
            items.append(
                {
                    "id": row["id"],
                    "source_canonical_id": row["source_canonical_id"],
                    "language": lang,
                    "domain": row["domain"],
                    "task_family": row["task_family"],
                    "prompt": row[prompt_key],
                    "gold_answer": row["answer"],
                    "gold_answer_label": row.get(label_key) or row.get("answer_label", ""),
                }
            )
    return items


def prompt_report(items: list[dict[str, Any]], rows: list[dict[str, Any]], args: argparse.Namespace, run_cfg: dict[str, str]) -> dict[str, Any]:
    lengths = [len(item["prompt"]) for item in items]
    by_lang = Counter(item["language"] for item in items)
    return {
        "dataset": str(args.llm_view.relative_to(ROOT) if args.llm_view.is_relative_to(ROOT) else args.llm_view),
        "provider": args.provider,
        "model": run_cfg["model"],
        "n_rows": len(rows),
        "n_prompts": len(items),
        "languages": dict(by_lang),
        "prompt_chars": {
            "min": min(lengths) if lengths else 0,
            "max": max(lengths) if lengths else 0,
            "mean": round(statistics.mean(lengths), 1) if lengths else 0,
        },
        "by_domain": dict(Counter(row["domain"] for row in rows)),
        "answer_distribution": dict(Counter(row["answer"] for row in rows)),
        "dry_run": bool(args.dry_run),
    }


def extract_message_text(body: dict[str, Any]) -> str:
    try:
        msg = body["choices"][0]["message"]
    except Exception:
        return ""
    for key in ("content", "reasoning_content", "reasoning"):
        value = msg.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    content = msg.get("content")
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                parts.append(part["text"])
        return "".join(parts).strip()
    return ""


def extract_json(text: str) -> dict[str, Any]:
    stripped = (text or "").strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            return json.loads(stripped[start : end + 1])
    return {}


def parse_answer(text: str) -> tuple[str, str, str]:
    data = extract_json(text)
    answer = str(data.get("answer", "")).strip().upper()[:1]
    label = str(data.get("answer_label", "")).strip()
    reason = str(data.get("reason", "")).strip()
    if answer not in {"A", "B", "C", "D"}:
        match = re.search(r"\b([ABCD])\b", text.upper())
        answer = match.group(1) if match else ""
    return answer, label, reason


def chat_once(item: dict[str, Any], run_cfg: dict[str, str], args: argparse.Namespace) -> dict[str, Any]:
    url = f"{run_cfg['base_url']}/chat/completions"
    payload: dict[str, Any] = {
        "model": run_cfg["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": item["prompt"]},
        ],
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
    }
    if not args.no_response_format:
        payload["response_format"] = {"type": "json_object"}
    if args.provider == "qwenlocal" and args.disable_qwen_thinking:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    if args.extra_body_json:
        payload.update(json.loads(args.extra_body_json))

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {run_cfg['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = time.time()
    with urllib.request.urlopen(request, timeout=args.timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    raw_text = extract_message_text(body)
    pred, pred_label, reason = parse_answer(raw_text)
    latency = time.time() - started
    return {
        **{key: item[key] for key in ("id", "source_canonical_id", "language", "domain", "task_family")},
        "model": run_cfg["model"],
        "provider": args.provider,
        "gold_answer": item["gold_answer"],
        "gold_answer_label": item["gold_answer_label"],
        "pred_answer": pred,
        "pred_answer_label": pred_label,
        "correct": pred == item["gold_answer"],
        "reason": reason[:1000],
        "raw_response": raw_text,
        "prompt_chars": len(item["prompt"]),
        "latency_sec": round(latency, 3),
    }


def evaluate_item(item: dict[str, Any], run_cfg: dict[str, str], args: argparse.Namespace) -> dict[str, Any]:
    last_error = ""
    for attempt in range(args.max_retries + 1):
        try:
            return chat_once(item, run_cfg, args)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            last_error = f"HTTP {exc.code}: {detail[:500]}"
        except Exception as exc:  # noqa: BLE001
            last_error = repr(exc)
        if attempt < args.max_retries:
            time.sleep(min(30, 2**attempt))
    return {
        **{key: item[key] for key in ("id", "source_canonical_id", "language", "domain", "task_family")},
        "model": run_cfg["model"],
        "provider": args.provider,
        "gold_answer": item["gold_answer"],
        "gold_answer_label": item["gold_answer_label"],
        "pred_answer": "",
        "pred_answer_label": "",
        "correct": False,
        "reason": "",
        "raw_response": "",
        "error": last_error,
        "prompt_chars": len(item["prompt"]),
        "latency_sec": 0.0,
    }


def aggregate(predictions: list[dict[str, Any]], report: dict[str, Any], elapsed: float) -> dict[str, Any]:
    def acc(items: list[dict[str, Any]]) -> float:
        return round(sum(1 for item in items if item.get("correct")) / len(items), 4) if items else 0.0

    def grouped(field: str) -> dict[str, dict[str, Any]]:
        out = {}
        for value in sorted({str(item[field]) for item in predictions}):
            subset = [item for item in predictions if str(item[field]) == value]
            out[value] = {"n": len(subset), "accuracy": acc(subset)}
        return out

    errors = [item for item in predictions if item.get("error")]
    latencies = [float(item["latency_sec"]) for item in predictions if float(item.get("latency_sec", 0)) > 0]
    return {
        "run": {**report, "elapsed_sec": round(elapsed, 2), "error_count": len(errors)},
        "overall": {
            "n": len(predictions),
            "accuracy": acc(predictions),
            "empty_answer_rate": round(sum(1 for item in predictions if not item.get("pred_answer")) / len(predictions), 4) if predictions else 0.0,
            "mean_latency_sec": round(statistics.mean(latencies), 3) if latencies else 0.0,
        },
        "by_language": grouped("language"),
        "by_domain": grouped("domain"),
        "by_task_family": grouped("task_family"),
        "pred_answer_distribution": dict(Counter(item.get("pred_answer") or "EMPTY" for item in predictions)),
        "errors_preview": errors[:10],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    load_key_env(ROOT)
    run_cfg = resolve_provider(args)
    llm_rows = load_jsonl(args.llm_view)
    rows = merge_rows(llm_rows, canonical_by_id(args.canonical))
    rows = select_rows(rows, max_items=args.max_items, per_domain=args.per_domain, seed=args.seed)
    languages = ["en", "zh"] if args.languages == "both" else [args.languages]
    items = build_eval_items(rows, languages)
    report = prompt_report(items, rows, args, run_cfg)

    run_name = args.run_name or f"{args.provider}_{safe_name(run_cfg['model'])}_{args.languages}_{len(rows)}"
    out_dir = args.out_dir or (DEFAULT_OUT_BASE / run_name)
    out_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = out_dir / "predictions.jsonl"
    metrics_path = out_dir / "metrics.json"
    write_json(out_dir / "prompt_report.json", report)
    write_jsonl(
        out_dir / "prompt_preview.jsonl",
        [
            {
                "id": item["id"],
                "language": item["language"],
                "domain": item["domain"],
                "prompt_chars": len(item["prompt"]),
                "prompt_preview": item["prompt"][:1200],
            }
            for item in items[: args.preview_count]
        ],
    )
    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return report

    started = time.time()
    existing_predictions: list[dict[str, Any]] = []
    done_keys: set[tuple[str, str]] = set()
    if args.resume and predictions_path.is_file():
        existing_predictions = load_jsonl(predictions_path)
        for row in existing_predictions:
            done_keys.add((row["id"], row["language"]))
    remaining_items = [item for item in items if (item["id"], item["language"]) not in done_keys]
    if args.resume and existing_predictions:
        print(f"[resume] loaded {len(existing_predictions)} existing predictions; remaining {len(remaining_items)}")

    lock = Lock()
    if not args.resume and predictions_path.exists():
        predictions_path.unlink()

    predictions: list[dict[str, Any]] = list(existing_predictions)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(evaluate_item, item, run_cfg, args) for item in remaining_items]
        for idx, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            result = future.result()
            predictions.append(result)
            append_jsonl(predictions_path, result, lock)
            if args.progress_every > 0 and idx % args.progress_every == 0:
                print(f"[progress] {idx}/{len(remaining_items)} newly evaluated; total {len(predictions)}/{len(items)}")

    predictions.sort(key=lambda item: (item["id"], item["language"]))
    metrics = aggregate(predictions, report, time.time() - started)
    write_jsonl(predictions_path, predictions)
    write_json(metrics_path, metrics)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm_view", type=Path, default=DEFAULT_LLM_VIEW)
    parser.add_argument("--canonical", type=Path, default=DEFAULT_CANONICAL)
    parser.add_argument("--out_dir", type=Path, default=None)
    parser.add_argument("--run_name", default="")
    parser.add_argument("--provider", default="openai", choices=["openai", "linkapi", "qwen", "qwenlocal", "custom"])
    parser.add_argument("--model", default="")
    parser.add_argument("--api_key", default="")
    parser.add_argument("--base_url", default="")
    parser.add_argument("--languages", default="both", choices=["en", "zh", "both"])
    parser.add_argument("--max_items", type=int, default=0, help="0 means all rows")
    parser.add_argument("--per_domain", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20260521)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--max_retries", type=int, default=2)
    parser.add_argument("--max_tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--extra_body_json", default="")
    parser.add_argument("--disable_qwen_thinking", dest="disable_qwen_thinking", action="store_true", default=True)
    parser.add_argument("--enable_qwen_thinking", dest="disable_qwen_thinking", action="store_false")
    parser.add_argument("--no_response_format", action="store_true")
    parser.add_argument("--dry_run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--preview_count", type=int, default=4)
    parser.add_argument("--progress_every", type=int, default=10)
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
