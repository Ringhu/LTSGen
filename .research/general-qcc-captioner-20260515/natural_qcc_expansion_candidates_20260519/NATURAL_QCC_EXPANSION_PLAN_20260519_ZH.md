# Natural QCC 扩展候选计划（2026-05-19）

## 目的

balanced8 pilot 已经证明 natural evidence caption 可以接回 QA 评估，但 43 条 reviewer-positive 样本不足以支撑 QCC 训练结论。下一步需要从 MultiSim v5 的完整 source JSONL 中选出更大的候选池，再做自然化改写和 GPT-5.5 reviewer gate。

## 当前本地运行结果

命令：

```bash
python3 scripts/generate/select_natural_qcc_expansion_candidates.py --per_source 100
```

本地结果：

| 项目 | 数值 |
| --- | ---: |
| 本地可读取 source | 1 |
| 本地 selected rows | 25 |
| missing source files | 15 |
| selection complete | false |

本机只存在 `aiopslab_official_v3` 的 source JSONL，因此只物化了 25 条 AIOps 数值时序候选；Grid2Op、CityLearn、FinRL、water、traffic 的源文件在当前 checkout 不存在，但路径已记录在 manifest 中。

本轮进一步把 `aiops_official_faulty_service_context` 和 `aiops_official_fault_layer_context` 从主候选池剔除。原因是它们依赖官方 incident metadata，而不是由当前时序窗口和领域规则推理得到；这类问题可以单独做 metadata/context split，但不应混入主 natural QCC 训练池。

## 当前 AIOps 子集闭环结果

在本地可读取的 AIOpsLab v3 子集上，后续步骤已经实际跑通：

| 阶段 | 结果 |
| --- | --- |
| natural rewrite | 25 条候选全部改写为自然场景、自然问题、双语选项和自然 evidence |
| GPT-5.5 reviewer | 25/25 reviewed，`keep=25`，`accuracy_risk=low=25`，positive gate `25/25` |
| dataset/SFT | 25 条 positive、0 excluded，dev/test/train=`5/10/10`，`schema_gate_pass=true` |
| baseline/probe | `natural_oracle=1.0000`，`generic_caption=0.0000`，`statistical_caption=0.0000`，`question_only=0.2000` |
| nearest probe | question-conditioned/no-question 均为 `1.0000`，说明这个单源小子集可被近邻记忆解决 |
| GPU preflight | 数据、bridge 和 evaluator 通过；本机缺 Qwen3-4B、`torch/transformers/peft` 和 CUDA |
| GPU runner | `run_natural_qcc_gpu_smoke.py --dry_run` 已写出 preflight/train/generate/QA 命令计划 |

这些结果说明新构造方式已经能生成可评估、可训练格式的数据资产；但还不能说明 QCC 训练收益，因为没有真正 GPU SFT，也没有跨域 reviewer-positive 数据。

## 产物

| 资产 | 路径 |
| --- | --- |
| selector 脚本 | `scripts/generate/select_natural_qcc_expansion_candidates.py` |
| candidate JSONL | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_candidates_20260519/natural_qcc_expansion_candidates.jsonl` |
| candidate SFT JSONL | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_candidates_20260519/natural_qcc_expansion_candidates_sft.jsonl` |
| manifest | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_candidates_20260519/natural_qcc_expansion_candidates_manifest.json` |
| selector report | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_candidates_20260519/NATURAL_QCC_EXPANSION_CANDIDATES_20260519_ZH.md` |
| natural rewrite 脚本 | `scripts/generate/build_natural_qcc_expansion_rewrites.py` |
| natural rewrite JSONL | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519/natural_qcc_expansion_rewrites.jsonl` |
| natural rewrite lint | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519/natural_qcc_expansion_rewrites_lint.json` |
| natural rewrite report | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519/NATURAL_QCC_EXPANSION_REWRITES_20260519_ZH.md` |
| GPT-5.5 reviewer 脚本 | `scripts/generate/review_natural_qcc_expansion_rewrites.py` |
| reviewer-positive dataset builder | `scripts/generate/build_natural_qcc_expansion_dataset.py` |
| GPT-5.5 reviewer report | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519/NATURAL_QCC_EXPANSION_REVIEW_20260519_ZH.md` |
| reviewer JSON | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519/natural_qcc_expansion_rewrites_review.json` |
| positive dataset/SFT | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/` |
| baseline/probe report | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/probe_eval/NATURAL_QCC_PROBE_RESULTS_20260519_ZH.md` |
| GPU dry-run plan | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/tsrlm_natural_qcc_expansion_smoke_qwen3_4b_20260520/natural_qcc_smoke_pipeline_plan.json` |

## 数据机器上应执行的命令

在包含完整 MultiSim v5 source JSONL 的 A100/3090 数据环境运行：

```bash
python3 scripts/generate/select_natural_qcc_expansion_candidates.py \
  --schema .research/general-qcc-captioner-20260515/multisim_qcc_v5_aiops_v3/schema_report.json \
  --out_dir .research/general-qcc-captioner-20260515/natural_qcc_expansion_candidates_20260519 \
  --per_source 100 \
  --seed 55

python3 scripts/generate/build_natural_qcc_expansion_rewrites.py \
  --input_jsonl .research/general-qcc-captioner-20260515/natural_qcc_expansion_candidates_20260519/natural_qcc_expansion_candidates.jsonl \
  --out_dir .research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519

python3 scripts/generate/review_natural_qcc_expansion_rewrites.py \
  --input_jsonl .research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519/natural_qcc_expansion_rewrites.jsonl \
  --review_json .research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519/natural_qcc_expansion_rewrites_review.json \
  --review_md .research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519/NATURAL_QCC_EXPANSION_REVIEW_20260519_ZH.md \
  --model gpt-5.5

python3 scripts/generate/build_natural_qcc_expansion_dataset.py \
  --natural_jsonl .research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519/natural_qcc_expansion_rewrites.jsonl \
  --review_json .research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519/natural_qcc_expansion_rewrites_review.json \
  --raw_jsonl .research/general-qcc-captioner-20260515/natural_qcc_expansion_candidates_20260519/natural_qcc_expansion_candidates.jsonl \
  --out_dir .research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519
```

完成条件：

- `missing_files` 为空，或只剩明确不参与的 source；
- Grid2Op、CityLearn、FinRL、water、traffic 每个 source 选出 100 条；
- AIOpsLab v3 由于原始数据小，且 metadata/context lookup 已排除，预期最多约 25 条数值时序候选；
- candidate pool 覆盖 trend、extrema、volatility、anomaly、periodicity、window/cross-variable、lead-lag、counterfactual、domain-context；
- dataset builder 的 `schema_gate_pass` 为 `true`，并输出 `train/dev/test` split-specific raw/SFT 文件。

## 后续步骤

1. 在数据机器上重跑 selector，补齐 Grid2Op、CityLearn、FinRL、water、traffic 的候选。
2. 对 candidate JSONL 跑 `build_natural_qcc_expansion_rewrites.py`，保持 gold answer 和 support slots 不变。
3. 对自然化结果跑 GPT-5.5 reviewer gate，只保留 `decision=keep`、自然性和可答性均不低于 4、`accuracy_risk=low` 的样本。
4. 用 `build_natural_qcc_expansion_dataset.py` 把 reviewer-positive 样本重建为 train/dev/test natural QCC 数据和 SFT 文件。
5. 重新跑 `natural_oracle/generic/statistical/question_only` baseline，并检查 nearest q/noq 是否仍然持平。
6. 再启动 `run_natural_qcc_gpu_smoke.py` 或扩展版正式 SFT，产出 generated caption 后用 QA evaluator 判断是否相对旧流程提升。
