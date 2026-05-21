# Grid2Op 中等长度时序 QA 案例分析

这个目录保存当前 Grid2Op TS-QA pilot 的 GitHub 可读中文案例分析报告。

- [grid2op_case_study.md](grid2op_case_study.md)：带折叠面板的中文报告，包含时序图、QA 问题、caption（说明文本）与 evidence（证据）、各方法回答。
- `figures/`：4 个单轨迹观测案例和 1 个 factual/counterfactual（事实/反事实）配对案例的 PNG 时序图。
- `selected_cases.json`：被选中的 QA 记录和案例说明。
- `manifest.json`：供后续脚本使用的紧凑 manifest。

这组案例支持当前论文 framing：question-conditioned（问题条件化）、verifiable（可验证）的 evidence caption（证据说明文本）是更短且更可靠的接口；generic caption（通用说明文本）和 sampled numbers prompt（采样数值提示文本）在定位、聚合和配对轨迹比较任务上会出现明显失败。
