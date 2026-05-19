# Natural QCC Cross-Domain Objective Completion Audit（2026-05-20）

本审计用于判断当前 active objective 是否已经完成。结论先行：**目标尚未完成**。新的自然 TS-QA 构造、数据资产评估、reviewer gate、SFT 数据准备、训练前 probe、本地弱训练诊断、caption-quality audit、no-question control 准备和 GitHub 同步已经完成；但目标中要求的真实 QCC caption 训练、TS-RLM/Qwen generated-caption 生成、generated-caption QA 提升和 q-conditioned vs no-question 训练对照尚未完成。

因此本轮不能调用 `update_goal(status="complete")`，也不能声称“新的数据已经带来 QCC 训练提升”。

## 目标拆解

用户目标：

> 按照新的构造数据方式重新走一遍之前流程，看结果能否更好；不仅做数据资产评估，还要在 QCC 的想法上做训练，看看新的数据是否适配 caption 任务，以及在 QA 任务上是否能够有所提升。

拆成可检查 deliverables：

1. 用新的自然 TS-QA 构造方式重新走候选选择、自然化、reviewer、positive dataset、SFT 文件准备流程。
2. 做数据资产评估：至少包括 question-only、generic caption、statistical caption、oracle evidence caption 等 baseline/probe。
3. 做 QCC caption 训练：训练一个 question-conditioned captioner，而不只是 oracle/probe。
4. 做 no-question captioner 训练对照，用来判断 question conditioning 是否真的带来训练收益。
5. 生成 trained caption，并用同一 QA 规则评估 generated-caption QA。
6. 审计 generated caption 是否像 evidence caption，而不是只输出答案标签。
7. 判断 QA 是否相对非 oracle baseline 有提升，并判断 q-conditioned 是否超过 no-question。
8. 把产物同步到 GitHub。

## Prompt-to-Artifact Checklist

| requirement | evidence inspected | status |
| --- | --- | --- |
| 新构造方式跨域候选选择 | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_candidates_20260520/natural_qcc_crossdomain_candidates_manifest.json`；selected `n=60`，每个可用 source 各 12 条 | complete for available sources |
| FinRL included if source exists | manifest `missing_files` includes `finrl_broad_scaled_v1_{train,dev,test}.jsonl` missing | blocked, not faked |
| 自然化 rewrite | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_rewrites_20260520/natural_qcc_crossdomain_rewrites.jsonl` and lint report | complete |
| GPT-5.5 reviewer gate | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_rewrites_20260520/natural_qcc_crossdomain_rewrites_review.json`；60 reviewed；55 pass positive gate | complete |
| Positive dataset | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_positive.jsonl`；55 rows | complete |
| Excluded risky rows preserved | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_excluded.jsonl`；5 rows | complete |
| SFT split files | `sft/natural_qcc_crossdomain_{train,dev,test}_{sft,raw}.jsonl`；train/dev/test = 31/11/13 | complete |
| No-question control SFT files | `sft_no_question/natural_qcc_crossdomain_no_question_{train,dev,test}_{sft,raw}.jsonl`；train/dev/test = 31/11/13；top-level prompt `Question:` marker count = 0 | complete |
| Schema gate | `natural_qcc_crossdomain_dataset_summary.json`；`schema_gate_pass=true`，`missing_required_count=0` | complete |
| 数据资产 probe | `probe_eval/natural_qcc_probe_results.json` | complete |
| Oracle evidence QA | `natural_oracle accuracy=1.0000` | complete |
| Non-oracle baselines | `generic_caption=0.0182`，`statistical_caption=0.0000`，`question_only=0.1273` | complete |
| Weak question-conditioned probe | `nearest_caption_question_conditioned=0.4615` vs `nearest_caption_no_question=0.2308` | complete, diagnostic only |
| Caption-adaptation summary | `natural_qcc_caption_adaptation_summary_20260520.json` combines strict QA, semantic QA, and caption-quality metrics; nearest qcond QA gap `+0.2307`, semantic QA gap `+0.2307`, quality gap `-0.1539` | complete diagnostic only |
| Semantic QA bridge diagnostic | `probe_eval/*_semantic_qa/semantic_qa_metrics.json`; deterministic bridge, no LLM judge, does not alter gold | complete diagnostic only |
| Local weak training diagnostic | `local_caption_ranker/qcond/local_caption_ranker_summary.json` and `no_question/local_caption_ranker_summary.json`；both test QA `0.6154` | partial diagnostic |
| Local caption-quality audit | `local_caption_ranker/{qcond,no_question}/natural_qcc_caption_quality_audit.json`；both `evidence_shape_rate=0.0000` and `answer_label_only_rate=1.0000` | complete diagnostic; shows ranker is not evidence-caption training |
| True QCC TS-RLM/Qwen training | GPU smoke audit checks `pipeline_complete=false`，no predictions, no QA metrics | missing |
| No-question TS-RLM/Qwen training control | no-question GPU smoke audit checks `pipeline_complete=false`，no predictions, no QA metrics | missing |
| Generated trained captions | `generate_eval_test_clean/predictions.jsonl` absent in GPU run dir | missing |
| Generated caption-quality audit | `natural_qcc_caption_quality_audit.json` absent in both GPU run dirs | missing |
| Generated-caption QA | `generate_eval_test_clean/rule_qa/qa_metrics.json` absent | missing |
| Claim of QA improvement after training | GPU audit `audit_pass=false` and `claim_scope="No training-result claim allowed."` | missing |
| Q-conditioned vs no-question training comparison | `tsrlm_natural_qcc_crossdomain_qcond_vs_noquestion_audit_20260520.json` status `incomplete_or_blocked` | missing |
| Safe GitHub result sync after GPU | `natural_qcc_gpu_result_manifest_20260520.json` currently `manifest_pass=false` because required GPU result files are absent; `unsafe_path_detected=false` | prepared but incomplete |
| Remote GPU access diagnosis | `natural_qcc_remote_gpu_access_check_20260520.json` shows `any_access_pass=false`; `a100` DNS unresolved, `3090` SSH closed | blocker documented |
| Objective-level completion gate | `natural_qcc_objective_completion_audit_20260520.json` status `incomplete_or_blocked`; blocks on GPU audits, generated metrics, comparison, and manifest | incomplete |
| GitHub sync | current natural-QCC data, audit, launcher, manifest, and remote-access diagnostic artifacts are pushed to `refs/heads/codex/question-repair-20260519-ready`; verify with `git ls-remote origin refs/heads/codex/question-repair-20260519-ready` | complete for current non-GPU artifacts |

## Inspected Metrics

Data asset probe on 55 reviewer-positive rows:

| condition | accuracy | empty |
| --- | ---: | ---: |
| `natural_oracle` | 1.0000 | 0.0000 |
| `natural_evidence_no_label` | 0.6545 | 0.1636 |
| `generic_caption` | 0.0182 | 0.8909 |
| `statistical_caption` | 0.0000 | 1.0000 |
| `question_only` | 0.1273 | 0.7091 |
| `nearest_caption_question_conditioned` | 0.4615 | 0.3846 |
| `nearest_caption_no_question` | 0.2308 | 0.6154 |

Caption-quality audit for evidence-style probe captions:

| diagnostic | evidence shape | answer-label-only | numeric evidence | quality gate |
| --- | ---: | ---: | ---: | ---: |
| `natural_oracle` | 0.9091 | 0.0000 | 0.9091 | `true` |
| `natural_evidence_no_label` | 0.9091 | 0.0000 | 0.9091 | `true` |
| `nearest_caption_question_conditioned` | 0.7692 | 0.0000 | 0.7692 | `false` |
| `nearest_caption_no_question` | 0.9231 | 0.0000 | 0.9231 | `true` |

Semantic QA bridge diagnostic:

| diagnostic | strict QA | semantic QA | semantic empty |
| --- | ---: | ---: | ---: |
| `natural_oracle` | 1.0000 | 1.0000 | 0.0000 |
| `natural_evidence_no_label` | 0.6545 | 1.0000 | 0.0000 |
| `nearest_caption_question_conditioned` | 0.4615 | 0.4615 | 0.3077 |
| `nearest_caption_no_question` | 0.2308 | 0.2308 | 0.6154 |

Local dependency-free ranker diagnostic:

| diagnostic | train QA | test QA | empty |
| --- | ---: | ---: | ---: |
| `local_ranker_qcond` | 0.9677 | 0.6154 | 0.0000 |
| `local_ranker_no_question` | 0.9677 | 0.6154 | 0.0000 |

Local caption-quality audit:

| diagnostic | evidence shape | answer-label-only | numeric evidence | quality gate |
| --- | ---: | ---: | ---: | ---: |
| `local_ranker_qcond` | 0.0000 | 1.0000 | 0.0000 | `false` |
| `local_ranker_no_question` | 0.0000 | 1.0000 | 0.0000 | `false` |

Interpretation:

- 数据资产本身通过了一个 smoke-level gate：oracle 强，generic/statistical/question-only 弱。
- deterministic semantic bridge 显示 `natural_evidence_no_label` 的 strict QA `0.6545` 是过严 label bridge 的低估；自然 evidence 去掉答案标签后仍可被确定性读到 `1.0000`。
- 最近邻 probe 有 question-conditioning QA gap，但 q-conditioned quality gate 未通过；它不是训练出的 QCC captioner。
- 最近邻 q-conditioned/no-question 在 semantic QA 下仍是 `0.4615` / `0.2308`，所以弱探针失败主要来自 evidence retrieval，不是 evaluator 低估。
- 本地弱 ranker 显示数据中有可训练信号，但 q-conditioned 与 no-question 结果完全相同，不能证明 QCC conditioning 成功。
- 本地 ranker 会把预测选项写进 caption；caption-quality audit 明确显示它是答案标签式输出，不等同于 TS-RLM/Qwen 自然 evidence caption 训练。

No-question GPU control assets:

| split | qcond SFT rows | no-question SFT rows |
| --- | ---: | ---: |
| train | 31 | 31 |
| dev | 11 | 11 |
| test | 13 | 13 |

No-question control 只移除顶层模型输入 prompt 中的 downstream question，保留相同 values、target caption、gold answer 和 split。该 control 用于训练 no-question captioner，对照 QCC 是否真的利用问题条件。

## GPU Training Audit

GPU smoke run directory:

`.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520/`

Audit file:

`.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520/natural_qcc_gpu_smoke_result_audit.json`

Observed status:

- `audit_pass=false`
- `status=incomplete_or_blocked`
- `preflight_exists=false`
- `pipeline_complete=false`
- `predictions_exist=false`
- `qa_metrics_exists=false`
- `claim_scope="No training-result claim allowed."`

Local preflight:

`.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/gpu_smoke_preflight_local.json`

Observed blocker:

- data paths: available
- schema/bridge/evaluator: available
- `torch=false`
- `transformers=false`
- `peft=false`
- `cuda_available=false`
- `has_required_gpu_memory=false`
- `preflight_pass=false`

This means the repository has a runnable training plan, but no completed TS-RLM/Qwen QCC training evidence.

No-question control run directory:

`.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_no_question_smoke_qwen3_4b_20260520/`

Observed status:

- `audit_pass=false`
- `status=incomplete_or_blocked`
- `pipeline_complete=false`
- `predictions_exist=false`
- `qa_metrics_exists=false`

Qcond-vs-no-question audit:

`.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_qcond_vs_noquestion_audit_20260520.json`

Observed status:

- `status=incomplete_or_blocked`
- `qcond_accuracy=null`
- `no_question_accuracy=null`
- `qcond_minus_no_question=null`
- `claim_scope="No q-conditioning training comparison allowed."`

Remote GPU access check:

`.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_remote_gpu_access_check_20260520.json`

Observed status:

- `any_access_pass=false`
- `a100`: `reachable=false`; blocker `ssh: Could not resolve hostname a100`
- `3090`: `reachable=false`; blocker `Connection closed by 0.0.12.18 port 22`

This is a blocker diagnostic only. It confirms why the paired GPU smoke could not be launched from the current workstation, but it does not satisfy any training-result requirement.
If the real GPU host is reachable through a different SSH alias or root path, rerun `scripts/remote/check_natural_qcc_remote_gpu_access.py` with `--profiles`, `--ssh-target`, `--remote-root`, and `--python-path` before launching the paired smoke.

Objective-level completion gate:

`.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_objective_completion_audit_20260520.json`

Observed status:

- `objective_complete=false`
- `status=incomplete_or_blocked`
- blockers: `qcond_gpu_audit_pass`, `no_question_gpu_audit_pass`, `qcond_generated_metrics_present`, `no_question_generated_metrics_present`, `qcond_caption_quality_audit_present`, `no_question_caption_quality_audit_present`, `qcond_vs_no_question_comparison_complete`, `safe_result_manifest_pass`

This gate is the final close-out check for the active objective. It only passes when data assets, q-conditioned GPU training, no-question GPU training, generated-caption QA, generated-caption quality audit, paired comparison, and safe result manifest are all complete. Passing the data/probe/local diagnostics alone is intentionally insufficient.

## Commands Needed To Finish The Objective

Run on an accessible GPU host:

```bash
PROFILE=a100 scripts/remote/run_natural_qcc_crossdomain_pair_a100.sh
```

or:

```bash
PROFILE=3090 scripts/remote/run_natural_qcc_crossdomain_pair_a100.sh
```

Or launch remotely from this workstation after SSH access is restored:

```bash
PROFILE=a100 scripts/remote/launch_natural_qcc_crossdomain_pair_ssh.sh
```

or:

```bash
PROFILE=3090 scripts/remote/launch_natural_qcc_crossdomain_pair_ssh.sh
```

The SSH launcher fetches, checks out, and fast-forwards `codex/question-repair-20260519-ready` on the remote host before running the paired GPU smoke command.
It does not push training results unless `PUSH_RESULTS=1` is explicitly set. With `PUSH_RESULTS=1`, it first runs `scripts/eval/collect_natural_qcc_gpu_result_manifest.py` and commits only the manifest pathspec: preflight, pipeline summary, generated predictions, caption-quality audit, rule-QA metrics, and audit files. Checkpoint/model paths are excluded from the manifest.
The paired runner now also runs caption-quality audit, objective-level gate, and safe manifest close-out after qcond/no-question comparison. The close-out order is `objective -> manifest -> objective -> manifest`, so the final objective gate can see the latest manifest state and the final manifest includes the objective gate JSON/Markdown. With `PUSH_RESULTS=1`, the SSH launcher refreshes the objective gate before collecting and committing the manifest pathspec.

Equivalent explicit commands:

```bash
MODE=qcond PROFILE=a100 scripts/remote/run_natural_qcc_crossdomain_smoke_a100.sh
MODE=no_question PROFILE=a100 scripts/remote/run_natural_qcc_crossdomain_smoke_a100.sh
```

or:

```bash
MODE=qcond PROFILE=3090 scripts/remote/run_natural_qcc_crossdomain_smoke_a100.sh
MODE=no_question PROFILE=3090 scripts/remote/run_natural_qcc_crossdomain_smoke_a100.sh
```

For the q-conditioned run alone, `MODE=qcond` is the default:

```bash
PROFILE=a100 scripts/remote/run_natural_qcc_crossdomain_smoke_a100.sh
```

Then rerun the single-run audits:

```bash
python3 scripts/eval/audit_natural_qcc_gpu_smoke_result.py \
  --run_dir .research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520 \
  --probe_results .research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/probe_eval/natural_qcc_probe_results.json

python3 scripts/eval/audit_natural_qcc_gpu_smoke_result.py \
  --run_dir .research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_no_question_smoke_qwen3_4b_20260520 \
  --probe_results .research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/probe_eval/natural_qcc_probe_results.json
```

Then run caption-quality audits if the paired runner did not already do it:

```bash
python3 scripts/eval/audit_natural_qcc_caption_quality.py \
  --predictions_jsonl .research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520/generate_eval_test_clean/predictions.jsonl \
  --gold_jsonl .research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_positive.jsonl \
  --out .research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520/natural_qcc_caption_quality_audit.json

python3 scripts/eval/audit_natural_qcc_caption_quality.py \
  --predictions_jsonl .research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_no_question_smoke_qwen3_4b_20260520/generate_eval_test_clean/predictions.jsonl \
  --gold_jsonl .research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_positive.jsonl \
  --out .research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_no_question_smoke_qwen3_4b_20260520/natural_qcc_caption_quality_audit.json
```

Then compare q-conditioned against no-question:

```bash
python3 scripts/eval/audit_natural_qcc_gpu_qcond_vs_noquestion.py
```

Finally rerun the objective-level gate:

```bash
python3 scripts/eval/audit_natural_qcc_objective_completion.py
```

When using `scripts/remote/run_natural_qcc_crossdomain_pair_a100.sh`, this final gate and manifest close-out are run automatically after the paired GPU smoke completes.

Minimum evidence required before marking this objective complete:

1. GPU `preflight.json` exists and passes.
2. q-conditioned SFT training finishes and `pipeline_complete=true`.
3. no-question SFT training finishes and `pipeline_complete=true`.
4. Both `generate_eval_test_clean/predictions.jsonl` files exist with positive row counts.
5. Both `generate_eval_test_clean/rule_qa/qa_metrics.json` files exist with positive row counts.
6. Both `natural_qcc_caption_quality_audit.json` files exist with positive row counts.
7. Generated-caption QA is compared against `question_only=0.1273`, `generic_caption=0.0182`, and `statistical_caption=0.0000`.
8. q-conditioned generated-caption QA is compared against no-question generated-caption QA.
9. If generated-caption QA does not improve, q-conditioned does not beat no-question, or caption-quality gate fails, report failure plainly instead of weakening the claim.

## Completion Decision

Current decision: **incomplete**.

What is complete:

- New natural TS-QA construction flow for available sources.
- GPT-5.5 reviewer gate and risky-row exclusion.
- Positive dataset and SFT split preparation.
- No-question control SFT split preparation.
- Data asset baseline/probe.
- Caption-adaptation summary combining QA and caption-quality for oracle, nearest-caption probe, and local ranker.
- Local weak training diagnostic.
- Caption-quality audit for the local weak diagnostic, showing the ranker is not evidence-caption training.
- GitHub sync for the current non-GPU artifacts, including the remote-access diagnostic report.
- Objective-level completion gate added; current result is `incomplete_or_blocked`.

What remains incomplete:

- True TS-RLM/Qwen QCC training.
- True TS-RLM/Qwen no-question control training.
- Generated natural evidence captions from the trained QCC model.
- Caption-quality audit for true trained captions.
- Generated-caption QA evaluation.
- Evidence that trained QCC captions improve QA over non-oracle baselines and no-question control.

Therefore the active goal should remain open until the q-conditioned and no-question GPU smoke trainings, generated-caption quality audits, generated-caption QA audits, and qcond-vs-no-question comparison audit are complete.
