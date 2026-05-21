# Self-contained Reasoning TS-QA v3（2026-05-21）

## 这版修了什么

v3 保留 v2 的自包含题面、规则、选项、gold 和 support slots，只清洗 caption 训练目标。
核心变化是：`target_caption/output` 不再写 `Answer label`，也不再使用 `the rule maps this to` 这种规则执行模板。

## 规模

- 总样本：60
- 分域：{'grid2op': 10, 'citylearn': 10, 'traffic': 10, 'water': 10, 'aiopslab': 10, 'finrl': 10}

## 清洗检查

| phrase | count in target/evidence |
| --- | ---: |
| `Answer label` | 0 |
| `the rule maps this to` | 0 |
| `按规则判断为` | 0 |
| `supports the answer` | 0 |

## 产物

- QA JSONL: `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/self_contained_reasoning_tsqa.jsonl`
- SFT JSONL: `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/self_contained_reasoning_tsqa_sft.jsonl`
- summary: `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/self_contained_reasoning_tsqa_summary.json`

