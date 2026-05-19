#!/usr/bin/env python3
"""Render simulator data-source case study with concrete time-series figures."""
from __future__ import annotations

import json
import math
from pathlib import Path
from textwrap import dedent

import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw_samples" / "balanced_eval_per_source8.jsonl"
REPAIRED = ROOT.parents[1] / "question_repair_20260519" / "repaired_multisim_v5_balanced8_predictions.jsonl"
FIG_DIR = ROOT / "figures"
OUT_MD = ROOT / "SIMULATOR_SYNTHETIC_DATA_CASE_STUDY_ZH_20260518.md"

for font_path in (
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
):
    if Path(font_path).exists():
        font_manager.fontManager.addfont(font_path)
        plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "Noto Sans CJK JP", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False
        break

SELECTED_IDS = {
    "grid2op": [
        "multisim_qcc_v5_aiops_v3::grid2op::grid2op_broad::rte_case14_realistic_chronic2_trace_2048_nooverflow::w128_384::grid_cross_variable_stress",
        "multisim_qcc_v5_aiops_v3::grid2op::grid2op_broad_cf::h2048_c-1_t512_line1::post769_1025::grid_counterfactual_peak_stress",
        "multisim_qcc_v5_aiops_v3::grid2op::grid2op_broad::rte_case14_realistic_chronic4_trace_2048_nooverflow::w512_1536::grid_temporal_lead_lag",
    ],
    "citylearn": [
        "multisim_qcc_v5_aiops_v3::citylearn::citylearn_broad::citylearn_challenge_2022_phase_1_start6144_h2048_b5::w320_576::city_volatility_total_load",
        "multisim_qcc_v5_aiops_v3::citylearn::citylearn_broad::citylearn_challenge_2022_phase_1_start6144_h2048_b5::w512_768::city_anomaly_total_load",
        "multisim_qcc_v5_aiops_v3::citylearn::citylearn_broad::citylearn_challenge_2022_phase_1_start6144_h2048_b5::w1664_1920::city_window_total_load",
    ],
    "finrl_scaled": [
        "multisim_qcc_v5_aiops_v3::finrl_scaled::finrl_broad::JPM::w0_256::fin_volume_anomaly",
        "multisim_qcc_v5_aiops_v3::finrl_scaled::finrl_broad::GS::w1022_1534::fin_extrema_price",
        "multisim_qcc_v5_aiops_v3::finrl_scaled::finrl_broad::MRK::w2043_2555::fin_drawdown_price",
    ],
    "water": [
        "multisim_qcc_v5_aiops_v3::water::water_broad::water_scenario_025::water_pressure_periodicity",
        "multisim_qcc_v5_aiops_v3::water::water_broad::water_scenario_005::water_leak_counterfactual_pressure",
        "multisim_qcc_v5_aiops_v3::water::water_broad::water_scenario_000::water_event_recovery_context",
    ],
    "traffic": [
        "multisim_qcc_v5_aiops_v3::traffic::traffic_broad::traffic_scenario_011::traffic_speed_periodicity",
        "multisim_qcc_v5_aiops_v3::traffic::traffic_broad::traffic_scenario_020::traffic_speed_queue_lead_lag",
        "multisim_qcc_v5_aiops_v3::traffic::traffic_broad::traffic_scenario_025::traffic_signal_counterfactual_queue",
    ],
    "aiopslab_official_v3": [
        "multisim_qcc_v5_aiops_v3::aiopslab_official_v3::aiopslab_official::port_misconfig_seed0_user-service::case000::aiops_official_window_memory",
        "multisim_qcc_v5_aiops_v3::aiopslab_official_v3::aiopslab_official::scale_pod_zero_seed0_user-service::case005::aiops_official_window_memory",
        "multisim_qcc_v5_aiops_v3::aiopslab_official_v3::aiopslab_official::port_misconfig_seed0_user-service::case000::aiops_official_network_volatility",
    ],
}

DISPLAY = {
    "grid2op": {
        "title": "Grid2Op power-grid trace",
        "zh": "电网运行仿真",
        "vars": ["x0 max line-loading stress", "x1 total demand", "x2 generation margin"],
        "vars_zh": ["x0 最大线路负载压力", "x1 总需求", "x2 发电裕度"],
        "scale_note": "raw_compact_values 保留电网紧凑变量；values 是按窗口标准化后的模型输入。",
    },
    "citylearn": {
        "title": "CityLearn building-energy trace",
        "zh": "建筑能耗仿真",
        "vars": ["x0 total building load", "x1 outdoor/demand context", "x2 solar/auxiliary signal"],
        "vars_zh": ["x0 建筑总负载", "x1 外部/需求上下文", "x2 光伏或辅助信号"],
        "scale_note": "raw_compact_values 来自 CityLearn 建筑负载和外部条件；values 是标准化后的模型输入。",
    },
    "finrl_scaled": {
        "title": "FinRL market trace",
        "zh": "金融市场时序",
        "vars": ["x0 target close price", "x1 equal-weight market index", "x2 trading volume"],
        "vars_zh": ["x0 目标资产收盘价", "x1 等权市场指数", "x2 交易量"],
        "scale_note": "FinRL 使用历史 OHLCV 数据构造，严格说是 market trace，不是因果仿真器。",
    },
    "water": {
        "title": "Water-network trace",
        "zh": "供水系统仿真",
        "vars": ["x0 pressure", "x1 flow", "x2 storage/tank signal"],
        "vars_zh": ["x0 水压", "x1 流量", "x2 蓄水/水箱信号"],
        "scale_note": "water 当前来源是稳定 dataflow 产物；报告中需区分 official simulator 与 fallback/smoke 场景。",
    },
    "traffic": {
        "title": "Traffic-system trace",
        "zh": "交通系统仿真",
        "vars": ["x0 mean speed", "x1 queue length", "x2 occupancy/incidence signal"],
        "vars_zh": ["x0 平均速度", "x1 队列长度", "x2 占有率/事件信号"],
        "scale_note": "traffic 当前来源是稳定 dataflow 产物；可表达周期、拥堵、事故、信号反事实等任务。",
    },
    "aiopslab_official_v3": {
        "title": "AIOpsLab official telemetry",
        "zh": "AIOpsLab 官方遥测",
        "vars": ["x0 CPU load", "x1 memory working set", "x2 network receive", "x3 network transmit"],
        "vars_zh": ["x0 CPU 负载", "x1 内存工作集", "x2 网络接收", "x3 网络发送"],
        "scale_note": "AIOpsLab v3 来自 Prometheus CSV export；当前 case 数少，是规模瓶颈。",
    },
}

TRANSLATIONS = {
    "This is a Grid2Op power-grid window. x0 is maximum line-loading stress over grid lines, x1 is total demand, and x2 is generation margin. A line-loading stress value above 1.0 means overload.": "这是一个 Grid2Op 电网窗口。x0 是跨线路的最大线路负载压力，x1 是总需求，x2 是发电裕度。线路负载压力高于 1.0 表示过载。",
    "This is a Grid2Op power-grid time-series window. x0 is maximum line-loading stress, x1 is total demand, and x2 is generation margin. Stress near or above 1.0 indicates overload risk.": "这是一个 Grid2Op 电网时序窗口。x0 是最大线路负载压力，x1 是总需求，x2 是发电裕度。压力接近或超过 1.0 表示存在过载风险。",
    "This is a CityLearn building-energy window. x0 is total building load, x1 is an outdoor/weather support signal, and x2 is solar-generation support. Higher x0 means higher building demand.": "这是一个 CityLearn 建筑能耗窗口。x0 是建筑总负载，x1 是室外/天气辅助信号，x2 是太阳能发电辅助信号。x0 越高表示建筑需求越高。",
    "This is a CityLearn building-energy time-series window. x0 is total building electrical load, x1 is outdoor or demand context, and x2 is solar or auxiliary context.": "这是一个 CityLearn 建筑能耗时序窗口。x0 是建筑总用电负载，x1 是室外或需求上下文，x2 是太阳能或辅助上下文。",
    "This is a financial-market window for the ticker named in the question. x0 is the target price or return-derived signal, and the task may also use returns, volume, drawdown, or regime evidence.": "这是一个金融市场窗口，股票代码由问题指定。x0 是目标价格或由收益率派生的信号，任务也可能使用收益率、交易量、回撤或市场状态证据。",
    "This is a FinRL market time-series window. x0 is the target asset close price, x1 is an equal-weight market index, and x2 is trading volume. It is historical market trace data, not an intervention simulator.": "这是一个 FinRL 金融市场时序窗口。x0 是目标资产收盘价，x1 是等权市场指数，x2 是交易量。它是历史市场轨迹，不是可干预仿真器。",
    "This is a water-network simulation window. x0 is water pressure, x1 is pipe flow, and x2 is tank storage. Low pressure can indicate service risk; unusually high flow can indicate disruption or leak-like stress.": "这是一个供水网络仿真窗口。x0 是水压，x1 是管道流量，x2 是水箱蓄水量。低水压可能表示供水服务风险；异常高流量可能表示扰动或类似漏水的压力。",
    "This is a water-network time-series window. x0 is pressure, x1 is flow, and x2 is a storage or tank-related signal.": "这是一个供水系统时序窗口。x0 是水压，x1 是流量，x2 是蓄水或水箱相关信号。",
    "This is a traffic simulation window. x0 is mean traffic speed, x1 is queue length, and x2 is lane occupancy. Lower speed and higher queue or occupancy indicate congestion.": "这是一个交通仿真窗口。x0 是平均车速，x1 是队列长度，x2 是车道占有率。更低车速以及更高队列或占有率表示拥堵。",
    "This is a traffic-system time-series window. x0 is mean speed, x1 is queue length, and x2 is occupancy or incident/control context.": "这是一个交通系统时序窗口。x0 是平均速度，x1 是队列长度，x2 是占有率或事故/控制上下文。",
    "This is an AIOpsLab microservice telemetry case. Numeric channels usually include service CPU load, memory working set, network receive rate, and network transmit rate. Application, service, fault-family, and provenance questions require official case metadata rather than inference from numeric telemetry alone.": "这是一个 AIOpsLab 微服务遥测样本。数值通道通常包括服务 CPU 负载、内存工作集、网络接收速率和网络发送速率。应用、服务、故障族和来源问题需要官方 case 元数据，不能只靠数值遥测推断。",
    "Cross-variable rule: compare absolute correlations between the target signal and each companion signal. Use both weak when both correlations are small, and both similar when the correlations are close.": "跨变量规则：比较目标信号与每个候选信号之间的绝对相关系数。当两个相关性都很小时选二者都弱；当二者接近时选二者相近。",
    "Counterfactual rule: the trace describes intervention-minus-factual post-event stress. Positive deviations mean the intervention raises stress; negative deviations mean it lowers stress. Classify the strongest deviation as upward peak, downward dip, or no material change.": "反事实规则：这条轨迹描述事件后的“干预减事实”压力。正偏差表示干预提高压力，负偏差表示干预降低压力。按最强偏差分类为向上峰值、向下跌幅或没有实质变化。",
    "Counterfactual rule: the trace is intervention-minus-factual. Positive x0 means the intervention raises stress relative to factual, negative means it lowers stress. Compare the largest upward and downward deviations after the event.": "反事实规则：这条轨迹是 intervention-minus-factual。x0 为正表示干预后压力高于事实轨迹，为负表示低于事实轨迹。比较事件后的最大上升和最大下降偏差。",
    "Lead-lag rule: compare lagged correlation with zero-lag correlation. Positive lag means x0 leads x1; negative lag means x1 leads x0. If the best lagged correlation is not meaningfully stronger than zero lag, answer no clear lead.": "先后关系规则：比较滞后相关和零滞后相关。正 lag 表示 x0 领先 x1；负 lag 表示 x1 领先 x0。如果最佳滞后相关没有明显强于零滞后相关，就回答没有清晰领先关系。",
    "Lead-lag rule: compare lagged correlations between the two signals. A clear positive lag means the first named signal leads; a clear negative lag means it lags. Near-zero or weak correlations mean no clear lead.": "先后关系规则：比较两个信号之间的滞后相关。明显正 lag 表示第一个被命名的信号领先；明显负 lag 表示它滞后。接近零或相关性较弱表示没有清晰领先关系。",
    "Volatility rule: split the window into first, middle, and final thirds, compute the variability of the named signal in each third, and choose the third with the largest variability. Use similar thirds only when the three variability levels are close.": "波动规则：把窗口分成第一段、中间段和最后一段三等份，计算指定信号在每一段里的变动程度，并选择变动最大的那一段。只有三段变动程度接近时才选择三段相近。",
    "Volatility rule: split the window into early, middle, and late thirds, then compare the standard deviation of the named signal in each third.": "波动规则：把窗口分成早期、中期、后期三段，比较指定信号在三段中的标准差。",
    "Anomaly rule: look for the strongest isolated simulator event or spike in the named signal. Report whether it is in the first, middle, or final third, or say no pronounced event if no isolated event dominates.": "异常规则：寻找指定信号中最强的孤立仿真事件或尖峰。报告它出现在第一段、中间段还是最后一段；如果没有占主导的孤立事件，就回答没有明显事件。",
    "Anomaly rule: locate the strongest isolated spike by robust z-score. Use early, middle, or late according to the spike index; use no pronounced spike when the spike is weak.": "异常规则：用 robust z-score 定位最强孤立尖峰。根据尖峰位置选择早期、中期或后期；尖峰很弱时选择没有明显尖峰。",
    "Window-comparison rule: compare the first-half mean and second-half mean of the named signal. Use similar halves only when the means are close.": "窗口比较规则：比较指定信号前半段均值和后半段均值。只有两者足够接近时才选择前后两半相近。",
    "Extrema rule: split the window into first, middle, and final thirds, then locate where the named signal reaches the requested highest or lowest point.": "极值规则：把窗口分成第一段、中间段和最后一段三等份，然后定位指定信号在何处达到问题要求的最高点或最低点。",
    "Extrema rule: locate the maximum or minimum of the named signal within the window and map its index to early, middle, or late.": "极值规则：在窗口内找到指定信号的最大值或最小值，并按索引映射为早期、中期或后期。",
    "Drawdown rule: compute the largest peak-to-trough percentage drop of the target price within the window, then classify its severity by drawdown magnitude.": "回撤规则：计算窗口内目标价格从峰值到谷值的最大百分比跌幅，并按跌幅大小划分严重程度。",
    "Periodicity rule: use the strongest autocorrelation peak. If its score is below the predefined weak-cycle threshold, answer no clear cycle. Otherwise classify the peak lag relative to the window length as short, medium, or long.": "周期性规则：使用最强自相关峰。如果它的分数低于预设的弱周期阈值，就回答没有明显周期。否则按峰值 lag 相对窗口长度的位置分类为短周期、中等周期或长周期。",
    "Periodicity rule: compare autocorrelation peaks for the named signal. Short, medium, and long cycles depend on the best lag; low autocorrelation means no clear cycle.": "周期性规则：比较指定信号的自相关峰。短、中、长周期由最佳 lag 决定；自相关很低表示没有明显周期。",
    "Traffic counterfactual rule: compare factual mean queue length with the matched fixed-signal baseline. Positive factual-minus-baseline means adaptive control has higher queue; negative means lower queue.": "交通反事实规则：比较事实场景的平均队列长度与匹配的固定信号基线。事实减基线为正表示自适应控制队列更高，为负表示队列更低。",
    "Counterfactual rule: compare the factual simulator trace with the matched baseline or intervention trace for the named quantity. Use the direction and size of the mean difference to decide lower, higher, no material change, or mixed effect.": "反事实规则：比较事实仿真轨迹与匹配的基线或干预轨迹中指定量的差异。根据均值差异的方向和大小，判断为更低、更高、没有实质变化或混合影响。",
    "Water counterfactual rule: compare factual leak-scenario pressure with the matched no-leak baseline. Use material change only when the mean-pressure difference is large enough.": "供水反事实规则：比较事实漏水场景的压力与匹配的无漏水基线。只有均值压力差足够大时才判定为实质变化。",
    "Event-recovery rule: compare pre-event, event-window, and post-event means of the primary stress signal. Recovery means post-event moves back toward pre-event; persistent stress stays displaced; overshoot moves past the pre-event level.": "事件恢复规则：比较主压力信号在事件前、事件窗口中和事件后的均值。恢复表示事件后回到事件前水平；持续压力表示仍然偏离；过冲表示越过事件前水平。",
    "Recovery rule: compare pre-event, event, and post-event means of the primary stress signal. Recovery returns toward pre-event level; persistent stress stays degraded; overshoot exceeds the pre-event level.": "恢复规则：比较主压力信号在事件前、事件中和事件后的均值。恢复表示回到事件前水平附近；持续压力表示仍然变差；过冲表示超过事件前水平。",
    "Which compact variable is more strongly associated with maximum line-loading stress x0: total demand x1 or generation margin x2?": "哪个紧凑变量与最大线路负载压力 x0 的关联更强：总需求 x1，还是发电裕度 x2？",
    "The provided trace is intervention-minus-factual after disconnecting line 1 at global step 512, shown in segment post769_1025. What is the strongest post-event stress deviation in x0?": "这条轨迹是在全局第 512 步断开 1 号线路后的“干预减事实”结果，显示的是 post769_1025 片段。事件后 x0 最强的压力偏差是什么？",
    "Does total demand x1 tend to lead or lag maximum line-loading stress x0?": "总需求 x1 倾向于领先还是滞后最大线路负载压力 x0？",
    "Which third of the window has the highest volatility in total building load x0?": "窗口的哪一个三分之一部分里，建筑总负载 x0 的波动最大？",
    "When does the strongest isolated spike in total building load x0 occur?": "建筑总负载 x0 的最强孤立尖峰出现在什么时候？",
    "Is total building load x0 higher in the first half or the second half of the window?": "建筑总负载 x0 在窗口前半段更高，还是后半段更高？",
    "When does the strongest trading-volume spike for JPM occur?": "JPM 最强的交易量尖峰出现在什么时候？",
    "Where in the window does GS target price x0 reach its highest point?": "GS 目标价格 x0 在窗口的什么位置达到最高点？",
    "What drawdown regime best describes MRK target price x0 in this window?": "这个窗口里的 MRK 目标价格 x0 最符合哪种回撤状态？",
    "What cyclic pattern best describes water pressure x0 in this window?": "这个窗口里的水压 x0 最符合哪种周期模式？",
    "Compared with the matched no-leak baseline, how does the leak scenario change mean pressure?": "与匹配的无漏水基线相比，漏水场景如何改变平均水压？",
    "After the event window, does the primary stress signal recover, persist, or overshoot?": "事件窗口之后，主要压力信号是恢复、持续异常，还是过冲？",
    "What cyclic pattern best describes mean speed x0 in this window?": "这个窗口里的平均速度 x0 最符合哪种周期模式？",
    "Does speed movement lead queue movement, lag it, or show no clear relation?": "速度变化是领先队列变化、滞后队列变化，还是没有清晰关系？",
    "Compared with the matched fixed-signal baseline, how does the traffic-control scenario change mean queue length?": "与匹配的固定信号基线相比，交通控制场景如何改变平均队列长度？",
    "Is memory working set x1 higher in the first half or the second half of the window?": "内存工作集 x1 在窗口前半段更高，还是后半段更高？",
    "Which third of the window has the highest volatility in network receive rate x2?": "窗口哪一个三分之一部分里，网络接收速率 x2 的波动最大？",
    "x2 is more strongly associated with maximum line-loading stress x0 than x1: corr(x0,x2) is 0.99 versus corr(x0,x1) 0.86.": "x2 与最大线路负载压力 x0 的关联强于 x1：corr(x0,x2)=0.99，而 corr(x0,x1)=0.86。",
    "The strongest post-event stress deviation is larger upward peak: post-event x0 differences range from 0.37 to 0.56.": "事件后最强的压力偏差是更大的上升峰值：事件后 x0 差值范围为 0.37 到 0.56。",
    "There is no clear lead between x0 and x1 because the strongest lagged correlation occurs near zero lag (0 steps) with correlation 0.87.": "x0 和 x1 之间没有清晰领先关系，因为最强滞后相关出现在接近零滞后的位置（0 步），相关系数为 0.87。",
    "Total building load x0 varies most in the central third of the window.": "建筑总负载 x0 在窗口中间三分之一部分波动最大。",
    "The strongest isolated total building load x0 spike is concentrated in the final third of the window.": "建筑总负载 x0 的最强孤立尖峰集中在窗口最后三分之一部分。",
    "The average total building load x0 level is higher before the midpoint than after it.": "建筑总负载 x0 的平均水平在窗口中点之前高于中点之后。",
    "The strongest trading-volume spike occurs in the early part of the window, at step 8 of 256 with robust z-score 9.00.": "最强交易量尖峰出现在窗口早期，即 256 步窗口中的第 8 步，robust z-score 为 9.00。",
    "Target price x0 reaches its highest point in the late part of the window, at step 497 of 512 with value about 294.79.": "目标价格 x0 在窗口后期达到最高点：512 步窗口中的第 497 步，数值约为 294.79。",
    "The window shows severe drawdown: the maximum drawdown is about 36.65%, from step 340 to step 502.": "这个窗口呈现严重回撤：最大回撤约为 36.65%，从第 340 步到第 502 步。",
    "The dominant cyclic pattern is no clear cycle: the strongest autocorrelation peak is at lag 106 with score 0.132.": "主导周期模式是没有明显周期：最强自相关峰在 lag 106，分数只有 0.132。",
    "The matched simulator comparison shows no material pressure change: factual mean is 77.51 versus matched baseline mean 77.51.": "匹配仿真器对比显示没有实质水压变化：事实均值为 77.51，匹配基线均值为 77.51。",
    "The post-event evidence is pressure overshoot: pre-event mean x0 is 74.77, event mean is 74.75, and post-event mean is 74.83.": "事件后证据显示水压过冲：事件前 x0 均值为 74.77，事件中均值为 74.75，事件后均值为 74.83。",
    "The dominant cyclic pattern is short cycle: the strongest autocorrelation peak is at lag 7 with score 0.784.": "主导周期模式是短周期：最强自相关峰在 lag 7，分数为 0.784。",
    "The temporal relation is no clear lead: strongest lagged absolute correlation is -0.462 at lag -3, compared with zero-lag correlation -0.444.": "时间关系是没有清晰领先：最强滞后绝对相关为 lag -3 处的 -0.462，而零滞后相关为 -0.444。",
    "The matched simulator comparison shows higher queue under adaptive signal: factual mean is 2.91 versus matched baseline mean 2.56.": "匹配仿真器对比显示自适应信号下队列更高：事实均值为 2.91，匹配基线均值为 2.56。",
    "The half-window comparison is similar halves: first-half mean x1 is 797644.80 and second-half mean x1 is 801177.60.": "半窗口比较结果是前后两半相近：x1 前半段均值为 797644.80，后半段均值为 801177.60。",
    "The half-window comparison is second half higher: first-half mean x1 is 12725660.44 and second-half mean x1 is 14534246.40.": "半窗口比较结果是后半段更高：x1 前半段均值为 12725660.44，后半段均值为 14534246.40。",
    "Network receive rate x2 has volatility labeled early: early, middle, and late standard deviations are 305.62, 0.00, and 0.00.": "网络接收速率 x2 的波动标签是早期：早期、中期、后期标准差分别为 305.62、0.00 和 0.00。",
}


def load_rows() -> list[dict]:
    with RAW.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_repaired_rows() -> dict[str, dict]:
    with REPAIRED.open(encoding="utf-8") as f:
        return {row["id"]: row for row in (json.loads(line) for line in f if line.strip())}


def sanitize(name: str) -> str:
    return name.replace("/", "_").replace(" ", "_")


def pick_rows(rows: list[dict]) -> dict[str, list[dict]]:
    by_id = {row["id"]: row for row in rows}
    out = {}
    for source, ids in SELECTED_IDS.items():
        out[source] = [by_id[row_id] for row_id in ids]
    return out


def option_zh(option: str) -> str:
    label = option.split(".", 1)[0].strip() if "." in option else ""
    text = option.split(".", 1)[1].strip() if "." in option else option
    mapping = {
        "early": "早期",
        "middle": "中间",
        "late": "后期",
        "no pronounced spike": "没有明显尖峰",
        "x1": "x1",
        "x2": "x2",
        "both similar": "二者相近",
        "both weak": "二者都弱",
        "short cycle": "短周期",
        "medium cycle": "中等周期",
        "long cycle": "长周期",
        "no clear cycle": "没有明显周期",
        "similar halves": "前后两半相近",
        "first half higher": "前半段更高",
        "second half higher": "后半段更高",
        "cannot determine": "无法判断",
        "similar thirds": "三段相近",
        "larger downward dip": "更大的向下跌幅",
        "no material change": "没有实质变化",
        "larger upward peak": "更大的向上峰值",
        "x0 leads x1": "x0 领先 x1",
        "x1 leads x0": "x1 领先 x0",
        "no clear lead": "没有清晰领先",
        "unclear relation": "关系不清楚",
        "moderate drawdown": "中等回撤",
        "mild drawdown": "轻微回撤",
        "severe drawdown": "严重回撤",
        "little drawdown": "回撤很小",
        "lower pressure under leak": "漏水下水压更低",
        "higher pressure under leak": "漏水下水压更高",
        "no material pressure change": "没有实质水压变化",
        "mixed effect": "混合影响",
        "pressure recovers": "水压恢复",
        "pressure overshoot": "水压过冲",
        "persistent pressure stress": "持续水压压力",
        "no event recovery": "没有事件恢复",
        "speed leads queue": "速度领先队列",
        "queue leads speed": "队列领先速度",
        "lower queue under adaptive signal": "自适应信号下队列更低",
        "no material queue change": "没有实质队列变化",
        "higher queue under adaptive signal": "自适应信号下队列更高",
    }
    return f"{label}. {text}（{mapping.get(text, text)}）" if label else f"{text}（{mapping.get(text, text)}）"


def translate(text: str) -> str:
    return TRANSLATIONS.get(text, text)


def split_repaired_question(question: str) -> dict[str, str]:
    markers = [
        ("background", "Background: ", " Task rule: "),
        ("task_rule", "Task rule: ", " Specific question: "),
        ("specific_question", "Specific question: ", None),
    ]
    out = {}
    for key, start, end in markers:
        start_idx = question.find(start)
        if start_idx < 0:
            continue
        start_idx += len(start)
        end_idx = question.find(end, start_idx) if end else -1
        out[key] = question[start_idx:end_idx if end_idx >= 0 else None].strip()
    if "specific_question" not in out:
        out["specific_question"] = question
    return out


def plot_row(source: str, row: dict, case_idx: int) -> str:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    info = DISPLAY[source]
    raw = np.asarray(row.get("raw_compact_values") or row["values"], dtype=float)
    values = np.asarray(row["values"], dtype=float)
    t = np.arange(raw.shape[0])

    if raw.shape[1] <= 3:
        fig, axes = plt.subplots(raw.shape[1], 1, figsize=(8.0, 5.2), sharex=True)
    else:
        fig, axes = plt.subplots(raw.shape[1], 1, figsize=(8.0, 6.3), sharex=True)
    if raw.shape[1] == 1:
        axes = [axes]

    for idx, ax in enumerate(axes):
        ax.plot(t, raw[:, idx], color=f"C{idx}", lw=1.3)
        label_en = info["vars"][idx] if idx < len(info["vars"]) else f"x{idx}"
        label_zh = info["vars_zh"][idx] if idx < len(info["vars_zh"]) else f"x{idx}"
        ax.set_ylabel(f"x{idx}")
        ax.set_title(f"{label_en}\n{label_zh}", fontsize=9, loc="left")
        ax.grid(True, alpha=0.25)

    axes[-1].set_xlabel("time step / 时间步")
    fig.suptitle(f"{info['title']} | {info['zh']} | {row['task_family']}", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = FIG_DIR / f"{sanitize(source)}_case{case_idx:02d}_{sanitize(row['task_family'])}.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)

    norm_fig, norm_ax = plt.subplots(1, 1, figsize=(7.6, 2.8))
    for idx in range(values.shape[1]):
        norm_ax.plot(np.arange(values.shape[0]), values[:, idx], lw=1.1, label=f"x{idx}")
    norm_ax.set_title(f"Normalized model input | 标准化模型输入: {source}", fontsize=10)
    norm_ax.set_xlabel("time step / 时间步")
    norm_ax.set_ylabel("z-score")
    norm_ax.grid(True, alpha=0.25)
    norm_ax.legend(ncol=min(values.shape[1], 4), fontsize=8)
    norm_fig.tight_layout()
    norm_out = FIG_DIR / f"{sanitize(source)}_case{case_idx:02d}_{sanitize(row['task_family'])}_normalized.png"
    norm_fig.savefig(norm_out, dpi=180)
    plt.close(norm_fig)
    return str(out.relative_to(ROOT))


def fmt_slots(slots: dict) -> str:
    if not slots:
        return "`{}`"
    parts = []
    for key, value in slots.items():
        if isinstance(value, float):
            parts.append(f"`{key}={value:.4g}`")
        else:
            parts.append(f"`{key}={value}`")
    return ", ".join(parts)


def build_case_section(source: str, row: dict, repaired_row: dict, fig_rel: str, case_idx: int) -> str:
    info = DISPLAY[source]
    question = repaired_row.get("question") or row["question"]
    question_parts = split_repaired_question(question)
    specific_question = question_parts.get("specific_question", row["question"])
    evidence = row["oracle_evidence_caption"]
    options = row["options"]
    option_lines = "\n".join(f"- {option_zh(opt)}" for opt in options)
    values = np.asarray(row["values"], dtype=float)
    raw = np.asarray(row.get("raw_compact_values") or row["values"], dtype=float)
    raw_preview = ", ".join(f"x{i}={raw[0, i]:.4g}" for i in range(raw.shape[1]))
    final_preview = ", ".join(f"x{i}={raw[-1, i]:.4g}" for i in range(raw.shape[1]))
    return "\n".join(
        [
            f"### {case_idx}. {info['title']}（{info['zh']}）",
            "",
            f"![]({fig_rel})",
            "",
            f"**样本 ID:** `{row['id']}`  ",
            f"**任务:** `{row['task_family']}`  ",
            f"**窗口长度:** `{values.shape[0]}` steps，变量数 `{values.shape[1]}`  ",
            f"**变量语义:** {', '.join(info['vars_zh'])}  ",
            f"**数据说明:** {info['scale_note']}",
            "",
            f"**起点 raw 值:** {raw_preview}  ",
            f"**终点 raw 值:** {final_preview}",
            "",
            f"**Repaired question:** {question}",
            "",
            f"**中文背景:** {translate(question_parts.get('background', ''))}  ",
            f"**中文判定规则:** {translate(question_parts.get('task_rule', ''))}  ",
            f"**中文具体问题:** {translate(specific_question)}",
            "",
            "**Options / 选项:**",
            "",
            option_lines,
            "",
            f"**Gold answer:** `{row['answer']}`，`{row['answer_label']}`",
            "",
            f"**Oracle evidence:** {evidence}  ",
            f"**中文证据:** {translate(evidence)}",
            "",
            f"**关键 support slots（可验证证据字段）:** {fmt_slots(row.get('support_slots') or {})}",
            "",
            f"**Question repair status:** `{repaired_row.get('question_repair_status', 'unknown')}`",
        ]
    )


def main() -> None:
    rows = load_rows()
    repaired_rows = load_repaired_rows()
    selected = pick_rows(rows)
    fig_paths = {
        source: [plot_row(source, row, idx) for idx, row in enumerate(source_rows, start=1)]
        for source, source_rows in selected.items()
    }

    sections = []
    for source in SELECTED_IDS:
        source_sections = []
        for idx, row in enumerate(selected[source], start=1):
            source_sections.append(build_case_section(source, row, repaired_rows[row["id"]], fig_paths[source][idx - 1], idx))
        sections.append(f"## {source}：新增 2 道后共 3 道 case study\n\n" + "\n\n".join(source_sections))
    md = dedent(
        """
        # Case Study: Multi-Simulator QCC 数据源特质与规模上限

        **日期:** 2026-05-18；2026-05-19 补充每域 2 道 case study
        **样本来源:** `multisim_qcc_v5_aiops_v3/balanced_eval_per_source8.jsonl`
        **目的:** 用真实 JSONL 样本展示每个 simulator/source 生成的时序数据长什么样、对应 QA 是什么、证据如何验证，以及这些数据源的可扩容上限。2026-05-19 版把每个域从 1 道扩展到 3 道，并补充 repaired question、中文问题、中文选项和时序图。

        ## 1. 总体结论

        当前数据生成已经覆盖 6 个来源：

        - `Grid2Op`：电网运行时序，适合压力、负载、反事实干预、跨变量关系。
        - `CityLearn`：建筑能耗时序，适合负载、天气/光伏上下文、窗口比较、波动。
        - `FinRL`：金融市场历史 OHLCV trace，适合价格/交易量/市场 regime，但不是因果仿真器。
        - `water`：供水系统 trace，适合压力、流量、事件恢复、周期性、反事实。
        - `traffic`：交通系统 trace，适合速度、排队、占有率、信号干预、周期性。
        - `AIOpsLab official v3`：Kubernetes/Prometheus 遥测，适合 CPU/内存/网络、服务上下文、故障上下文，但当前规模最小。

        最重要的结论是：**总行数不是唯一瓶颈**。数据源已经能合成到几千行级别；真正的瓶颈是 AIOpsLab official case 数、任务算子均衡、以及 evidence slot 是否显式可验证。

        ## 2. 当前规模与可扩容上限

        ### 当前主数据集规模

        `multisim_qcc_v5_aiops_v3` 当前规模：

        | 来源 | 当前使用 rows | 已加载 rows | 主要限制 |
        | --- | ---: | ---: | --- |
        | Grid2Op | 384 | 1791 | 可扩，受 chronic/干预场景数限制 |
        | CityLearn | 384 | 1344 | 可扩，受 building/weather/window 组合限制 |
        | FinRL | 384 | 3348 | 很容易扩，受 ticker/window 数限制 |
        | water | 384 | 504 | 可扩，需更多场景/事件参数 |
        | traffic | 384 | 504 | 可扩，需更多路网/信号/事件参数 |
        | AIOpsLab official v3 | 60 | 60 | 当前最大瓶颈，受成功导出的 official case 数限制 |
        | **合计** | **1980** | **7551 左右** | 不平衡明显 |

        ### 规模上限的保守估计

        | 口径 | 估计规模 | 说明 |
        | --- | ---: | --- |
        | 当前可靠 balanced v5 | `1980` | 已过 schema gate，六源合并，AIOpsLab official 只 60 |
        | 当前已有单源全部合并 | `~7551` | 不平衡，FinRL/Grid2Op/CityLearn 远多于 AIOpsLab |
        | 短期均衡扩展 | `~2580` | 五个成熟 source 各 504，AIOpsLab 60 |
        | 加大 FinRL windows_per_length | `~9500-10000` | 容易堆量，但会强化金融/source prior |
        | water/traffic 场景参数扩展后 | `1万+` | 工程上可行，但必须保留 official/fallback 标记 |
        | AIOpsLab official 大规模 | 未稳定 | 取决于 Docker/kind/Helm/kubectl runtime 和 case 成功率 |

        解释：

        - Grid2Op/CityLearn/FinRL/water/traffic 都能通过增加窗口、场景、事件参数继续扩。
        - FinRL 最容易扩到几千到上万，但它更像历史市场 trace，不应单独承担“simulator 泛化”主证据。
        - AIOpsLab official 的上限目前不是理论问题，而是 runtime 和 case export 成功率问题。
        - 如果只追求行数，很快能到 `1万+`；如果追求多 simulator 均衡和可验证，当前更现实的是 `2k-3k` 的高质量 balanced set。

        ### 每个 simulator 的扩容上限分析

        | 数据源 | 当前已验证规模 | 短期可扩规模 | 更高规模的条件 | 主要风险 |
        | --- | ---: | ---: | --- | --- |
        | Grid2Op | `1791` loaded / `384` used | `3k-5k` | 更多 chronic、更多干预线/时间点、更多窗口长度 | CF label collapse 和任务模板偏置 |
        | CityLearn | `1344` loaded / `384` used | `2k-5k` | 更多 building、weather window、控制策略组合 | 与其他 building simulator 语义重叠 |
        | FinRL | `3348` loaded / `384` used | `5580+`（`windows_per_length=5`） | 更多 ticker、更多窗口、更多市场周期 | 容易堆量但不是因果 simulator |
        | water | `504` loaded / `384` used | `1500-3000` | 更多 leak/event seed、阀门/泵/修复策略组合 | 必须区分 official simulator 和 fallback/smoke |
        | traffic | `504` loaded / `384` used | `1500-3000` | 更多 route demand、信号策略、事故/封路场景 | 场景过少时容易学固定模板 |
        | AIOpsLab official | `60` loaded / `60` used | `数百到一千级` | 稳定 Docker/kind/Helm/kubectl runtime，并提高 case export 成功率 | 当前最大瓶颈；5 个成功 case，每 case 约 12 rows |

        AIOpsLab 的线性估算很直接：当前 5 个成功 case 生成 60 rows，即每个成功 case 约 12 rows。若能稳定得到 100 个 successful official cases，则约 1200 rows；若 500 个 cases，则约 6000 rows。但这依赖 runtime 工程稳定性，不能用 fallback 数据替代 official 口径。

        ## 3. 具体时序样本与 QA

        本节每个域给 3 道 case study：原有代表样例 1 道，新增 2 道。AIOpsLab 只选可由数值时序或窗口统计支撑的样例，避免把 metadata-only 题当作纯时间序列理解案例。
        """
    ).strip()

    md += "\n\n" + "\n\n".join(sections)
    md += "\n\n" + dedent(
        """

        ## 4. 数据源特质总结

        | 数据源 | 合成数据特质 | 优点 | 遗留问题 |
        | --- | --- | --- | --- |
        | Grid2Op | 长窗口、多变量、电网状态和反事实干预 | 真实 simulator 语义强，counterfactual 清楚 | 当前模型容易学标签模板，CF label collapse 曾出现 |
        | CityLearn | 建筑负载、天气/光伏/需求上下文 | 窗口比较和波动任务稳定 | 与其他 building simulator 有领域重叠 |
        | FinRL | 历史市场价格/指数/交易量 | 规模最容易扩大，任务多样 | 不是因果 simulator，不能证明 intervention 泛化 |
        | water | 压力/流量/储水信号，事件恢复和泄漏 | 适合反事实和基础设施 reasoning | 当前 smoke 数据规模小，需明确 official/fallback |
        | traffic | 速度/排队/占有率/信号事件 | 周期性、lead-lag、干预效果直观 | 当前场景较少，需更多路网和控制策略 |
        | AIOpsLab official | Prometheus CPU/内存/网络遥测 + 故障元数据 | 最贴近真实运维异常和 agent 场景 | official case 只有 60 rows，是主要规模瓶颈 |

        ## 5. 对模型训练的启示

        这些数据源足够说明“多 simulator 数据流可以打通”，但还不足以说明模型已经学会泛化。原因是：

        1. 不同 simulator 的变量语义差别很大。
        2. 不同 task family 需要完全不同的算子，例如均值比较、相关系数、自相关、异常定位、反事实差异、metadata lookup。
        3. 目前模型诊断显示 actual time series 不优于 zeroed/permuted time series，说明模型还没有稳定使用时序证据。
        4. 下一步数据生成不应只追求更多行，而应为每条样本显式保存 operator slots，例如 `corr_x1/corr_x2`、`region_stds`、`robust_z`、`period_score`、`first_mean/second_mean`。

        ## 6. 建议的下一步数据生成路线

        1. 固定一个 `balanced high-quality v6`：每个成熟 source 约 500 条，AIOpsLab 暂时 60 条，全部带显式 operator slots。
        2. 对 water/traffic 增加更多 scenario seed 和事件参数，让它们从 504 提到 1500-3000 条。
        3. AIOpsLab 单独作为 official case collection 项目推进，优先提升成功 case 数，而不是用 fallback 冒充 official。
        4. 每个 task family 做最小计数门槛，例如每个 source 每类任务至少 50 条，避免模型只学常见任务。
        5. 生成训练数据时同时生成 diagnostic controls：actual、zeroed、permuted、oracle-slot verbalization，用于判断模型是否真的看时序。
        """
    ).strip() + "\n"

    OUT_MD.write_text(md, encoding="utf-8")
    print(OUT_MD)


if __name__ == "__main__":
    main()
