# Natural QCC No-Question Control Assets（2026-05-20）

本目录保留相同 values、gold target caption 和 train/dev/test split，只把模型输入 prompt 中的 downstream question 移除。
用途是训练 no-question captioner，对照 question-conditioned QCC captioner 是否真正利用问题条件。

## Inputs

- source SFT dir: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/sft`
- source run name: `natural_qcc_crossdomain`

## Outputs

- output dir: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/sft_no_question`
- output run name: `natural_qcc_crossdomain_no_question`

## Split Summary

| split | raw rows | sft rows | raw question markers | sft question markers |
| --- | ---: | ---: | ---: | ---: |
| `dev` | 11 | 11 | 0 | 0 |
| `test` | 13 | 13 | 0 | 0 |
| `train` | 31 | 31 | 0 | 0 |

## GPU Usage

Run the no-question control with:

```bash
MODE=no_question PROFILE=a100 scripts/remote/run_natural_qcc_crossdomain_smoke_a100.sh
```

Then compare against the question-conditioned run with:

```bash
python3 scripts/eval/audit_natural_qcc_gpu_qcond_vs_noquestion.py
```

若 no-question 与 q-conditioned 结果相同或更强，应报告为 Q-conditioning gap 不成立，而不是 QCC 成功。
