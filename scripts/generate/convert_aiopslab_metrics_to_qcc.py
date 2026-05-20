#!/usr/bin/env python3
"""Convert official AIOpsLab Prometheus CSV exports into General QCC JSONL.

Input is a directory produced by `collect_aiopslab_official_cases.py` or the
older `59_aiopslab_case_collector.py`: it must contain `index.json` and one
subdirectory per case with `manifest.json` and `metrics_output/**/*.csv`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


LETTERS = ("A", "B", "C", "D")
PROMPT = (
    "You are a question-conditioned time-series evidence captioner. Given the "
    "time series and the question, write one or two concise natural-language "
    "sentences containing only the evidence needed to answer the question. Do "
    "not choose an answer option, do not write an option letter, and do not "
    "output JSON. Domain context: x0 is service CPU load, x1 is memory working "
    "set, x2 is network receive rate, and x3 is network transmit rate for a "
    "service or pod group observed through AIOpsLab Prometheus telemetry."
)


METRIC_ALIASES = {
    "cpu": "container_cpu_load_average_10s",
    "memory": "container_memory_working_set_bytes",
    "net_rx": "container_network_receive_bytes_total",
    "net_tx": "container_network_transmit_bytes_total",
}


def stable_int(*parts: Any) -> int:
    text = "::".join(str(part) for part in parts)
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:4], "big")


def fmt(value: float) -> str:
    return f"{float(value):.2f}"


def fmt3(value: float) -> str:
    return f"{float(value):.3f}"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def split_for_case(seed: int, case_pos: int) -> str:
    key = (int(seed) + int(case_pos)) % 5
    if key == 0:
        return "test"
    if key == 1:
        return "dev"
    return "train"


def region_from_fraction(frac: float) -> str:
    if frac < 1 / 3:
        return "early"
    if frac < 2 / 3:
        return "middle"
    return "late"


def normalize_values(values: np.ndarray) -> np.ndarray:
    mean = values.mean(axis=0, keepdims=True)
    std = values.std(axis=0, keepdims=True)
    std = np.where(std < 1e-6, 1.0, std)
    return ((values - mean) / std).astype(float)


def options_from_label(correct: str, labels: list[str], key: str) -> tuple[list[str], str]:
    distractors = [label for label in labels if label != correct]
    if len(distractors) < 3:
        raise ValueError(f"Need 3 distractors for {correct}: {labels}")
    target = LETTERS[stable_int(key) % 4]
    texts = {target: correct}
    for letter, value in zip([letter for letter in LETTERS if letter != target], distractors[:3]):
        texts[letter] = value
    return [f"{letter}. {texts[letter]}" for letter in LETTERS], target


def abstract_primitive_for_task(task_family: str) -> str:
    if "trend" in task_family:
        return "trend"
    if "extrema" in task_family:
        return "extrema"
    if "volatility" in task_family:
        return "volatility"
    if "anomaly" in task_family:
        return "anomaly"
    if "_window_" in task_family:
        return "window_comparison"
    if "_cross_" in task_family:
        return "cross_variable_relation"
    if "context" in task_family or "domain" in task_family:
        return "domain_context"
    return task_family


def abstract_answer_label_for(label: str, primitive: str) -> str:
    text = label.lower()
    if primitive in {"trend", "extrema", "volatility", "anomaly"}:
        return text.replace(" ", "_")
    if primitive == "window_comparison":
        if "first" in text:
            return "first_higher"
        if "second" in text:
            return "second_higher"
        if "similar" in text:
            return "similar"
        return "unclear"
    if primitive == "cross_variable_relation":
        if "cpu-memory" in text:
            return "x0_x1_relation"
        if "network" in text:
            return "x2_x3_relation"
        if "both similar" in text:
            return "both_similar"
        return "both_weak"
    if primitive == "domain_context":
        if "port" in text or "auth" in text or "scale" in text:
            return "stressed"
        if "stable" in text:
            return "stable"
        return "unclear"
    return text.replace(" ", "_")


def statistical_caption(raw: np.ndarray) -> str:
    names = ("x0", "x1", "x2", "x3")
    parts = []
    for idx, name in enumerate(names):
        x = raw[:, idx]
        parts.append(
            f"{name} starts {fmt(x[0])}, ends {fmt(x[-1])}, mean {fmt(x.mean())}, "
            f"std {fmt(x.std())}, min {fmt(x.min())}, max {fmt(x.max())}."
        )
    return " ".join(parts)


def read_metric_csv(metrics_dir: Path, metric_name: str) -> pd.DataFrame:
    matches = sorted(metrics_dir.rglob(f"kpi_{metric_name}.csv"))
    if not matches:
        raise FileNotFoundError(f"missing metric CSV for {metric_name} under {metrics_dir}")
    frames = []
    for path in matches:
        frame = pd.read_csv(path)
        if not frame.empty:
            frames.append(frame)
    if not frames:
        raise ValueError(f"empty metric CSVs for {metric_name}")
    return pd.concat(frames, ignore_index=True)


def pivot_metric(metrics_dir: Path, metric_name: str) -> pd.DataFrame:
    df = read_metric_csv(metrics_dir, metric_name)
    required = {"timestamp", "cmdb_id", "value"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{metric_name} missing columns {missing}")
    df = df[["timestamp", "cmdb_id", "value"]].copy()
    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["timestamp", "cmdb_id", "value"])
    df = df.groupby(["timestamp", "cmdb_id"], as_index=False)["value"].mean()
    return df.pivot(index="timestamp", columns="cmdb_id", values="value").sort_index()


def service_score_columns(columns: list[str], faulty_service: str) -> list[str]:
    service = faulty_service.replace("_", "-")
    matches = [col for col in columns if service in str(col)]
    if matches:
        return matches
    service_tokens = [tok for tok in service.split("-") if tok and tok not in {"service", "mongodb"}]
    if service_tokens:
        token_matches = [col for col in columns if any(tok in str(col) for tok in service_tokens)]
        if token_matches:
            return token_matches
    return list(columns)


def align_case_values(metrics_dir: Path, faulty_service: str, horizon: int) -> tuple[np.ndarray, dict[str, Any]]:
    pivots = {alias: pivot_metric(metrics_dir, metric) for alias, metric in METRIC_ALIASES.items()}
    common_index = None
    for frame in pivots.values():
        common_index = frame.index if common_index is None else common_index.intersection(frame.index)
    if common_index is None or len(common_index) == 0:
        raise ValueError(f"no common timestamps in {metrics_dir}")
    common_index = common_index.sort_values()

    series = []
    selected_columns: dict[str, list[str]] = {}
    for alias, frame in pivots.items():
        frame = frame.loc[common_index]
        cols = service_score_columns([str(col) for col in frame.columns], faulty_service)
        selected_columns[alias] = cols[:20]
        values = frame[cols].mean(axis=1).interpolate(limit_direction="both").fillna(0.0).to_numpy(dtype=float)
        if "network_" in METRIC_ALIASES[alias] or alias.startswith("net_"):
            # Network counters are cumulative. Convert to a non-negative per-step rate.
            values = np.diff(values, prepend=values[0])
            values = np.clip(values, 0.0, None)
        series.append(values)
    raw = np.stack(series, axis=1)
    if len(raw) >= horizon:
        idx = np.linspace(0, len(raw) - 1, horizon).round().astype(int)
        raw = raw[idx]
    else:
        raw = np.pad(raw, ((0, horizon - len(raw)), (0, 0)), mode="edge")
    meta = {
        "source_timestamps": [int(ts) for ts in common_index.tolist()],
        "selected_columns": selected_columns,
        "source_metric_names": METRIC_ALIASES,
    }
    return raw.astype(float), meta


def make_record(
    *,
    row_id: str,
    split: str,
    split_group: str,
    manifest: dict[str, Any],
    raw: np.ndarray,
    values: np.ndarray,
    task_family: str,
    question: str,
    labels: list[str],
    answer_label: str,
    caption: str,
    support_slots: dict[str, Any],
    source_meta: dict[str, Any],
) -> dict[str, Any]:
    options, answer = options_from_label(answer_label, labels, f"{row_id}::{task_family}")
    primitive = abstract_primitive_for_task(task_family)
    abstract_answer = abstract_answer_label_for(answer_label, primitive)
    meta = {
        "task_family": task_family,
        "domain": "aiops_broad_official",
        "multisim_source_domain": "aiopslab_official",
        "official_target_simulator": "AIOpsLab",
        "source_kind": "official_simulator_export",
        "case_id": manifest["case_id"],
        "problem_id": manifest.get("problem_id", ""),
        "fault_family": manifest.get("fault_family", ""),
        "faulty_service": manifest.get("faulty_service", ""),
        "app": manifest.get("app", ""),
        "seed": manifest.get("seed", 0),
        "split_group": split_group,
        "question": question,
        "options": options,
        "answer": answer,
        "answer_label": answer_label,
        "support_slots": support_slots,
        "abstract_primitive": primitive,
        "abstract_answer_label": abstract_answer,
        "format_version": "aiopslab_official_v1",
        "source_meta": source_meta,
    }
    generic = (
        "This AIOpsLab telemetry trace contains Prometheus CPU, memory, and "
        "network signals from a Kubernetes microservice environment."
    )
    return {
        "id": row_id,
        "domain": "aiops_broad_official",
        "multisim_source_domain": "aiopslab_official",
        "source_path": manifest.get("metrics_dir", ""),
        "split": split,
        "split_group": split_group,
        "scenario_index": int(manifest.get("seed", 0)),
        "horizon": int(raw.shape[0]),
        "task_family": task_family,
        "question": question,
        "options": options,
        "answer": answer,
        "answer_label": answer_label,
        "oracle_evidence_caption": caption,
        "target_caption": caption,
        "generic_caption": generic,
        "statistical_caption": statistical_caption(raw),
        "support_slots": support_slots,
        "abstract_primitive": primitive,
        "abstract_answer_label": abstract_answer,
        "values": values.tolist(),
        "raw_compact_values": raw.tolist(),
        "prompt": f"{PROMPT}\nQuestion: {question}",
        "output": caption,
        "meta": meta,
    }


def build_case_rows(manifest: dict[str, Any], raw: np.ndarray, source_meta: dict[str, Any], split: str, split_group: str) -> list[dict[str, Any]]:
    values = normalize_values(raw)
    horizon = raw.shape[0]
    x0, x1, x2, x3 = raw[:, 0], raw[:, 1], raw[:, 2], raw[:, 3]
    rows: list[dict[str, Any]] = []

    def add(task: str, question: str, labels: list[str], answer_label: str, caption: str, slots: dict[str, Any]) -> None:
        row_id = f"aiopslab_official::{split_group}::{task}"
        rows.append(
            make_record(
                row_id=row_id,
                split=split,
                split_group=split_group,
                manifest=manifest,
                raw=raw,
                values=values,
                task_family=task,
                question=question,
                labels=labels,
                answer_label=answer_label,
                caption=caption,
                support_slots={
                    **slots,
                    "answer_label": answer_label,
                    "window_start": 0,
                    "window_end": horizon,
                },
                source_meta=source_meta,
            )
        )

    # Trend: CPU load.
    delta = float(x0[-1] - x0[0])
    threshold = max(0.02, 0.35 * float(np.std(x0)))
    trend = "flat" if abs(delta) <= threshold else ("upward" if delta > 0 else "downward")
    add(
        "aiops_official_cpu_trend",
        "Across this AIOpsLab telemetry window, how does service CPU load x0 change overall?",
        ["upward", "downward", "flat", "mixed"],
        trend,
        f"Service CPU load x0 is {trend}: it starts near {fmt(x0[0])}, ends near {fmt(x0[-1])}, and has variability {fmt(np.std(x0))}.",
        {"start_value": float(x0[0]), "end_value": float(x0[-1]), "std": float(np.std(x0))},
    )

    # Extrema: memory peak region.
    peak_idx = int(np.argmax(x1))
    peak_region = region_from_fraction(peak_idx / max(horizon - 1, 1))
    add(
        "aiops_official_memory_extrema",
        "Where in the window does service memory working set x1 reach its highest point?",
        ["early", "middle", "late", "no clear extremum"],
        peak_region,
        f"Memory working set x1 reaches its highest point in the {peak_region} part of the window, at step {peak_idx} of {horizon} with value about {fmt(x1[peak_idx])}.",
        {"extrema_index": peak_idx, "extrema_value": float(x1[peak_idx]), "extrema_mode": "max"},
    )

    # Volatility: network receive.
    stds = [float(part.std()) for part in np.array_split(x2, 3)]
    if max(stds) - min(stds) <= max(0.05, 0.15 * max(stds)):
        vol = "similar thirds"
    else:
        vol = ["early", "middle", "late"][int(np.argmax(stds))]
    add(
        "aiops_official_network_volatility",
        "Which third of the window has the highest volatility in network receive rate x2?",
        ["early", "middle", "late", "similar thirds"],
        vol,
        f"Network receive rate x2 has volatility labeled {vol}: early, middle, and late standard deviations are {fmt(stds[0])}, {fmt(stds[1])}, and {fmt(stds[2])}.",
        {"region_stds": {"early": stds[0], "middle": stds[1], "late": stds[2]}},
    )

    # Window comparison: memory first/second half.
    mid = horizon // 2
    first, second = float(x1[:mid].mean()), float(x1[mid:].mean())
    if abs(first - second) <= max(0.05, 0.01 * max(abs(first), 1.0)):
        win = "similar halves"
    elif first > second:
        win = "first half higher"
    else:
        win = "second half higher"
    add(
        "aiops_official_window_memory",
        "Is memory working set x1 higher in the first half or the second half of the window?",
        ["first half higher", "second half higher", "similar halves", "cannot determine"],
        win,
        f"The half-window comparison is {win}: first-half mean x1 is {fmt(first)} and second-half mean x1 is {fmt(second)}.",
        {"first_mean": first, "second_mean": second},
    )

    # Cross-variable relation: CPU/memory vs network rx/tx.
    c01 = float(np.corrcoef(x0, x1)[0, 1]) if np.std(x0) > 1e-9 and np.std(x1) > 1e-9 else 0.0
    c23 = float(np.corrcoef(x2, x3)[0, 1]) if np.std(x2) > 1e-9 and np.std(x3) > 1e-9 else 0.0
    if max(abs(c01), abs(c23)) < 0.20:
        cross = "both weak"
    elif abs(c01 - c23) < 0.08 and max(abs(c01), abs(c23)) > 0.25:
        cross = "both similar"
    elif abs(c01) > abs(c23):
        cross = "cpu-memory coupling"
    else:
        cross = "network rx-tx coupling"
    add(
        "aiops_official_cross_signal_relation",
        "Which pair of telemetry signals is more strongly coupled in this window?",
        ["cpu-memory coupling", "network rx-tx coupling", "both similar", "both weak"],
        cross,
        f"The cross-signal evidence is {cross}: corr(x0,x1) is {fmt3(c01)} and corr(x2,x3) is {fmt3(c23)}.",
        {"corr_cpu_memory": c01, "corr_net_rx_tx": c23},
    )

    # Domain/fault context from official label.
    family = str(manifest.get("fault_family", ""))
    faulty_service = str(manifest.get("faulty_service", ""))
    app = str(manifest.get("app", ""))
    label_map = {
        "port_misconfig": "port misconfiguration context",
        "port-misconfig": "port misconfiguration context",
        "revoke_auth": "authentication fault context",
        "scale_pod_zero": "scale-to-zero context",
    }
    context = label_map.get(family, "unclear incident context")
    add(
        "aiops_official_fault_context",
        "What AIOpsLab fault context best describes this telemetry case?",
        ["port misconfiguration context", "authentication fault context", "scale-to-zero context", "unclear incident context"],
        context,
        f"The official simulator label indicates {context}: problem id is {manifest.get('problem_id', '')} and the faulty service is {manifest.get('faulty_service', '')}.",
        {"problem_id": manifest.get("problem_id", ""), "fault_family": family, "faulty_service": manifest.get("faulty_service", "")},
    )

    service_label_map = {
        "user-service": "user-service",
        "text-service": "text-service",
        "post-storage-service": "post-storage-service",
        "frontend": "frontend service",
        "geo": "geo service",
        "rate": "rate service",
    }
    service_context = service_label_map.get(faulty_service, "other service")
    service_answer = service_context if service_context in {"user-service", "text-service", "post-storage-service"} else "other service"
    add(
        "aiops_official_faulty_service_context",
        "Which service does the official AIOpsLab incident label mark as faulty?",
        ["user-service", "text-service", "post-storage-service", "other service"],
        service_answer,
        f"The official incident metadata maps this case to {service_answer}; the raw faulty-service field is {service_context}.",
        {"faulty_service": faulty_service, "service_context": service_context},
    )

    app_label_map = {
        "social-network": "social-network application",
        "hotel-reservation": "hotel-reservation application",
        "astronomy-shop": "astronomy-shop application",
    }
    app_context = app_label_map.get(app, "unknown application")
    add(
        "aiops_official_app_context",
        "Which benchmark application generated this AIOpsLab telemetry case?",
        ["social-network application", "hotel-reservation application", "astronomy-shop application", "unknown application"],
        app_context,
        f"The official case metadata ties this telemetry window to the {app_context}.",
        {"app": app, "app_context": app_context},
    )

    family_detail_map = {
        "port_misconfig": "port misconfiguration",
        "port-misconfig": "port misconfiguration",
        "revoke_auth": "authentication revocation",
        "scale_pod_zero": "scale-to-zero",
    }
    family_detail = family_detail_map.get(family, "other incident type")
    add(
        "aiops_official_fault_family_detail_context",
        "Which fault family is recorded by the official simulator metadata?",
        ["port misconfiguration", "authentication revocation", "scale-to-zero", "other incident type"],
        family_detail,
        f"The simulator metadata records the fault family as {family_detail}.",
        {"fault_family": family, "fault_family_detail": family_detail},
    )

    if family_detail == "port misconfiguration":
        layer_context = "service routing layer"
    elif family_detail == "authentication revocation":
        layer_context = "database authentication layer"
    elif family_detail == "scale-to-zero":
        layer_context = "replica scaling layer"
    else:
        layer_context = "unknown layer"
    add(
        "aiops_official_fault_layer_context",
        "Which system layer does the official fault family primarily affect?",
        ["service routing layer", "database authentication layer", "replica scaling layer", "unknown layer"],
        layer_context,
        f"The official fault family maps this incident to the {layer_context}.",
        {"fault_family": family, "fault_layer": layer_context},
    )

    if faulty_service == "user-service":
        role_context = "user/account service role"
    elif faulty_service == "text-service":
        role_context = "text/content service role"
    elif faulty_service == "post-storage-service":
        role_context = "storage service role"
    else:
        role_context = "other service role"
    add(
        "aiops_official_service_role_context",
        "What service role is implied by the official faulty-service label?",
        ["user/account service role", "text/content service role", "storage service role", "other service role"],
        role_context,
        f"The faulty-service label implies a {role_context} for this incident.",
        {"faulty_service": faulty_service, "service_role": role_context},
    )

    provenance_context = "built-in AIOpsLab incident"
    add(
        "aiops_official_case_provenance_context",
        "What is the provenance of this telemetry example?",
        ["built-in AIOpsLab incident", "synthetic fallback incident", "external log replay", "unknown provenance"],
        provenance_context,
        f"This example comes from a {provenance_context} exported through the simulator metric collector.",
        {"provenance": provenance_context},
    )
    return rebalance_answers(rows)


def rebalance_answers(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(rows, key=lambda row: hashlib.sha256(row["id"].encode("utf-8")).hexdigest())
    target_by_id = {row["id"]: LETTERS[pos % 4] for pos, row in enumerate(ranked)}
    out = []
    for row in rows:
        target = target_by_id[row["id"]]
        labels = [opt.split(". ", 1)[1] for opt in row["options"]]
        correct = row["answer_label"]
        distractors = [label for label in labels if label != correct]
        texts = {target: correct}
        for letter, value in zip([letter for letter in LETTERS if letter != target], distractors):
            texts[letter] = value
        new = dict(row)
        new["answer"] = target
        new["options"] = [f"{letter}. {texts[letter]}" for letter in LETTERS]
        new["meta"] = {**new["meta"], "answer": target, "options": new["options"]}
        out.append(new)
    return out


def sft_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "values": row["values"],
        "prompt": row["prompt"],
        "output": row["output"],
        "target_caption": row.get("target_caption", row.get("output", "")),
        "meta": row.get("meta", {}),
    }


def report_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    required = (
        "id",
        "domain",
        "split",
        "task_family",
        "horizon",
        "values",
        "prompt",
        "output",
        "target_caption",
        "oracle_evidence_caption",
        "generic_caption",
        "statistical_caption",
        "question",
        "options",
        "answer",
        "answer_label",
        "support_slots",
        "abstract_primitive",
        "abstract_answer_label",
        "meta",
    )
    ids = [row.get("id") for row in rows]
    split_groups: dict[str, set[str]] = defaultdict(set)
    missing = []
    support_prompt_count = 0
    for row in rows:
        split_groups[str(row.get("split", ""))].add(str(row.get("split_group", row.get("id", ""))))
        text = str(row.get("prompt", "")).lower()
        if "support_slots" in text or "support slots" in text:
            support_prompt_count += 1
        for key in required:
            if key not in row or row[key] in ("", [], None):
                missing.append((row.get("id", "?"), key))
    leakage = 0
    splits = sorted(split_groups)
    for idx, a in enumerate(splits):
        for b in splits[idx + 1 :]:
            leakage += len(split_groups[a] & split_groups[b])
    answers = Counter(row.get("answer", "") for row in rows)
    max_share = max(answers.values()) / max(1, len(rows)) if answers else 1.0
    split_counts = Counter(row.get("split", "") for row in rows)
    return {
        "n": len(rows),
        "by_split": dict(split_counts),
        "by_domain": dict(Counter(row.get("domain", "") for row in rows)),
        "by_multisim_source_domain": dict(Counter(row.get("multisim_source_domain", "") for row in rows)),
        "by_task_family": dict(Counter(row.get("task_family", "") for row in rows)),
        "by_answer": dict(answers),
        "by_abstract_primitive": dict(Counter(row.get("abstract_primitive", "") for row in rows)),
        "duplicate_id_count": len(ids) - len(set(ids)),
        "split_group_leakage_count": leakage,
        "prompt_support_slots_count": support_prompt_count,
        "missing_required_field_count": len(missing),
        "missing_required_fields": missing[:20],
        "max_answer_share": round(max_share, 4),
        "schema_gate_pass": bool(rows)
        and all(split_counts.get(split, 0) > 0 for split in ("train", "dev", "test"))
        and len(ids) == len(set(ids))
        and leakage == 0
        and not missing
        and support_prompt_count == 0
        and max_share <= 0.35,
    }


def manifests_from_input(input_dir: Path) -> list[dict[str, Any]]:
    index = input_dir / "index.json"
    if index.exists():
        manifests = load_json(index)
    else:
        manifests = []
    out = []
    for item in manifests:
        case_manifest = input_dir / item["case_id"] / "manifest.json"
        out.append(load_json(case_manifest) if case_manifest.exists() else item)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--prefix", default="aiopslab_official_v1")
    parser.add_argument("--horizon", type=int, default=64)
    parser.add_argument("--min_csv_count", type=int, default=4)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict[str, Any]] = []
    case_reports = []
    for case_pos, manifest in enumerate(manifests_from_input(input_dir)):
        if manifest.get("status") not in {"ok", "OK", None}:
            case_reports.append({"case_id": manifest.get("case_id"), "status": "skipped_failed_manifest"})
            continue
        metrics_dir = Path(manifest["metrics_dir"])
        if not metrics_dir.exists():
            metrics_dir = input_dir / manifest["case_id"] / "metrics_output"
        csv_count = len(list(metrics_dir.rglob("*.csv")))
        if csv_count < args.min_csv_count:
            case_reports.append({"case_id": manifest.get("case_id"), "status": "skipped_not_enough_csv", "csv_count": csv_count})
            continue
        raw, source_meta = align_case_values(metrics_dir, str(manifest.get("faulty_service", "")), args.horizon)
        split = split_for_case(int(manifest.get("seed", 0)), case_pos)
        split_group = f"{manifest['case_id']}::case{case_pos:03d}"
        rows = build_case_rows(manifest, raw, source_meta, split, split_group)
        all_rows.extend(rows)
        case_reports.append({"case_id": manifest.get("case_id"), "status": "converted", "rows": len(rows), "split": split, "csv_count": csv_count})

    # If only one official case is available, keep the artifact honest but make
    # all split files loadable by deterministic row-level splitting. The
    # split_group remains case-level, so leakage is visible in the report.
    if len({row["split"] for row in all_rows}) < 3 and len(all_rows) >= 6:
        ranked = sorted(all_rows, key=lambda row: hashlib.sha256(row["id"].encode("utf-8")).hexdigest())
        for pos, row in enumerate(ranked):
            row["split"] = ("test", "dev", "train", "train", "train")[pos % 5]
            row["meta"]["split_fallback_note"] = "row_level_split_used_because_only_one_official_case_was_available"

    write_jsonl(out_dir / f"{args.prefix}.jsonl", all_rows)
    write_jsonl(out_dir / f"{args.prefix}_sft.jsonl", [sft_row(row) for row in all_rows])
    for split in ("train", "dev", "test"):
        part = [row for row in all_rows if row["split"] == split]
        write_jsonl(out_dir / f"{args.prefix}_{split}.jsonl", part)
        write_jsonl(out_dir / f"{args.prefix}_{split}_sft.jsonl", [sft_row(row) for row in part])
    report = report_rows(all_rows)
    report["input_dir"] = str(input_dir)
    report["out_dir"] = str(out_dir)
    report["prefix"] = args.prefix
    report["case_reports"] = case_reports
    report["official_source_note"] = "Rows are derived from AIOpsLab Prometheus CSV exports; split leakage remains nonzero if only one official case is available."
    (out_dir / "schema_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
