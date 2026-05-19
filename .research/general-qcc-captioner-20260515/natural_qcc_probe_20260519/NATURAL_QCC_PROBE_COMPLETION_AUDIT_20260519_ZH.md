# Natural QCC Probe Completion Audit（2026-05-19）

## 用户目标拆解

用户目标是：用新的自然 QA 构造方式重新走一遍之前流程，判断结果是否更好；不只做数据资产评估，还要继续到 QCC caption 训练，检查新数据是否适配 caption 任务，以及 QA 是否提升。

拆成具体交付项：

| 要求 | 当前证据 | 状态 |
| --- | --- | --- |
| 新构造方式的数据资产评估 | `natural_qcc_probe_positive.jsonl`，43 条 reviewer-positive；`NATURAL_QCC_PROBE_DATASET_20260519_ZH.md` | 已做 pilot |
| 接回 QA baseline 流程 | `probe_eval/natural_qcc_probe_results.json` 和 `NATURAL_QCC_PROBE_RESULTS_20260519_ZH.md` | 已做 pilot |
| 检查 natural evidence caption 是否可被 QA 使用 | `natural_oracle=1.0000`，`natural_evidence_no_label=0.6279` | 已验证接口，但暴露 evaluator 限制 |
| 做 trainable caption 探针 | `nearest_caption_question_conditioned=0.1250`，`nearest_caption_no_question=0.1250` | 已做弱探针 |
| 生成可接 TS-RLM/Qwen 训练的 SFT 资产 | `smoke_sft/natural_qcc_probe_train_dev_sft.jsonl`，`smoke_sft/natural_qcc_probe_eval_test_sft.jsonl`，schema gate pass | 已完成 smoke 资产 |
| 训练后 generated caption 的 QA 评估入口 | `scripts/eval/evaluate_natural_qcc_predictions.py`；`target_caption` sanity 为 1.0000，`generic_caption` sanity 为 0.0233 | 已完成评估入口 |
| GPU smoke 训练/生成/评估命令 | `NATURAL_QCC_GPU_SMOKE_RUNBOOK_20260519_ZH.md` | 已完成 runbook |
| GPU smoke preflight | `scripts/eval/check_natural_qcc_gpu_smoke_preflight.py`；本机报告 `gpu_smoke_preflight.json`，`preflight_pass=false` | 已完成检查，当前机器阻塞 |
| GPU smoke pipeline runner | `scripts/train/run_natural_qcc_gpu_smoke.py`；dry-run 写出 `natural_qcc_smoke_pipeline_plan.json` | 已完成 dry-run |
| 下一批自然化候选池选择 | `scripts/generate/select_natural_qcc_expansion_candidates.py`；本地 manifest 在 `natural_qcc_expansion_candidates_20260519/` | 已完成选择器，本地只物化 AIOps |
| 真正 QCC 模型训练 | 需要 A100/3090 Qwen3-4B 环境；当前本地没有 `/cluster/home/user1/fenghaoran/model/Qwen3-4B-Instruct-2507` | 未完成 |
| 判断 QA 是否相比旧流程提升 | 需要正式 train/dev/test 扩展数据和 trained QCC 生成结果 | 未完成 |

## 已执行命令

```bash
python3 -m py_compile scripts/generate/build_natural_qcc_probe_dataset.py scripts/eval/run_natural_qcc_probe.py
python3 scripts/generate/build_natural_qcc_probe_dataset.py
python3 scripts/eval/run_natural_qcc_probe.py
python3 -m py_compile scripts/generate/build_natural_qcc_probe_dataset.py scripts/eval/run_natural_qcc_probe.py scripts/generate/build_natural_qcc_smoke_sft.py
python3 scripts/generate/build_natural_qcc_smoke_sft.py
python3 -m py_compile scripts/eval/evaluate_natural_qcc_predictions.py
python3 scripts/eval/evaluate_natural_qcc_predictions.py --predictions_jsonl .research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/natural_qcc_probe_positive.jsonl --out_dir .research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/prediction_eval_target_caption --caption_field target_caption
python3 scripts/eval/evaluate_natural_qcc_predictions.py --predictions_jsonl .research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/natural_qcc_probe_positive.jsonl --out_dir .research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/prediction_eval_generic_caption --caption_field generic_caption
python3 -m py_compile scripts/generate/build_natural_qcc_smoke_sft.py scripts/eval/check_natural_qcc_gpu_smoke_preflight.py
python3 scripts/eval/check_natural_qcc_gpu_smoke_preflight.py
python3 -m py_compile scripts/train/run_natural_qcc_gpu_smoke.py
python3 scripts/train/run_natural_qcc_gpu_smoke.py --dry_run
python3 -m py_compile scripts/generate/select_natural_qcc_expansion_candidates.py
python3 scripts/generate/select_natural_qcc_expansion_candidates.py --per_source 100
```

## 当前不能宣称完成的部分

1. 还不能说“新数据让 QCC 训练更好”，因为没有完成正式 QCC 模型训练。
2. 还不能说“QA 提升”，因为当前只有 oracle/baseline/nearest-probe，没有 trained captioner 的 heldout 生成。
3. 当前 balanced8 只有 43 条 positive，且 split 不平衡；AIOps positive 只有 test，没有 train。
4. 本机 preflight 失败：缺少 Qwen3-4B 模型路径、`torch/transformers/peft` 环境，以及可用的大显存 GPU。
5. 本机缺少 Grid2Op、CityLearn、FinRL、water、traffic 的完整 source JSONL；扩展候选池需要在数据机器上重跑 selector。

## 下一步 gate

进入正式训练前，需要先完成：

- 每个 source `50-100` 条 reviewer-positive 样本。
- 真正的 `train/dev/test` split。
- reviewer-positive 后重跑 `natural_oracle/generic/statistical/question_only` baseline。
- 在 A100/3090 上先跑 `smoke_sft` 命令，确认 TS-RLM/Qwen 训练链路能读 natural SFT 文件。
