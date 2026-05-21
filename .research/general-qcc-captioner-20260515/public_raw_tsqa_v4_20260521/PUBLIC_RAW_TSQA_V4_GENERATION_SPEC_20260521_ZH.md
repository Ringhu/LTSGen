# Public Raw TSQA v4 Generation Spec（2026-05-21）

本目录实现 `RAW_TSQA_BENCHMARK_STANDARD_20260521_ZH.md`：一份 canonical raw time-series QA 数据，同时导出 LLM text view 和 TS-LLM array view。

## 产物

- `canonical_raw_tsqa_v4.jsonl`：公开 canonical raw-series QA。
- `llm_text_view.jsonl`：普通 LLM 使用的完整时序文本 prompt。
- `tsllm_array_view.jsonl`：TS-LLM / ChatTS-style 模型使用的原始数组 + 文本问题。
- `oracle_evidence.jsonl`：oracle evidence baseline 使用。
- `audit_support.jsonl`：内部审计证据字段、规则 ID、source 信息和 reviewer trace。
- `mismatch_audit.jsonl`：raw verifier 与 v3 gold 不一致而未纳入 public v4 的样本。

## 本批统计

- rows: `39`
- mismatch excluded: `2`
- public forbidden issues: `0`
- by domain: `{"power_grid": 7, "building_energy": 4, "traffic": 4, "water_service": 5, "service_telemetry": 9, "market": 10}`
- answer distribution: `{"C": 3, "B": 4, "A": 19, "D": 13}`
- time-series length: `{'min': 96, 'max': 256}`
- LLM prompt word length: `{'min': 250, 'max': 440, 'mean': 379.26}`
