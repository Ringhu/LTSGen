# TS-Cap + TS-Align 工程说明（单文档总规范）

> 说明：这份文档记录的是你此前围绕 `ts_capv2` 设计的目标规范。当前工程的活路径已经收敛到 `ts_cap + ts_align + ts_align_scripts_v2`，因此本文更适合作为研究/重构参考，而不是当前目录结构的事实描述。

> 本文档是该工程的“唯一入口规范文档”。目标读者是第一次接触本工程的人：  
> 1) 读完即可理解工程整体目标、数据流、关键设计点（抗幻觉、低成本、可对齐）  
> 2) 仅凭本说明文档即可实现/重写每个代码文件（即每个文件的职责、接口、数据结构、约束都在本文给出）

---

## 0. 工程目标与研究定位

本工程由两个大块组成：

- **`ts_capv2/`：时间序列 → 结构化事实 → 文本描述（可选 LLM 润色） 的数据生成器**
  - 核心理念：**硬逻辑（统计与规则）负责事实正确**，**软逻辑（模板/LLM）负责语言表达**  
  - 输出：用于训练/评估的 `.jsonl` 数据集，包含：
    - 原始时间序列窗口
    - 结构化统计特征（features）
    - 结构化事实断言（claims，带验证结果，防幻觉）
    - 文本描述（descriptions / caption_base）
    - **可选：层级化 dense 标注（dense_captions：global + local segments）**

- **`ts_align/`：时间序列 ↔ 文本对齐模型训练工程（CLIP 风格 + 局部稀疏对齐 + span 监督）**
  - 输入：`ts_capv2` 输出的 `.jsonl`
  - 模型：Dual-Encoder（Time Encoder + Text Encoder）
    - Global 对齐：整段序列 ↔ global_summary 文本
    - Local 对齐：局部 span ↔ local caption 文本
    - Span 定位：local text query → patch heatmap（用 start/end span 做监督）
  - 输出：训练好的 checkpoint + 评估指标（retrieval recall@k、grounding IoU）

---

## 1. 端到端数据流（概览）

### 1.1 数据生成（ts_capv2）
1. **Wrapper 读取真实数据集**（ETT/Weather/Traffic/UCR/NAB/FRED 等）  
2. **Windowing 切片**得到 `[T, D]` 窗口（T 可变长）  
3. **特征提取**：趋势、波动、极值、周期性、滞后相关等  
4. **Claims 构建 + 校验**：把特征变成可验证的“事实断言”并二次复算校验（防幻觉）  
5. **渲染**：
   - 基线：模板中文描述 `render_caption_zh`  
   - 升级：结构化输出 `render_structured_zh`（global + local spans）
6. **可选 LLM 润色**（只输入短 JSON：raw_stats + detected_events，不输入 raw 数列）  
7. 输出 `.jsonl`

### 1.2 对齐模型训练（ts_align）
1. 读取 `.jsonl`
2. 取 `dense_captions.global` 与整段序列做 global CLIP loss  
3. 取 `dense_captions.local[]` 或从 claims 动态生成 local events
4. Time encoder 输出 patch tokens  
5. ROI pooling 得到 span embedding，与 local text embedding 做 local CLIP loss  
6. 额外做 span localization loss（query->patch scores 在 GT span 内最大）

---

## 2. 核心数据结构与字段规范（必须一致）

### 2.1 Index/Span 约定（全工程统一）
- **时间索引使用整数 index**，对原序列窗口 `[0, T-1]`  
- `Claim.start/end`：**inclusive 区间** `[start, end]`  
- `dense_captions.local[].start/end`：**inclusive** `[start, end]`  
- `peak/valley` 点事件：`idx`，通常映射为 `[idx, idx]` 或加小上下文 `[idx-k, idx+k]`

### 2.2 ts_capv2 输出 JSONL Record Schema（训练最小必需）
每行一个 JSON 对象，建议包含以下字段（加粗为训练最小必需）：

- **`timeseries`**: `List[List[float]]`，shape = `[T, D]`
- **`variables`**: `List[Dict]`，至少包含 `name, role`（用于识别 target）
- **`descriptions`**: `List[str]`，默认取 `descriptions[0]` 作为 global 文本（兼容旧逻辑）
- **`claims`**: `List[Dict]`（用于动态 local 生成与可解释性）

推荐附带（强烈建议）：
- `time`: `List[str]`（原始时间戳）
- `features`: `Dict`（趋势/周期/波动/相关/显著片段）
- `dense_captions`: `{"global": str, "local": List[{start,end,description,type}]}`（用于 Dense/grounding 训练）
- `claim_check`: 校验统计
- `domain_context`: 数据集背景信息

---

## 3. 目录结构（建议标准）

```

project_root/
ts_capv2/
core/
features.py
claims.py
render_zh.py
samples.py
wrappers/
base.py
windowing.py
ltsf_wrappers.py
nab_wrapper.py
ucr_wrapper.py
fred_wrapper.py        # 可选：如果 registry 引用必须存在
registry.py
utils/
openai_chat.py
cli.py

ts_align/
**init**.py
data/
**init**.py
jsonl_dataset.py
collate.py
text_zh.py
models/
**init**.py
time_encoder.py
text_encoder.py
hsa_clip.py
losses.py
metrics.py
train_cli.py

````

---

# Part A：ts_capv2（数据生成系统）文件级规范

## A.0 ts_capv2 总体职责边界

- 只做“数据理解 + 事实结构化 + 文本输出”，不做深度学习训练
- LLM 只作为可选“润色/合并器”，绝不让 LLM 直接看 raw 数列
- 任何文本输出都必须能追溯到 claims/features，避免 factual error

---

## A.1 `ts_capv2/core/features.py`

### 职责
提供对单变量/多变量时间序列窗口的**统计特征计算**与**结构化摘要类型**。本文件必须是：
- 纯数学/统计逻辑（确定性，尽量无随机）
- 处理异常值、nan、std≈0、短序列等边界情况

### 依赖
- `numpy`
- 可选：`scipy.signal`（FFT/periodogram）

### 主要数据结构（必须定义）
1) `TrendSegment`
- `start:int, end:int`（inclusive）
- `slope_z:float`（在 z-normalized 空间的斜率）
- `label:str` ∈ `{"up","down","flat"}`

2) `VolatilityInfo`
- `overall_std: float`（归一化后总体波动）
- `segment_stds: List[float]`（分段波动）
- `most_volatile_segment: int`（argmax segment_stds）

3) `PeakValleyEvent`
- `kind: str` ∈ `{"peak","valley"}`
- `index: int`
- `z_value: float`
- `delta_pct_vs_mean: float`

4) `SeasonalityInfo`
- `has_seasonality: bool`
- `period: Optional[int]`
- `strength: float`

5) `CorrelationInfo`
- `var: str`
- `corr: float`
- `relation: str` ∈ `{"positive","negative"}`
- `lag: int`
- `stable: bool`
- `stability_note: str`

6) `StructuredSummary`
- `meta: Dict[str,Any]`
- `global_trend_label: str`（如 up/down/flat/up_then_down/down_then_up）
- `trend_segments: List[TrendSegment]`
- `volatility: VolatilityInfo`
- `peaks: List[PeakValleyEvent]`
- `valleys: List[PeakValleyEvent]`
- `seasonality: SeasonalityInfo`
- `correlations: List[CorrelationInfo]`

7)（升级）`SalientSegment`（显著片段 proposals）
- `start:int, end:int`（inclusive）
- `score:float`（显著性分数，用于排序/筛选）
- `type:str`（ramp_up/ramp_down/peak_context/valley_context/volatile/...）
- `features:Dict[str,Any]`（片段特征快照）

### 必须提供的核心函数接口（建议保持 stable）
- `z_normalize(x: np.ndarray) -> np.ndarray`
- `robust_scale(x: np.ndarray, eps=1e-8) -> float`
- `pct_change(a: float, b: float, scale: float) -> float`
- `detrend_linear(x: np.ndarray) -> np.ndarray`

趋势相关：
- `segment_by_slope_fixed(x, smooth_win=5, slope_eps=0.02, min_seg_len=10) -> List[Dict]`
  - 返回元素必须含：`start,end,label,slope`
  - label ∈ {-1,0,1}，slope 为 z 空间线性回归斜率

- `compute_trend_segments(x, n_segments=3) -> List[TrendSegment]`
- `summarize_global_trend(segments) -> str`

波动/极值：
- `compute_volatility(x, n_segments=3) -> VolatilityInfo`
- `volatility_label(x) -> str` ∈ {"low","medium","high"}
- `detect_peaks_and_valleys(x, z_thresh=1.0, min_distance=5) -> (peaks,valleys)`

ramp：
- `detect_ramps(x, min_ramp_len=24, min_ramp_z_change=0.8, max_ramps=3) -> List[Dict]`
  - 每个 dict 至少含：`kind,start,end,delta_z,delta_pct`

周期性：
- `estimate_dominant_period_acf(x, max_lag=200, min_strength=0.3, detrend=True) -> SeasonalityInfo`
- `estimate_period_fft(x, fs=1.0) -> (period:Optional[int], strength:float)`
- `estimate_dominant_period_robust(x, max_lag=200) -> SeasonalityInfo`
- `seasonality_strength_label(info) -> Dict`（如 {"period":..,"strength":"weak/medium/strong"}）

相关性（多变量）：
- `compute_lagged_correlations_stable(series_map, target_col, candidate_cols=None, top_k=3, max_lag=24, min_abs_corr=0.3, lag_tol=2) -> List[CorrelationInfo]`

显著性（升级支持 dense captioning）：
- `compute_salience_score(x_seg, global_std) -> float`
- `extract_salient_windows(x, trend_segments, peaks, valleys, top_k=5) -> List[SalientSegment]`
  - 必须具备去重（NMS / IoU 抑制）或等价逻辑

### 边界条件（必须处理）
- 序列长度过短：返回合理默认（无峰谷、无周期、趋势 flat）
- std≈0：相关系数返回 nan 或 stable=False
- 含 nan：相关计算需 mask，wrapper 侧也应 ffill/bfill

---

## A.2 `ts_capv2/core/claims.py`

### 职责
把 `features.StructuredSummary` 转为**结构化断言 Claims**，并提供：
- **validate_claim(s)**：复算验证，防幻觉
- **consistency rules**：修复逻辑冲突（如 flat vs delta）
- **policy**：对验证失败的某些 claim 降级保留（如 seasonality/lagged_corr）

### 核心数据结构
`Claim` dataclass（必须字段）
- `id: str`
- `type: str`（如 global_trend_label/global_net_change/phase/ramp/peak/valley/seasonality/lagged_corr/volatility...）
- `target: str`（目标变量名）
- `start,end,idx`（可选，span 或点事件）
- `t_start,t_end,t_idx`（可选，对应 timestamps）
- `data: Dict[str,Any]`（断言内容数值）
- `sentence: Optional[str]`（可选，若未来存文本）
- `ok: Optional[bool]`（验证结果）
- `reason,evidence`（验证失败原因与复算证据）

### 关键函数接口
- `build_phase_claims(x, target_col, time_list, ...) -> List[Claim]`
- `build_claims(summary, target_col, x, time_list, volatility_label) -> List[Claim]`
- `validate_claim(c, series_map, target_col) -> Claim`
- `validate_claims(claims, series_map, target_col) -> Dict`
  - 返回必须包含：`pass,n,n_failed,failed,checked`

一致性与策略：
- `apply_consistency_rules(claims) -> List[Claim]`
- `apply_claim_policy(claims, enforce=True) -> List[Claim]`
- （可选）`apply_budget_policy(claims, max_peaks=1, ...) -> List[Claim]`

### 约束与设计要求
- validate 必须是“复算”而不是“相信缓存”
- 对 `lagged_corr` 与 `seasonality` 可容错降级（避免样本全部被丢弃）
- 对 phase/ramp/global_net_change/peak/valley 这类“关键事实”若失败可丢弃（保证真实性）

---

## A.3 `ts_capv2/core/render_zh.py`

### 职责
把 Claims 渲染成自然语言中文描述。
- 保持可控随机（同一输入可复现）
- 模板化，避免 LLM 幻觉
- 支持两种输出：
  - Legacy：`render_caption_zh(...) -> str`
  - 结构化：`render_structured_zh(...) -> StructuredCaptionOutput`（global + local）

### 关键结构
- `LexiconZH`：中文模板词库（openers、trend words、templates…）
- `StructuredCaptionOutput`
  - `global_caption: str`
  - `local_captions: List[{"start","end","description","type"}]`
  - `full_text: str`（兼容旧字段）

### 必须提供的接口
- `stable_seed(*parts) -> int`：用 sha256 保证稳定随机种子
- `render_caption_zh(claims, variables, target_col, seed=None) -> str`

结构化输出（升级）：
- `_render_local_segment(rng, target, claim) -> str`
  - 输入一个 claim，输出一句短语（不含连接词），用于局部 caption
- `render_structured_zh(claims, variables, target_col, seed=None) -> StructuredCaptionOutput`
  - global_caption：可直接用 full_text（保守）或使用 overview+seasonality+relations 拼一个短 global summary（更稀疏）
  - local_captions：从 phase/ramp/peak/valley 生成 span-level 文本

### 约束
- 渲染不得篡改 claim.data 数值
- 对未通过验证（ok=False）的 claim 默认不渲染或降级处理
- local spans 必须输出 start/end（用于 dense alignment）

---

## A.4 `ts_capv2/core/samples.py`

### 职责
把“wrapper 输出的一个窗口样本”变成最终 record（写入 jsonl）：
- 组织 meta
- 调用 features 分析
- 构建 claims + 验证 + policy
- 渲染 caption（legacy + structured）
- 可选 LLM 润色（两阶段 pipeline：只传 stats/events，不传 raw 数列）

### 关键接口
- `analyze_window(meta, series_map, target_col, series_cols) -> StructuredSummary`
- `build_features(summary, x_target, target_col) -> Dict[str,Any]`
  - 必须至少包含：trend/seasonality/volatility/correlations
  - 推荐新增：salient_segments（用于 LLM 与 dense 提案）

- `generate_sample(...) -> Dict[str,Any]`
  - 输入：
    - `timestamps: List[str]`
    - `values: Sequence[Sequence[float]]`（[T,D]）
    - `series_cols: List[str]`（D）
    - `target_col: str`
    - `dataset_name, task, series_key, indices`
    - `variables_meta, label, domain_context`
    - `llm_hook, llm_enabled`
  - 输出 record（建议 schema）：
    - `timeseries, time, variables, claims, features`
    - `caption_base, descriptions`
    - `dense_captions: {"global": str, "local": List[...]}`（升级）
    - `claim_check` 等

- `write_jsonl(records, output_path)`

### LLM 对接（升级建议）
- `payload` 仅包含：
  - `task_type="hierarchical_captioning"`
  - `raw_stats`（趋势/周期/波动等结论）
  - `detected_events`（span proposals + type/score + 原始粗描述可选）
  - `dataset_context`
- LLM 返回严格 JSON：
  - `global_summary`
  - `local_segments[{start,end,caption}]`（start/end 必须来自输入 spans，不允许编造）

---

## A.5 `ts_capv2/utils/openai_chat.py`

### 职责
提供统一的 LLM 客户端与 Hook：
- 支持 provider（openai/deepseek/...）
- 支持 text 模式与 JSON 模式（结构化输出）
- 支持重试、timeout、温度、context 截断
- 提供默认 `enhance_caption_hook(payload) -> str`（legacy润色）
- 提供升级版 `hierarchical_caption_hook(payload) -> Dict`（建议新增）

### 关键数据结构与接口
- `LLMConfig(BaseModel)`
  - provider/model/api_key/base_url/system_prompt/timeout/max_retries/temperature/max_context_chars
- `configure_global_client(cfg)`
- `OpenAIChatClient`
  - `chat_text(user_prompt, system_prompt=None) -> {"content":str,"token_usage":{...}}`
  - `chat_json(user_prompt, system_prompt=None) -> Dict`（必须保证 json.loads 成功，否则抛错/返回 None）

系统 prompt（升级）：
- `SYSTEM_PROMPT_HIERARCHICAL`（见本文 A.4 约定）

Hook 规范：
- `enhance_caption_hook(payload) -> str`
  - 输入 payload 必须可序列化；输出仅文本（不改数值）
- `hierarchical_caption_hook(payload) -> Dict[str,Any]`（建议）
  - 输出 dict 且符合 schema：`global_summary`, `local_segments`

---

## A.6 `ts_capv2/wrappers/base.py`

### 职责
定义统一数据源接口，使上层无需关心数据集细节。

### 关键结构
- `WrapperConfig`
  - `input_path, dataset_name, task`
  - `time_col, series_cols, target_col`
  - `target_series_index`（可选：指定处理第几个序列）
  - `window_mode ("sliding"/"full"), window_len, stride, max_windows`
  - `ucr_name, ucr_split, ucr_label_semantics`
  - `llm_enabled`（wrapper 内推断 label 语义可用）

- `BaseWrapper(ABC)`
  - `iter_samples() -> Iterator[Dict[str,Any]]`

### wrapper 输出样本必须满足 schema（强制契约）
每个 yield 的 dict 必须包含：
- `timestamps: List[str]`（[T]）
- `values: List[List[float]]`（[T,D]）
- `series_cols: List[str]`（[D]）
- `target_col: str`
- `label: Any`（可 None）
- `variables_meta: Optional[List[Dict]]`
- `domain_context: Dict | str`
- `series_key: str`
- `indices: Optional[Tuple[int,int]]`（窗口在原序列中的 global 索引范围）

---

## A.7 `ts_capv2/wrappers/windowing.py`（你工程里必须存在）

### 职责
统一窗口切片策略（sliding/full），供所有 wrappers 复用。

### 必须定义的数据结构
- `WindowMeta`
  - `global_start_idx:int`
  - `global_end_idx:int`（exclusive 或 inclusive 必须明确；推荐 **exclusive**，与 python slice 一致）
  - `window_len:int`
  - `stride:int`
  - `mode:str`

### 必须提供接口
- `iter_windows(timestamps, values, window_mode, window_len, stride, max_windows=None) -> Iterator[(WindowMeta, t_win, v_win)]`
  - `t_win`：List[str] length T'
  - `v_win`：List[List[float]] shape [T',D]
  - 若 `window_mode="full"`：仅 yield 一次整个序列
  - 若 `"sliding"`：按 stride 滑动

### 约束
- 保证不会产生空窗口
- 对不足 window_len 的情况：
  - 可选择跳过 或 yield 短窗口（推荐 yield 短窗口以支持 64~1000+ 变长训练）

---

## A.8 `ts_capv2/wrappers/ltsf_wrappers.py`

### 职责
支持 LTSF/forecasting 常见 CSV 数据集（ETT/Weather/Traffic/Electricity/...）：
- 读取 CSV
- 识别 time 列（可选）
- 选择数值列作为 variables
- ffill/bfill 填补缺失
- windowing 切片输出样本

### 必须提供
- `LTSFWrapper(BaseWrapper).iter_samples()`
- dataset domain context：`DOMAIN_CONTEXT_ZH`
- variable info maps：`VAR_INFO_ETT/WEATHER/ILLNESS/...`
- helper：
  - `_guess_time_col`
  - `_pick_numeric_cols`
  - `_build_variables_meta`

### 输出要求
- `variables_meta` 至少包含：`name,index,role,meaning_zh,unit`

---

## A.9 `ts_capv2/wrappers/nab_wrapper.py`

### 职责
支持 NAB anomaly detection 数据集：
- 遍历 csv 文件
- 解析 timestamp/value
- 读取 labels（windows 或 points）
- windowing 切片
- 产出 label（窗口中是否包含异常点）

### 必须提供
- `NABWrapper(BaseWrapper).iter_samples()`
- 兼容：
  - `combined_windows.json`（interval labels）
  - `combined_labels.json`（point labels）

### 约束
- 解析失败行要跳过，不能导致全数据崩溃
- label 输出建议为 int(0/1)

---

## A.10 `ts_capv2/wrappers/ucr_wrapper.py`

### 职责
支持 UCR2018 分类数据集：
- 读取 TRAIN/TEST.tsv
- 解析 label + 单变量序列
- 缺失值填充（nan fill）
- domain_context 包含 readme_summary 与 label_map（可选）

### 必须提供
- `UCRWrapper(BaseWrapper).iter_samples()`
- label semantics：
  - `ucr_label_semantics="none"`：不提供 label_map
  - `"readme"`：从 README 解析 class->meaning
  - `"llm"`：可选调用 LLM 推断（必须 llm_enabled）

### 约束
- values 统一输出为 `[[v],[v]...]`（D=1）

---

## A.11 `ts_capv2/wrappers/fred_wrapper.py`（如果 registry 引用必须实现）

### 职责（建议实现）
支持从本地 CSV 或缓存读取 FRED 风格的经济时间序列：
- CSV 至少包含 date 与 value（或多列）
- 产出单变量或多变量窗口

### 必须提供
- `FREDWrapper(BaseWrapper).iter_samples()`
- domain_context 给出：指标含义/频率/单位（若可用）

---

## A.12 `ts_capv2/wrappers/registry.py`

### 职责
根据 `dataset` 名称路由到具体 wrapper，并构建 `WrapperConfig`。

### 必须提供
- `get_wrapper(dataset, input_path, **kwargs) -> BaseWrapper`

### 约束
- dataset 统一 `.lower()`
- 若 dataset 未命中专用 wrapper，默认回落 `LTSFWrapper`

---

## A.13 `ts_capv2/cli.py`

### 职责
工程化 CLI：从命令行/配置文件读取参数，调用 wrapper + `generate_sample` 批量生成 JSONL。

### 必须提供
- 参数解析（argparse）
- 配置合并策略（config_file + CLI override）
- Pydantic 配置模型：
  - `DatasetConfig`
  - `GenerationConfig`
  - `CLIConfig`
- 支持 LLM 开关：
  - `--llm_enabled`（兼容旧逻辑：默认启用 caption 润色）
  - `--llm_caption_enabled`
  - `--llm_label_enabled`
- 运行主循环：
  - for sample in wrapper: rec = generate_sample(...)
  - 逐行写 jsonl

### 约束
- 强制记录生成计数
- 支持 KeyboardInterrupt 不中断写入（尽力保存）

---

# Part B：ts_align（对齐训练系统）文件级规范

## B.0 ts_align 总体职责边界
- 只读 `.jsonl`
- 负责模型、loss、训练、评估
- 不负责数据集解析细节（那是 ts_capv2 的职责）

---

## B.1 `ts_align/data/jsonl_dataset.py`

### 职责
读取 `ts_capv2` 生成的 `.jsonl`，产出训练样本：
- `x`: torch.FloatTensor `[C,T]`
- `global_text`: str（优先 dense/global，否则 descriptions[0]）
- `locals`: List[LocalEvent]（优先 dense/local，否则由 claims 生成）

### 必须提供
- `class TSCapJSONLDataset(Dataset)`
  - `__init__(jsonl_path, max_records=None, seed=0)`
    - 使用 offset 索引加速随机访问（不把全文件读进内存）
  - `__getitem__(idx) -> Dict[str,Any]`
    - 返回字段：
      - `x: FloatTensor [C,T]`
      - `length: int`
      - `global_text: str`
      - `locals: List[Dict]`（见 B.2）
      - `target_col: str`

### target 推断策略
- 从 `variables` 中找 `role=="target"` 的 `name`
- fallback：variables[0].name 或 "x"

---

## B.2 `ts_align/data/text_zh.py`

### 职责
将 `record["claims"]` 的 dict 形式转为可训练的 local event（含 span + text variants + salience）。

### 必须提供
- `claim_dict_to_local_event(claim:Dict, target_col:str, rng) -> Optional[Dict]`
  - 输出 schema：
    - `start:int, end:int`（inclusive）
    - `type:str`（phase/ramp/peak/valley）
    - `salience:float`（排序用）
    - `text_variants:List[str]`（同义模板）

### 约束
- `claim["ok"]==False` 的默认不输出
- `peak/valley` 用 `idx` 映射为 `[idx,idx]` 或 caller 决定上下文扩展

---

## B.3 `ts_align/data/collate.py`

### 职责
Batch Collate：
- 对变长时间序列做 padding
- 构造 patch_mask
- flatten locals（跨 batch 展开）
- 将 time span 映射到 patch span（ps inclusive, pe exclusive）

### 必须提供
- `hsa_collate_fn(batch, patch_size:int, max_local_per_sample:int=4, seed=0) -> Dict`

输出 schema（训练核心依赖）：
- `x: FloatTensor [B,C,T_max]`
- `lengths: LongTensor [B]`
- `patch_mask: BoolTensor [B,N_patch]`
- `global_texts: List[str]`
- `local_texts: List[str]`（长度 M）
- `local_batch_idx: LongTensor [M]`
- `local_ps: LongTensor [M]`
- `local_pe: LongTensor [M]`

### 映射规则
- patch j 覆盖 `[j*patch_size, (j+1)*patch_size)`（time）
- time span `[start,end]` → patch span `[start//ps, ceil((end+1)/ps))`

---

## B.4 `ts_align/models/time_encoder.py`

### 职责
Patch-based time encoder：输出 patch tokens embedding，用于 global pooling 与 local ROI pooling。

### 必须提供
- `class PatchTimeEncoder(nn.Module)`
  - `__init__(in_channels, d_model=256, patch_size=16, n_layers=6, n_heads=8, dropout=0.1)`
  - `forward(x:[B,C,T], lengths:[B]) -> (H:[B,N,D], patch_mask:[B,N])`

### 关键实现建议
- `Conv1d(kernel=patch_size, stride=patch_size)` 生成 patch embeddings
- TransformerEncoder（batch_first=True）
- key_padding_mask = ~patch_mask

---

## B.5 `ts_align/models/text_encoder.py`

### 职责
文本编码器，支持两种模式：
- **HF 模式**：若安装 transformers 且提供 model_name → AutoModel + mean pooling
- **Fallback 模式**：自包含 byte-level Transformer（保证工程可跑）

### 必须提供
- `class TextEncoder(nn.Module)`
  - `__init__(model_name=None, d_model=256, n_layers=4, n_heads=8, max_len=256, dropout=0.1)`
  - `forward(texts:List[str]) -> Tensor [B,Dt]`
  - `out_dim:int`（供上层 projection）

---

## B.6 `ts_align/models/hsa_clip.py`

### 职责
组合 time encoder + text encoder + projection heads，形成共享 embedding 空间。

### 必须提供
- `class HSAClipModel(nn.Module)`
  - `encode_time(x, lengths) -> {"H","patch_mask","z_patch","z_global"}`
  - `encode_text(texts) -> z_text:[B,E]`
  - `get_scale() -> Tensor`（logit_scale.exp() clamp）
- 参数：
  - `d_embed`：共享对齐维度
  - `logit_scale`：CLIP temperature

### 约束
- `z_patch/z_global/z_text` 必须 L2 normalize（对比学习稳定性）

---

## B.7 `ts_align/losses.py`

### 职责
定义三种损失：
1) `clip_infonce`：global CLIP loss
2) `local_clip_infonce`：local CLIP loss（span pooled ts embedding vs local text embedding）
3) `span_localization_loss`：query→patch 分布在 GT span 内最大（均匀交叉熵或等价）

### 必须提供
- `clip_infonce(z_a:[B,E], z_b:[B,E], logit_scale) -> scalar`
- `local_clip_infonce(z_ts:[M,E], z_txt:[M,E], logit_scale) -> scalar`
- `span_localization_loss(z_patch:[B,N,E], patch_mask:[B,N], z_query:[M,E], local_batch_idx:[M], local_ps:[M], local_pe:[M], logit_scale) -> scalar`

---

## B.8 `ts_align/metrics.py`

### 职责
评估工具：
- retrieval recall@k：global text->time / time->text
- grounding IoU：给定 query 与 patch scores，预测最优 span，计算 IoU

### 必须提供
- `recall_at_k(sim:[N,N], ks=[1,5,10]) -> Dict[int,float]`
- `iou_1d([a0,a1), [b0,b1)) -> float`
- `best_span_same_len(scores:[N], mask:[N], span_len:int) -> (s,e)`

---

## B.9 `ts_align/train_cli.py`

### 职责
训练入口 CLI：
- 读取 train/val jsonl
- 构建 dataloader + model + optimizer
- 训练 loop（global + λlocal + λloc）
- 每 epoch 评估 retrieval + grounding
- 保存 checkpoint

### 必须提供
- argparse 参数：
  - `--train_jsonl --val_jsonl`
  - `--batch_size --epochs --lr --weight_decay`
  - `--patch_size --d_model --time_layers --time_heads`
  - `--text_model_name`（可选）
  - `--lambda_local --lambda_loc --max_local_per_sample`
  - `--out_dir`
- `evaluate(model, loader, device)`：打印 R@k 与 mIoU@1

---

# 4. 关键扩展点（研究/论文可用）

## 4.1 数据侧扩展
- `features.extract_salient_windows`：
  - 可加入 `ruptures` change points → 提供更准确的事件 proposal
  - 可加入 volatility burst、mean shift、frequency shift 等更丰富事件类型

- `claims.build_claims`：
  - 加入 event 类型：level shift、variance change、period change
  - 每类 claim 必须能复算 validate

- `render_structured_zh`：
  - local caption 可按 type 使用更丰富短语模板
  - 支持多语言（zh/en）

## 4.2 模型侧扩展（HSA）
- multi-positive：同一 span 的多个 text variants 同时作为正样本
- hard negatives：同一序列内其他 spans 作为强负
- boundary head：直接预测 start/end（替代 fixed length window）

---

# 5. Quick Start（建议）

## 5.1 生成 JSONL（ts_capv2）
- 准备 config 或 CLI 参数，调用 `ts_capv2/cli.py`
- 输出 `train.jsonl / val.jsonl`

## 5.2 训练对齐（ts_align）
```bash
python -m ts_align.train_cli \
  --train_jsonl /path/train.jsonl \
  --val_jsonl /path/val.jsonl \
  --batch_size 16 \
  --epochs 5 \
  --patch_size 16 \
  --out_dir runs/hsa
````

如安装 transformers 并希望用大型 text encoder：

```bash
python -m ts_align.train_cli ... --text_model_name BAAI/bge-m3
```

---

# 6. 最低限度的工程质量要求（强烈建议遵循）

* 所有关键结构（Claim、StructuredSummary、dense_captions）必须在文档中有明确 schema，且代码严格遵守
* “span 的起止”必须统一为 inclusive，patch 映射时才转为 exclusive
* LLM 输出必须 JSON 可解析，否则回退到 rule/template 结果
* 任何 claim 的文本描述必须可追溯到 claim.data，不能生成“未计算过”的事实

---

# 7. 单元测试建议（可选但推荐）

* features：

  * std≈0、短序列、包含 nan 的相关计算稳定性
* claims：

  * validate_claim 对每个 type 的复算一致性
* render：

  * seed 固定时输出稳定
  * local captions start/end 与 claim 一致
* ts_align：

  * collate 的 span->patch 映射正确
  * loss 不产生 nan，mask 正确屏蔽 padding

---

## 附：必须统一的字段命名建议（避免后续训练混乱）

* `record["descriptions"][0]`：默认 global 文本（兼容旧逻辑）
* `record["dense_captions"]["global"]`：更干净的 global summary（优先用）
* `record["dense_captions"]["local"]`：局部 spans（优先用）
* `record["claims"]`：可解释性与 fallback 生成 local 的来源
* `record["features"]["salient_segments"]`：proposal（供 LLM 合并/筛选）

---

