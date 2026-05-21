# Self-contained Reasoning TSQA Data-only GPT Probe（2026-05-21）

本 probe 只给 LLM 自足背景、变量、决策规则、四选项和物理量时序表，不给 evidence caption 或 support slots。

## 总览

- model: `gpt-5.4-mini`
- rows: `8/8`
- strict letter accuracy: `0.875`
- semantic answer accuracy: `0.875`
- mean latency: `3.415s`
- needs full series: `0`

## By Source

| source | n | letter correct | letter acc | semantic correct | semantic acc |
| --- | ---: | ---: | ---: | ---: | ---: |
| `aiopslab` | 4 | 3 | 0.75 | 3 | 0.75 |
| `grid2op` | 3 | 3 | 1.0 | 3 | 1.0 |
| `water` | 1 | 1 | 1.0 | 1 | 1.0 |

## Semantic Wrong / Risk Cases

| source | task | gold | pred | reason |
| --- | --- | --- | --- | --- |
| `aiopslab` | `self_contained_aiops_symptom_triage` | D / no dominant symptom | A / memory leak pattern | First-half mean x1 = 9.32182e+06 and second-half mean x1 = 9.43837e+06, a rise of about 1.25%, which is below the 15% memory threshold. Max x2 = 1.26338, max x3 = 1.31441, and max x0 = 0.418642, all below their respective thresholds. So no dominant symptom applies, but since the memory rule has priority only when x1 grows by at least 15%, that condition is not met; the correct choice is D. However, the sampled table shows no threshold met, so the available data is sufficient. |

## Letter / Label Mismatches

| source | task | gold | returned letter | returned label | letter label |
| --- | --- | --- | --- | --- | --- |
| - | - | - | - | - | 无 |
