import json
from typing import Any, Dict, List

SYSTEM_PROMPT_TEMPLATE = """
You are an expert Time Series Analyst with deep domain knowledge. Your task is to generate high-quality, factual, and structured textual descriptions for time series data.

### Task Overview
I have pre-identified specific time segments ("Target Segments") that contain important patterns. You must describe these segments based *strictly* on the provided statistical facts.

### IMPORTANT ABOUT TIME
- Each segment includes index-based boundaries: start/end.
- If the payload provides timestamp strings (e.g., t_start/t_end), you should prefer referencing those timestamps in the narrative (you may still mention indices if helpful).
- Do NOT invent timestamps or time formats that are not provided.

### 1. Style & Formatting Guidelines (CRITICAL)
* **Rounding**:
    * Round raw values (start/end/mean) to **2-4 significant digits** (e.g., 1.374884 -> 1.37).
    * Round percentages (delta_pct) to **1 decimal place** (e.g., 298.443% -> 298.4%).
    * Round Z-scores to **1-2 decimal places** (e.g., z=1.70).
    * **Do NOT** output overly precise numbers like "1.6925881".
* **Tone**: Professional, objective, and analytical.
* **Bilingual**: Provide both **Chinese (zh)** and **English (en)** for every text field.
* **No Hallucination**: Do not invent numbers or events not present in the input data.

### 2. Output Structure Requirements
Generate a JSON object containing strictly the following keys:

1.  **"global_summary"**:
    * A holistic description of the series behavior.
    * Cover overall trend, seasonality (period/strength), volatility, and key extremes.
    * *Do not* focus on domain background here; keep it statistical.

2.  **"domain_summary"**:
    * Merge the **Domain Context** (if available) with the **Statistical Facts**.
    * Explain what the patterns represent in the real world (e.g., "The sharp drop likely corresponds to a sensor failure...").
    * If no domain context is provided, summarize the statistics naturally.

3.  **"local_captions"**:
    * I provided a list of `TASKS_TARGET_SEGMENTS` with unique `segment_id`s.
    * You must generate a description for **EACH** segment in that list.
    * **CRITICAL**: You must include the `segment_id` in your output so I can map it back.
    * Do NOT change the start/end indices.

### JSON Output Schema
{
  "global_summary": {"zh": "...", "en": "..."},
  "domain_summary": {"zh": "...", "en": "..."},
  "local_captions": [
    {
      "segment_id": 0,
      "description": {
        "zh": "...",
        "en": "..."
      }
    }
  ]
}
"""

def build_user_prompt(
    meta: Dict[str, Any],
    features: Dict[str, Any],
    claims: List[Dict[str, Any]],
    domain_context: Dict[str, Any],
    target_segments: List[Dict[str, Any]],
) -> str:
    """
    Constructs the user message payload.
    """

    # Claims：保留必要字段；时间信息(t_*)保留，方便 LLM 在有真实 timestamp 时引用
    clean_claims: List[Dict[str, Any]] = []
    for c in claims:
        if c.get("ok") is False:
            continue
        clean_claims.append(
            {
                "type": c.get("type"),
                "target": c.get("target"),
                "start": c.get("start"),
                "end": c.get("end"),
                "idx": c.get("idx"),
                "t_start": c.get("t_start"),
                "t_end": c.get("t_end"),
                "t_idx": c.get("t_idx"),
                "data": c.get("data"),
            }
        )

    # Features：保持精简
    clean_features = {
        "trend": features.get("trend"),
        "seasonality": features.get("seasonality"),
        "volatility": features.get("volatility"),
    }

    # Domain Context
    domain_info_str = "Unknown / Generic Time Series"
    if domain_context:
        readme = domain_context.get("readme_summary") or domain_context.get("description")
        if readme:
            domain_info_str = readme

    payload = {
        "dataset_name": meta.get("dataset"),
        "task": meta.get("task"),
        "series_key": meta.get("series_key"),
        "indices": meta.get("indices"),
        "time_kind": meta.get("time_kind"),  # "timestamp" or "index"
        "t_start": meta.get("t_start"),
        "t_end": meta.get("t_end"),

        "domain_background_info": domain_info_str,

        "statistical_features": clean_features,

        # [核心任务] 目标片段（已包含 start/end 以及可选 t_start/t_end）
        "TASKS_TARGET_SEGMENTS": target_segments,

        "supporting_facts_claims": clean_claims,
    }

    return json.dumps(payload, ensure_ascii=False, indent=2)
