# Natural QCC v2.2 Token-Budget Fix 下一轮测试诊断（2026-05-20）

## 结论

这轮测试把问题推进了一层：

1. **token-budget 主因已被验证并修复**：旧配置 `max_text_length=224` 会被新的 preflight hard gate 拦下；新配置 `max_text_length=768, max_prompt_length=384` 下，v2.2 qcond 训练集不再发生 prompt/output 截断。
2. **空生成问题已解除**：5-example qcond overfit 生成 5 条，empty caption rate 从上一轮的 `1.0000` 变成 `0.0000`。
3. **但 5-example overfit 没有严格通过**：caption quality 通过，semantic QA 为 `0.8000`，但 slot factuality 只有 `0.2000`。模型能生成像 evidence 的文本，但数值 grounding 仍明显不准。

因此本轮结论不是“v2.2 已修好”，而是：

> 第一层训练协议 bug 已定位并修复：target caption 确实进入 loss 了；下一层主要问题是小样本 overfit 仍不能稳定复制关键数值，尤其是 correlation / extrema / half-window 数值。

## 改动

### 1. Preflight 增加 token-budget hard gate

修改：

`scripts/eval/check_natural_qcc_gpu_smoke_preflight.py`

新增检查项：

- `prompt_full_tokens`
- `prompt_kept_tokens`
- `prompt_truncated`
- `output_full_tokens`
- `output_kept_tokens`
- `output_truncated`
- `labels_non_ignored`
- `needed_tokens`
- `supervised_text_preview`

默认要求：

- `zero_output_kept == 0`
- `output_truncated == 0`
- `prompt_truncated == 0`
- `eos_only_supervision == 0`

也就是说，target caption 不允许再被静默截断。

### 2. Runner 暴露训练长度和小样本参数

修改：

`scripts/train/run_natural_qcc_gpu_smoke.py`

新增参数：

- `--max_text_length`
- `--max_prompt_length`
- `--max_train_samples`
- `--max_eval_samples`
- `--generate_limit`
- `--qa_splits`
- `--allow_output_truncation`
- `--allow_prompt_truncation`

这让我们可以用同一个正式 pipeline 做 5-example overfit，而不是写一条临时训练路径。

### 3. 新增远程诊断脚本

新增：

`scripts/remote/run_natural_qcc_v22_tokenfix_overfit5_3090.sh`

运行配置：

| item | value |
| --- | ---: |
| train samples | `5` |
| eval samples | `5` |
| generation limit | `5` |
| epochs | `20` |
| max text length | `768` |
| max prompt length | `384` |
| max new tokens | `160` |
| QA splits | `train dev` |

结果目录：

`.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/numeric_grounding_repair_v22_20260520/token_budget_fix_diagnostics_20260520/qcond_overfit5_maxtext768_qwen3_4b/`

## Preflight 结果

### 旧配置：预期失败

文件：

`token_budget_fix_diagnostics_20260520/preflight_expected_fail_224.json`

关键结果：

| metric | value |
| --- | ---: |
| max text length | `224` |
| max prompt length | `320` |
| train rows | `89` |
| zero output kept | `89` |
| output truncated | `89` |
| eos-only supervision | `89` |
| prompt truncated | `2` |
| token budget pass | `false` |
| preflight pass | `false` |

这证明新 gate 能拦住上一轮导致空输出的配置。

### 新配置：预期通过

文件：

`token_budget_fix_diagnostics_20260520/preflight_expected_pass_768.json`

关键结果：

| metric | value |
| --- | ---: |
| max text length | `768` |
| max prompt length | `384` |
| train rows | `89` |
| zero output kept | `0` |
| output truncated | `0` |
| prompt truncated | `0` |
| eos-only supervision | `0` |
| mean prompt tokens | `247.85` |
| mean output tokens | `68.27` |
| max needed tokens | `394` |
| token budget pass | `true` |
| preflight pass | `true` |

这说明 `768/384` 对当前 v2.2 qcond 数据足够宽，target caption 完整进入监督信号。

## 5-example Overfit 结果

运行目录：

`token_budget_fix_diagnostics_20260520/qcond_overfit5_maxtext768_qwen3_4b/`

### 生成形态

| metric | value |
| --- | ---: |
| generated rows | `5` |
| empty caption rate | `0.0000` |
| mean caption chars | `285.0` |

这说明“prompt 后立刻 EOS”的问题已经解除。

### Caption quality

| metric | value |
| --- | ---: |
| quality gate pass | `true` |
| evidence shape rate | `1.0000` |
| numeric evidence rate | `1.0000` |
| answer-label-only rate | `0.0000` |
| option letter leak rate | `0.0000` |

模型不再输出空字符串，也没有退化为只输出答案标签。

### Semantic QA

| metric | value |
| --- | ---: |
| rows | `5` |
| semantic QA accuracy | `0.8000` |
| empty answer rate | `0.0000` |

按 task family：

| task family | n | accuracy |
| --- | ---: | ---: |
| `aiops_official_cross_signal_relation` | `2` | `0.5000` |
| `aiops_official_memory_extrema` | `2` | `1.0000` |
| `aiops_official_window_memory` | `1` | `1.0000` |

语义答案多数能对上，但 cross-signal relation 仍有一条错。

### Slot factuality

| metric | value |
| --- | ---: |
| rows | `5` |
| slot value pass rate | `0.2000` |
| slot value recall | `0.6000` |
| direction pass rate | `0.7500` |
| horizon pass rate | `1.0000` |
| overall slot factuality | `0.2000` |

失败原因：

| reason | count |
| --- | ---: |
| `slot_value_mismatch` | `4` |
| `direction_mismatch` | `1` |

这说明当前不是生成协议仍空，而是数值拷贝/计算不稳定。

## 具体失败样例

### cross-signal relation 记错相关系数

Gold target：

```text
CPU-memory correlation is 0.000, and network receive/transmit correlation is 0.000.
Therefore, neither telemetry pair reaches usable coupling.
```

Generated：

```text
CPU-memory correlation is 0.000, and network receive/transmit correlation is 1.002.
Therefore, network rx-tx coupling.
```

问题：模型把另一条样本的网络相关系数模式迁移过来，生成了不可能的 `1.002`，导致答案方向也错。

### memory extrema 拷贝了别的样本数值

Gold target：

```text
the maximum value is 412,876.80 at local step 2
```

Generated：

```text
the maximum value is 798,720.00 at local step 2
```

问题：local step 和 early/middle/late 方向对了，但 extrema value 是另一个样本的数值。

### window memory 用自然词替代数值

Generated：

```text
first-half mean is 798,720.00, second-half mean is same, and second-minus-first difference is +0.0
```

语义上能答对，但 slot factuality 不接受 `same` 替代明确数值，因此 slot value 失败。

## 当前判断

本轮给出两个可靠判断：

1. **上一轮 qcond 全空生成确实主要由 token-budget 截断造成**。修复预算后，5-example generation 已非空，caption quality 过关。
2. **即便 target 完整进入 loss，当前 TS-RLM/Qwen smoke recipe 仍不能严格 overfit 5 条数值证据**。这说明下一步不应直接跑完整 89/35，而应先继续做小样本机制诊断。

## 下一步建议

不要立即跑完整 89/35。建议先做两件更小的诊断：

1. **保存 token-level generation trace**
   - `first_new_token_id`
   - `decoded_raw_skip_special_false`
   - `decoded_new_tokens_skip_special_false`
   - `decoded_new_tokens_skip_special_true`
   - 是否第一步 EOS
   - 是否重复 continuation 被 cleaner 截断

2. **做 save-load parity / before-save generation**
   - 训练后、保存前生成 5 条；
   - reload 后生成同 5 条；
   - 如果 before-save 明显好而 reload 后差，查 checkpoint / LoRA load；
   - 如果二者都数值错，查模型容量、prefix bridge、target 数值拷贝机制。

3. **做 1-example overfit**
   - 只用一条 `aiops_official_cross_signal_relation`；
   - 训练到能逐字复制目标；
   - 如果 1-example 都不能复制数值，优先查 generation/save-load；
   - 如果 1-example 能复制，5-example 失败就是小数据多样本互相干扰/数值记忆混淆。

4. **考虑降低目标难度**
   - 先训练只输出一条 `Evidence:` clause；
   - 或者把数值字段做成更短、更规则的 canonical evidence；
   - 等 1/5-example 过了，再恢复完整 `Evidence / Decision rule / Therefore` 格式。

## 本轮状态

本轮达成：

- token-budget hard gate 已实现；
- 旧错误配置会 fail；
- 新预算配置会 pass；
- qcond 5-example overfit 已真实跑完；
- 空生成问题解除；
- 下一层 grounding failure 已定位。

本轮未达成：

- 5-example strict overfit 未通过；
- slot factuality 未达标；
- 因此不应启动完整 89/35 smoke 作为效果验证。

