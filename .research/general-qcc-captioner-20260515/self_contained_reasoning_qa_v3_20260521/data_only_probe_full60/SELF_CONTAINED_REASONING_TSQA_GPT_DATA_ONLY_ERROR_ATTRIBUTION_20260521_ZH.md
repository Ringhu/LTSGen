# Self-contained Reasoning TSQA v3 Data-only Error Attribution（2026-05-21）

本报告只分析 data-only probe 的 semantic wrong 样本。它不是人工最终判定，而是扩增前的错误归因队列。

## 总览

- probe: `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/data_only_probe_full60/self_contained_reasoning_tsqa_gpt_data_only_probe.json`
- semantic wrong: `19`
- classes: `{"reason_does_not_recover_gold": 3, "reason_supports_gold_output_field_wrong": 14, "reason_mentions_gold_but_output_wrong": 2}`

## 类别解释

- `reason_supports_gold_output_field_wrong`：模型 reason 中已经算出或陈述了 gold label，但 JSON `answer/answer_label` 字段填成了别的选项。
- `reason_mentions_gold_but_output_wrong`：reason 提到 gold，但文本中也混有错误判断，需要人工看是否为输出一致性问题。
- `reason_does_not_recover_gold`：reason 没有恢复 gold，优先检查题面、规则阈值、变量定义或样本边界。

## By Domain

| domain | attribution counts |
| --- | --- |
| `aiopslab` | `{"reason_supports_gold_output_field_wrong": 1}` |
| `citylearn` | `{"reason_supports_gold_output_field_wrong": 5, "reason_does_not_recover_gold": 1}` |
| `grid2op` | `{"reason_does_not_recover_gold": 1}` |
| `traffic` | `{"reason_supports_gold_output_field_wrong": 5, "reason_mentions_gold_but_output_wrong": 1}` |
| `water` | `{"reason_does_not_recover_gold": 1, "reason_supports_gold_output_field_wrong": 3, "reason_mentions_gold_but_output_wrong": 1}` |

## 错例队列

| domain | task | gold | pred | class | reason excerpt |
| --- | --- | --- | --- | --- | --- |
| `grid2op` | `self_contained_grid_counterfactual_risk` | C / risk is broadly unchanged | D / manual review needed | `reason_does_not_recover_gold` | From the 12 rows, mean x0 is about 8.92e-06, mean x1 = 0, mean x2 = 0, and max x3 is about 9.68e-06. None of the risk-increase, risk-decrease, or broadly-unchanged thresholds are met, so manual review is needed. |
| `citylearn` | `self_contained_building_net_load_reserve` | A / reserve early | D / balanced reserve | `reason_supports_gold_output_field_wrong` | Compute third means of x3 from the 12 rows: early (0-3) mean = (5.5491+6.82786+6.62549+6.33136)/4 = 6.33345; middle (4-7) mean = (5.48295+5.7858+4.96394+4.31857)/4 = 5.13782; late (8-11) mean = (3.84497+5.15268+5.71735+5 |
| `citylearn` | `self_contained_building_net_load_reserve` | D / balanced reserve | A / reserve early | `reason_supports_gold_output_field_wrong` | Using the compact table as the full sample, split 12 rows into thirds of 4 rows each. Early mean x3 = (4.72424+4.4502+5.06184+5.33063)/4 = 4.89173. Middle mean x3 = (4.25567+3.64772+4.02788+5.1843)/4 = 4.27889. Late mean |
| `citylearn` | `self_contained_building_net_load_reserve` | C / reserve late | D / balanced reserve | `reason_does_not_recover_gold` | The table has 12 rows, so split into thirds of 4 rows each. Early x3 mean = (3.97264+3.6067+4.30417+4.62726)/4 = 4.12769. Middle x3 mean = (3.61712+3.12597+3.78827+5.70718)/4 = 4.05964. Late x3 mean = (6.46833+6.28715+5. |
| `citylearn` | `self_contained_building_net_load_reserve` | A / reserve early | D / balanced reserve | `reason_supports_gold_output_field_wrong` | Split 12 rows into thirds of 4 rows each. Early mean x3 = (5.04724+5.72568+7.29302+7.75964)/4 = 6.456395. Middle mean x3 = (5.83194+4.70383+4.75405+5.66099)/4 = 5.2377025. Late mean x3 = (4.93658+4.56409+4.67638+6.25924) |
| `citylearn` | `self_contained_building_net_load_reserve` | C / reserve late | D / balanced reserve | `reason_supports_gold_output_field_wrong` | Compute third means of x3 from 12 rows: early (0-3) mean = (6.51229+5.78748+4.93203+4.14965)/4 = 5.34536; middle (4-7) mean = (5.30522+5.54988+5.4318+5.3082)/4 = 5.39878; late (8-11) mean = (7.02034+8.35724+8.01674+6.212 |
| `citylearn` | `self_contained_building_net_load_reserve` | A / reserve early | D / balanced reserve | `reason_supports_gold_output_field_wrong` | Split 12 rows into thirds of 4 rows each. Early mean x3 = (4.86008+4.70793+6.11034+7.06837)/4 = 5.68668. Middle mean x3 = (5.68990+3.93810+3.57158+4.66175)/4 = 4.46533. Late mean x3 = (4.64423+4.20862+3.82520+5.09914)/4  |
| `traffic` | `self_contained_traffic_recovery_reasoning` | A / no clear congestion shock | D / congestion persists | `reason_supports_gold_output_field_wrong` | Split 12 rows into thirds of 4 rows each. Pre-event x3 mean = (6.77864+5.64036+6.46284+7.11736)/4 = 6.49980. Event x3 mean = (6.70945+6.33456+6.30680+7.15183)/4 = 6.62566. The increase is 0.12586, which is not more than  |
| `traffic` | `self_contained_traffic_recovery_reasoning` | A / no clear congestion shock | B / congestion recovers | `reason_supports_gold_output_field_wrong` | Split 12 rows into thirds of 4 rows each. Pre-event mean x3 = (7.27736+5.85152+4.40612+5.95514)/4 = 5.872535. Event mean x3 = (6.48735+5.53389+5.15607+5.55414)/4 = 5.6828625, which is not more than pre by 0.50 (it is low |
| `traffic` | `self_contained_traffic_recovery_reasoning` | A / no clear congestion shock | D / congestion persists | `reason_supports_gold_output_field_wrong` | Split 12 rows into thirds: pre = indices 0-3, event = 4-7, post = 8-11. Mean x3 pre = 6.4951, event = 6.7831, post = 6.6656. Event rises above pre by 0.2880, which is not more than 0.50, so by the rule there is no clear  |
| `traffic` | `self_contained_traffic_recovery_reasoning` | A / no clear congestion shock | D / congestion persists | `reason_supports_gold_output_field_wrong` | Split 12 rows into thirds of 4 rows each. Pre-event x3 mean = (5.85789+5.25774+7.19666+7.18339)/4 = 6.37392. Event x3 mean = (5.39891+6.07633+7.51396+6.36954)/4 = 6.33969. Post x3 mean = (5.9306+6.30184+6.64215+6.84471)/ |
| `traffic` | `self_contained_traffic_recovery_reasoning` | A / no clear congestion shock | D / congestion persists | `reason_mentions_gold_but_output_wrong` | Split 12 rows into thirds of 4: pre (0-3), event (4-7), post (8-11). Mean x3 pre = (4.32019+5.29459+6.96668+5.95142)/4 = 5.63322. Mean x3 event = (4.64022+5.91679+6.68803+5.40425)/4 = 5.66232. Event rises by only 0.02910 |
| `traffic` | `self_contained_traffic_recovery_reasoning` | A / no clear congestion shock | C / partial recovery | `reason_supports_gold_output_field_wrong` | Split 12 rows into thirds: pre=0-3, event=4-7, post=8-11. Mean x3 pre=(5.52034+5.24816+3.80213+4.71108)/4=4.82043. Event mean=(5.77234+4.25415+3.6946+5.35514)/4=4.76906. Event minus pre = -0.05138, which is not more than |
| `water` | `self_contained_water_service_recovery` | B / pressure recovers after disturbance | C / stable service | `reason_does_not_recover_gold` | Split into thirds of 4 rows each: pre-event rows 0-3, event rows 4-7, post-event rows 8-11. Pre-event mean x0 = 69.2342; event mean x0 = 58.7522 (more than 2.0 below pre-event); post-event mean x0 = 71.2292, which is not |
| `water` | `self_contained_water_service_recovery` | A / persistent leak pressure risk | B / pressure recovers after disturbance | `reason_supports_gold_output_field_wrong` | Split into thirds of 4 rows each. Pre-event x0 mean = (67.9423+71.4095+74.8087+71.6121)/4 = 71.4431. Event x0 mean = (64.1279+53.3308+53.9591+58.0874)/4 = 57.3763, which is more than 2.0 below pre-event. Post-event x0 me |
| `water` | `self_contained_water_service_recovery` | D / manual review needed | C / stable service | `reason_supports_gold_output_field_wrong` | Split into thirds of 4 rows each. Pre-event x0 mean = (68.3633+68.8554+70.6835+66.2343)/4 = 68.5341. Event x0 mean = (64.2608+64.9675+73.6858+79.2796)/4 = 70.5484. Post-event x0 mean = (83.1473+77.2027+71.8788+70.2222)/4 |
| `water` | `self_contained_water_service_recovery` | C / stable service | D / manual review needed | `reason_mentions_gold_but_output_wrong` | Split 12 rows into thirds: pre-event indices 0-3, event 4-7, post-event 8-11. Pre-event mean x0=72.8182, mean x1=11.9952. Event mean x0=71.4416 (not more than 2.0 below pre-event), mean x1=12.0114. Post-event mean x0=71. |
| `water` | `self_contained_water_service_recovery` | C / stable service | A / persistent leak pressure risk | `reason_supports_gold_output_field_wrong` | Using the 12 rows split into thirds of 4 rows each: pre-event rows 0-3 have mean x0=71.3535, mean x1=11.9535, mean x2=68.8273; event rows 4-7 have mean x0=71.0229, mean x1=12.0253; post-event rows 8-11 have mean x0=72.53 |
| `aiopslab` | `self_contained_aiops_symptom_triage` | D / no dominant symptom | A / memory leak pattern | `reason_supports_gold_output_field_wrong` | First-half mean x1 = 9.34937e+06 and second-half mean x1 = 9.33159e+06, so x1 does not grow by at least 15%. Max x2 = 1.36465, max x3 = 1.33289, and max x0 = 0.414442, all below their thresholds. Therefore no dominant sy |
