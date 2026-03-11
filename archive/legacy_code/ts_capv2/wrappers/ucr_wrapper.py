# ts_capv2/wrappers/ucr_wrapper.py
from __future__ import annotations

import csv
import logging
import re
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

from ts_capv2.utils.openai_chat import OpenAIChatClient
from .base import BaseWrapper, WrapperConfig

logger = logging.getLogger(__name__)

# --- Legacy Helper Functions ---

def _load_text(path: Path, max_chars: int = 8000) -> str:
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as e:
        logger.warning(f"Could not read README {path}: {e}")
        return ""
    text = text.strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...(truncated)"
    return text


def _safe_float(x: str) -> float:
    x = (x or "").strip()
    if x == "":
        return float("nan")
    try:
        return float(x)
    except ValueError:
        if x.lower() == "nan":
            return float("nan")
        # Return NaN instead of crashing
        return float("nan")


def _fill_nan_1d(values: List[float]) -> List[float]:
    if not values:
        return values
    n = len(values)
    last = None
    for i in range(n):
        v = values[i]
        if v == v:
            last = v
        else:
            if last is not None:
                values[i] = last
    last = None
    for i in range(n - 1, -1, -1):
        v = values[i]
        if v == v:
            last = v
        else:
            if last is not None:
                values[i] = last
    for i in range(n):
        if not (values[i] == values[i]):
            values[i] = 0.0
    return values


def _iter_tsv_rows(tsv_path: Path) -> Iterable[List[str]]:
    try:
        with tsv_path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                if not row:
                    continue
                yield row
    except OSError as e:
        logger.error(f"Error reading TSV {tsv_path}: {e}")


def _collect_labels(tsv_paths: Sequence[Path], max_scan: Optional[int] = None) -> List[int]:
    labels: List[int] = []
    seen = set()
    cnt = 0
    for p in tsv_paths:
        if not p.exists():
            continue
        for row in _iter_tsv_rows(p):
            if max_scan is not None and cnt >= max_scan:
                break
            cnt += 1
            try:
                lab = int(float(row[0]))
            except (ValueError, IndexError):
                continue
            if lab not in seen:
                seen.add(lab)
                labels.append(lab)
        if max_scan is not None and cnt >= max_scan:
            break
    labels.sort()
    return labels


def _parse_label_map_from_readme(readme_text: str) -> Dict[str, str]:
    if not readme_text:
        return {}
    text = readme_text
    patterns = [
        r"(?im)^\s*class\s*(\d+)\s*[:=\-]\s*(.+?)\s*$",
        r"(?im)^\s*label\s*(\d+)\s*[:=\-]\s*(.+?)\s*$",
        r"(?im)^\s*(\d+)\s*[:=\-]\s*(.+?)\s*$",
    ]
    lm: Dict[str, str] = {}
    for pat in patterns:
        for m in re.finditer(pat, text):
            k = m.group(1).strip()
            v = m.group(2).strip()
            if len(v) < 2:
                continue
            if any(kw in v.lower() for kw in ["train size", "test size", "time series length", "missing value"]):
                continue
            if len(v) > 200:
                v = v[:200] + "..."
            lm[k] = v
    return lm


def _summarize_readme(readme_text: str, max_lines: int = 12) -> str:
    if not readme_text:
        return ""
    lines = [ln.strip() for ln in readme_text.splitlines() if ln.strip()]
    return "\n".join(lines[:max_lines])


def _llm_infer_label_map(
    client: OpenAIChatClient,
    dataset_name: str,
    readme_text: str,
    labels: List[int],
    allow_guess: bool,
    language: str = "zh",
) -> Dict[str, Any]:
    labels_text = ", ".join([str(x) for x in labels]) if labels else "(unknown)"
    readme = readme_text.strip() or "(README is empty / missing)"

    instruction = (
        "请根据下面提供的 README 内容推断这个 UCR 时间序列分类数据集的 label 含义。"
        "如果 README 里没有足够信息，请把对应 label 的值写成 \"unknown\"。"
        "除非 allow_guess=true，否则不要凭空猜测。"
    )
    # Explicitly asking for JSON output for the Structured Output logic
    output_spec = (
        "Output ONLY valid JSON object with fields: "
        "label_map (dict of str->str), notes (str), confidence (str)."
    )

    user_prompt = f"""
{instruction}

Dataset: {dataset_name}
allow_guess={str(allow_guess).lower()}
Observed labels: [{labels_text}]

README:
{readme}

{output_spec}
""".strip()

    # Use the new chat_json which supports structured output/JSON mode
    return client.chat_json(user_prompt=user_prompt)


class _LegacyUCRIterWrapper:
    def __init__(
        self,
        *,
        ucr_root: str,
        ucr_name: Optional[str],
        ucr_split: str = "test",
        ucr_label_semantics: str = "readme",
        llm_enabled: bool = False,
        task: str = "classification",
    ) -> None:
        if not ucr_name:
            raise ValueError("ucr2018 requires --ucr_name, e.g., --ucr_name Adiac")

        self.ucr_root = Path(ucr_root).expanduser().resolve()
        self.ucr_name = str(ucr_name)
        self.ucr_split = str(ucr_split).lower()
        self.ucr_label_semantics = str(ucr_label_semantics).lower()
        self.llm_enabled = bool(llm_enabled)
        self.task = task

        self.ds_dir = self.ucr_root / self.ucr_name
        self.train_path = self.ds_dir / f"{self.ucr_name}_TRAIN.tsv"
        self.test_path = self.ds_dir / f"{self.ucr_name}_TEST.tsv"
        self.readme_path = self.ds_dir / "README.md"

        self.readme_text = _load_text(self.readme_path, max_chars=8000)
        self.readme_summary = _summarize_readme(self.readme_text)
        self.label_ids = _collect_labels([self.train_path, self.test_path], max_scan=None)

        self.label_map_source = "none"
        self.label_map: Dict[str, str] = {}

        if self.ucr_label_semantics == "none":
            self.label_map_source = "none"
            self.label_map = {}
        elif self.ucr_label_semantics == "readme":
            self.label_map_source = "readme"
            self.label_map = _parse_label_map_from_readme(self.readme_text)
        elif self.ucr_label_semantics == "llm":
            if not self.llm_enabled:
                raise RuntimeError("ucr_label_semantics=llm requires --llm_label_enabled")
            # Config is handled by global config now, so we just instantiate
            client = OpenAIChatClient(system_prompt="You are a careful assistant.")
            
            try:
                obj = _llm_infer_label_map(
                    client=client,
                    dataset_name=self.ucr_name,
                    readme_text=self.readme_text,
                    labels=self.label_ids,
                    allow_guess=False,
                    language="zh",
                )
                self.label_map_source = "llm"
                self.label_map = obj.get("label_map", {})
                if not isinstance(self.label_map, dict):
                    self.label_map = {}
            except Exception as e:
                logger.error(f"LLM Label inference failed: {e}")
                self.label_map = {}
        else:
            raise ValueError("ucr_label_semantics must be one of: none/readme/llm")

        self._domain_context = {
            "dataset": self.ucr_name,
            "task": "classification",
            "readme_summary": self.readme_summary,
            "readme_path": str(self.readme_path) if self.readme_path.exists() else "",
            "label_map": self.label_map,
            "label_map_source": self.label_map_source,
            "observed_labels": self.label_ids,
        }

    def iter_samples(self) -> Iterator[Dict[str, Any]]:
        splits = self.ucr_split
        paths: List[Tuple[str, Path]] = []
        if splits in ("train", "both"):
            paths.append(("train", self.train_path))
        if splits in ("test", "both"):
            paths.append(("test", self.test_path))
        if not paths:
            raise ValueError("--ucr_split must be train/test/both")

        for split_name, tsv_path in paths:
            if not tsv_path.exists():
                logger.warning(f"Split file missing: {tsv_path}")
                continue
            idx = 0
            for row in _iter_tsv_rows(tsv_path):
                idx += 1
                try:
                    label = int(float(row[0]))
                except (ValueError, IndexError):
                    label = None

                # Strict float parsing with nan filling
                values_1d = [_safe_float(x) for x in row[1:]]
                values_1d = _fill_nan_1d(values_1d)
                
                T = len(values_1d)
                # If T is 0, skip
                if T == 0:
                     continue
                     
                timestamps = [str(i) for i in range(T)]
                values = [[v] for v in values_1d] # List[List[float]]

                yield {
                    "timestamps": timestamps,
                    "values": values,
                    "series_cols": ["x"],
                    "target_col": "x",
                    "variables_meta": [
                        {"name": "x", "index": 0, "role": "target", "meaning_zh": f"UCR 单变量序列值（{self.ucr_name}）", "unit": None},
                    ],
                    "label": label,
                    "domain_context": self._domain_context,
                    "series_key": f"{self.ucr_name}/{split_name}/{idx:06d}",
                    "indices": None,
                }

class UCRWrapper(BaseWrapper):
    def __init__(self, cfg: WrapperConfig):
        super().__init__(cfg)
        self._impl = _LegacyUCRIterWrapper(
            ucr_root=cfg.input_path,
            ucr_name=cfg.ucr_name,
            ucr_split=cfg.ucr_split,
            ucr_label_semantics=cfg.ucr_label_semantics,
            llm_enabled=cfg.llm_enabled,
            task=cfg.task
        )

    def iter_samples(self) -> Iterator[Dict[str, Any]]:
        return self._impl.iter_samples()