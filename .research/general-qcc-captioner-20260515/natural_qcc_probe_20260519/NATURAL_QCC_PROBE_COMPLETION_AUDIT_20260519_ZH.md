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
| 下一批自然化候选池选择 | `scripts/generate/select_natural_qcc_expansion_candidates.py`；本地 manifest 在 `natural_qcc_expansion_candidates_20260519/` | 已完成选择器，本地只物化 AIOps 数值时序候选 |
| 扩展候选自然化改写 | `scripts/generate/build_natural_qcc_expansion_rewrites.py`；本地 25 条 AIOps 候选已写入 `natural_qcc_expansion_rewrites_20260519/` | 已完成本地可运行阶段 |
| 扩展 reviewer gate | `natural_qcc_expansion_rewrites_review.json`；GPT-5.5 审查 25/25，`keep=25`，`accuracy_risk=low=25`，positive gate `25/25` | 已完成真实 AIOps 子集 review |
| 扩展 reviewer-positive dataset/SFT builder | `natural_qcc_expansion_dataset_20260519/`；25 条 positive、0 excluded、dev/test/train=`5/10/10`，`schema_gate_pass=true` | 已完成真实 AIOps 子集 dataset |
| 扩展 baseline/probe | `natural_qcc_expansion_dataset_20260519/probe_eval/`；oracle `1.0000`，generic/statistical `0.0000`，question-only `0.2000`，nearest q/noq 均 `1.0000` | 已完成 AIOps 子集 probe，但不能证明 Q-conditioning 收益 |
| 扩展 GPU smoke preflight/dry-run | `natural_qcc_expansion_dataset_20260519/gpu_smoke_preflight.json` 与 `tsrlm_natural_qcc_expansion_smoke_qwen3_4b_20260520/`；数据路径、prefix bridge 和 evaluator 通过，本机缺模型/torch/CUDA | 已完成本机可做的 preflight 与 dry-run |
| 扩展 GPU result audit | `scripts/eval/audit_natural_qcc_gpu_smoke_result.py`；当前未训练 run 的审计状态为 `incomplete_or_blocked`；`tests/eval/test_audit_natural_qcc_gpu_smoke_result.py` 覆盖 incomplete / no-improvement / improvement 三类判定 | 已完成审计入口，等待真实 GPU 输出 |
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
python3 -m py_compile scripts/generate/build_natural_tsqa_balanced8.py scripts/generate/select_natural_qcc_expansion_candidates.py scripts/generate/build_natural_qcc_expansion_rewrites.py
python3 scripts/generate/build_natural_qcc_expansion_rewrites.py
python3 -m py_compile scripts/generate/review_natural_qcc_expansion_rewrites.py
python3 scripts/generate/review_natural_qcc_expansion_rewrites.py --dry-run
python3 -m py_compile scripts/generate/build_natural_qcc_expansion_dataset.py
python3 scripts/generate/build_natural_qcc_expansion_dataset.py --review_json /tmp/natural_qcc_expansion_keep_review_fixture.json --out_dir /tmp/natural_qcc_expansion_dataset_fixture
python3 scripts/generate/build_natural_qcc_expansion_dataset.py --review_json /tmp/natural_qcc_expansion_partial_review_fixture.json --out_dir /tmp/natural_qcc_expansion_dataset_partial_fixture  # expected failure: incomplete reviewer output
python3 scripts/generate/review_natural_qcc_expansion_rewrites.py --max-calls 1
python3 scripts/generate/review_natural_qcc_expansion_rewrites.py
python3 scripts/generate/build_natural_qcc_expansion_dataset.py
python3 scripts/eval/run_natural_qcc_probe.py --data .research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/natural_qcc_expansion_positive.jsonl --out_dir .research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/probe_eval --train_split train --eval_split test
python3 scripts/eval/check_natural_qcc_gpu_smoke_preflight.py --train_sft .research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/sft/natural_qcc_expansion_train_sft.jsonl --eval_sft .research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/sft/natural_qcc_expansion_test_sft.jsonl --eval_raw .research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/sft/natural_qcc_expansion_test_raw.jsonl --gold_jsonl .research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/natural_qcc_expansion_positive.jsonl --out .research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/gpu_smoke_preflight.json  # expected local failure: no torch/CUDA/model path
python3 scripts/train/run_natural_qcc_gpu_smoke.py --dry_run --train_sft .research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/sft/natural_qcc_expansion_train_sft.jsonl --eval_sft .research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/sft/natural_qcc_expansion_test_sft.jsonl --eval_raw .research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/sft/natural_qcc_expansion_test_raw.jsonl --gold_jsonl .research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/natural_qcc_expansion_positive.jsonl --run_dir .research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/tsrlm_natural_qcc_expansion_smoke_qwen3_4b_20260520
python3 scripts/eval/audit_natural_qcc_gpu_smoke_result.py --run_dir .research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/tsrlm_natural_qcc_expansion_smoke_qwen3_4b_20260520 --out /tmp/natural_qcc_gpu_smoke_result_audit_final2.json  # expected failure until GPU run exists
python3 tests/eval/test_audit_natural_qcc_gpu_smoke_result.py
```

## 当前不能宣称完成的部分

1. 还不能说“新数据让 QCC 训练更好”，因为没有完成正式 QCC 模型训练。
2. 还不能说“QA 提升”，因为当前只有 oracle/baseline/nearest-probe，没有 trained captioner 的 heldout 生成。
3. 当前真实扩展数据只覆盖 AIOpsLab 官方 v3 的 25 条数值时序样本；nearest q/noq 都是 `1.0000`，说明这个小子集过于重复，不能报告 Q-conditioning 或训练收益。
4. 本机 preflight 失败：缺少 Qwen3-4B 模型路径、`torch/transformers/peft` 环境，以及可用的大显存 GPU。
5. 本机缺少 Grid2Op、CityLearn、FinRL、water、traffic 的完整 source JSONL；每域扩展候选池需要在数据机器上重跑 selector、natural rewrite、reviewer gate 和 dataset builder。
6. AIOps 的 `faulty_service` / `fault_layer` 等 metadata-context lookup 已从主候选池剔除；若后续要保留，应作为单独 metadata/context split，而不是主数值时序 QCC 训练样本。
7. 已有真实 AIOps positive 数据和 SFT 文件，但还没有在 GPU 上得到 generated caption，也没有 generated-caption QA accuracy。

## 下一步 gate

进入正式训练前，需要先完成：

- 每个 source `50-100` 条 reviewer-positive 样本。
- 真正的 `train/dev/test` split。
- 主训练池排除依赖隐藏 metadata 的 lookup 题，保留能由时序窗口、领域规则和 support slots 验证的样本。
- dataset builder 的 `schema_gate_pass=true`，并生成可训练的 split-specific SFT 文件。
- reviewer-positive 后重跑 `natural_oracle/generic/statistical/question_only` baseline。
- 在 A100/3090 上先跑 `smoke_sft` 命令，确认 TS-RLM/Qwen 训练链路能读 natural SFT 文件。
