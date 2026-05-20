# GPT Pro Prompt: Natural QCC v2.2 Training Failure Diagnosis

I am working on a time-series QA research project called LTSGen / General QCC.

The method trains a TS-RLM/Qwen captioner to generate short question-conditioned evidence captions from time-series windows. The evidence caption is then evaluated by deterministic semantic QA and slot-factuality checks. LLMs are allowed to review naturalness, but gold answers and slot facts are deterministic.

Please review the following failure diagnosis. I want you to act as a senior ML/debugging reviewer. Do not decide the gold QA labels. Focus on whether the training/generation protocol diagnosis is correct, and whether there are additional likely failure modes.

## Current Observation

We created a v2.2 numeric-grounding repair for Natural QCC. The target captions themselves pass all deterministic gates:

- target semantic QA accuracy: `1.0000`
- target caption quality gate: `true`
- target evidence shape rate: `1.0000`
- target answer-label-only rate: `0.0000`
- target overall slot factuality: `1.0000`
- target Grid2Op slot factuality: `1.0000`

Then we trained paired qcond/no-question TS-RLM/Qwen3-4B smoke runs on a 3090:

- model: `Qwen/Qwen3-4B`
- bridge: `prefix`
- epochs: `5`
- train/test rows: `89 / 35`
- max_new_tokens at generation: `128`
- clean_max_sentences: `3`
- QA evaluator: deterministic semantic bridge

Both pipelines completed and smoke audits passed.

But generated results failed:

| run | semantic QA | empty caption rate | mean caption chars | caption quality | slot factuality | Grid2Op slot factuality |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| v2.2 qcond | `0.0000` | `1.0000` | `0.0` | `false` | `0.0857` | `0.0000` |
| v2.2 no-question | `0.0000` | `0.1429` | `86.6` | `true` | `0.0857` | `0.0000` |

For qcond, `pred_caption` and `pred_caption_raw` are empty strings for all 35 test examples.

## Relevant Training Collator

The training collator is in `tslm/scripts/train_multisim_v5_smoke.py`.

Important defaults:

```python
max_text_length = 224
max_prompt_length = 320
add_eos = True
```

Encoding logic:

```python
prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"][: self.max_prompt_length]
output_ids = tokenizer(output, add_special_tokens=False)["input_ids"]
reserve = 1 + len(prompt_ids) + (1 if self.add_eos else 0)
output_ids = output_ids[: max(self.max_text_length - reserve, 0)]
ids = [bos_id] + prompt_ids + output_ids
labels = [-100] * (1 + len(prompt_ids)) + output_ids
if self.add_eos:
    ids.append(eos_id)
    labels.append(eos_id)
```

The v2.2 runner did not override `max_text_length`, so it used `224`.

## Token-Budget Diagnostic

Using the same remote environment and `Qwen/Qwen3-4B` tokenizer, I measured how many output tokens remain under the current collator contract:

| dataset | n | min prompt kept | max prompt kept | mean prompt kept | zero output kept | mean output kept | min output kept | max output kept |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v2.1 qcond | `89` | `139` | `232` | `157.64` | `2` | `52.61` | `0` | `71` |
| v2.2 qcond | `89` | `227` | `320` | `247.81` | `89` | `0.00` | `0` | `0` |
| v2.2 no-question | `89` | `185` | `264` | `198.47` | `13` | `27.60` | `0` | `37` |

The v2.2 qcond prompt became longer because it added a grounding checklist and required evidence fields, for example:

```text
Grounding checklist: compute numbers from this specific trace window only; do not reuse numeric facts from other examples. The local window has 64 time steps; if you mention a window length, it must be 64. required evidence fields: CPU-memory correlation, network receive/transmit correlation, threshold comparison, and trusted pair. Keep local-step, half-window, correlation, and counterfactual signs internally consistent with the numbers you report.
```

Example qcond target:

```text
Evidence: in the 64-step local window, CPU-memory correlation is 0.000, and network receive/transmit correlation is 0.000. Decision rule: use absolute correlation; values below 0.30 are not usable, and close usable values are treated as similar. Therefore, neither telemetry pair reaches usable coupling.
```

## Hypothesis

Primary hypothesis:

The v2.2 qcond target captions were fully truncated during SFT because `max_text_length=224` was too small for `BOS + prompt + output + EOS`. Since all qcond rows have `output_tokens_kept=0`, labels contain only EOS after the prompt. The model therefore learns to stop immediately, which explains:

- near-zero train/eval loss,
- all-empty raw generation for qcond,
- no semantic QA signal,
- no slot factuality improvement.

For no-question, prompts are shorter, so some output prefix remains, but only around 27.6 output tokens on average. That explains residual template fragments and wrong/incomplete evidence.

## Questions For You

1. Is this token-budget diagnosis sufficient to explain the qcond all-empty generation?
2. Are there any additional high-probability failure modes I should inspect before rerunning, such as:
   - checkpoint save/load mismatch with trainable-only state,
   - LoRA wrapping order during load,
   - `inputs_embeds` generation behavior,
   - EOS/pad token behavior for Qwen,
   - generation starting from `inputs_embeds` without explicit `input_ids`,
   - cleaning accidentally removing output despite raw captions being empty?
3. What is the minimal next validation experiment?
   - My current plan is:
     - add a token-budget preflight gate;
     - rerun with `max_text_length >= 512`;
     - verify `output_tokens_kept > 0` before training;
     - run 5-example overfit;
     - generate on train set before test set;
     - inspect raw and cleaned generations separately.
4. If you disagree with the diagnosis, what specific evidence would falsify it?
5. If you agree, how would you write the next experiment acceptance criteria?

Please answer in Chinese. Keep the diagnosis actionable and distinguish primary cause from secondary risks.

