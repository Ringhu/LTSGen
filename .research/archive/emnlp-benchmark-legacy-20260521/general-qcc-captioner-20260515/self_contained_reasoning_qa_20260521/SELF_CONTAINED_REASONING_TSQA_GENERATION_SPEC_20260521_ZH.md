# Self-contained Reasoning TSQA Generation Spec（2026-05-21）

本规范针对上一批 review 中暴露的问题：题目太像直接读时序特征，背景依赖 simulator 名称，且部分答案不能只由问题和时序值复现。

## 生成约束

1. 每个样本必须给出自足背景：变量含义、单位或方向性、时间窗口划分、决策规则。
2. 用户可见输入只需要 `scene + decision_rule + variables + question + options + physical-unit time series values`。
3. 不允许要求答题者知道 Grid2Op、CityLearn、AIOpsLab、FinRL 等 simulator 背景。
4. 问题必须需要至少一个派生量或聚合量：均值、分段均值、比例、差值、峰值/中位数比、最大回撤等。
5. support slots 仍用于审计，但不能是唯一能推出答案的信息。
6. 给 TS-LLM/LLM 的 `values` 使用物理量，不使用 z-score 后的归一化值。

## 本批数据

- rows: `60`
- by domain: `{"grid2op": 10, "citylearn": 10, "traffic": 10, "water": 10, "aiopslab": 10, "finrl": 10}`
- answer distribution: `{"C": 8, "B": 5, "A": 31, "D": 16}`
- local gate pass: `True`
