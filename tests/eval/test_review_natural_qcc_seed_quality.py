import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/eval/review_natural_qcc_seed_quality.py"


def load_module():
    spec = importlib.util.spec_from_file_location("review_natural_qcc_seed_quality", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_review_distinguishes_qa_ready_from_caption_ready():
    module = load_module()
    row = {
        "id": "row1",
        "merge_source_name": "grid2op",
        "task_family": "self_contained_grid_counterfactual_risk",
        "scene_zh": "电网调度员比较计划断线和正常运行，x0 为压力差。",
        "decision_rule_zh": "若 x0 均值 >= 0.05 且比例 >= 0.80，则风险上升；若 |x0| <= 0.02，则基本不变。",
        "variables_zh": ["x0 压力差", "x1 高风险比例"],
        "question_zh": "调度员应如何判断断线影响？",
        "options_zh": ["A. 风险上升", "B. 风险下降", "C. 基本不变", "D. 需要复核"],
        "natural_evidence_caption": "Mean x0 is 0.01, so the rule maps this to unchanged.",
        "natural_evidence_zh": "x0 均值为 0.01，按规则判断为风险基本不变。",
        "target_caption": "Mean x0 is 0.01. Answer label: risk is broadly unchanged.",
        "background_self_contained": True,
        "simulator_prior_required": False,
        "requires_reasoning": True,
        "review_naturalness_score": 4,
        "review_answerability_score": 5,
        "review_accuracy_risk": "low",
    }
    probe = {
        "row1": {
            "semantic_correct": True,
            "letter_correct": True,
            "label_letter_mismatch": False,
        }
    }

    review = module.review_self_row(row, probe)

    assert review["qa_seed_ready"] is True
    assert review["caption_train_ready"] is False
    assert any(issue["code"] == "target_caption_answer_label_leak" for issue in review["issues"])


def test_gpt_data_only_wrong_triggers_attribution_not_qa_reject():
    module = load_module()
    row = {
        "id": "row2",
        "merge_source_name": "citylearn",
        "task_family": "self_contained_building_net_load_reserve",
        "scene_zh": "建筑控制器比较早中晚三段净负荷，x3 是净电网负荷。",
        "decision_rule_zh": "若最高一段 x3 均值比第二高至少高 0.30，则为该段预留；否则均衡供能。",
        "variables_zh": ["x0 总用电", "x2 太阳能", "x3 净电网负荷"],
        "question_zh": "应在哪个时段优先预留供能？",
        "options_zh": ["A. 早段", "B. 中段", "C. 后段", "D. 均衡供能"],
        "natural_evidence_caption": "Early, middle, and late net loads are 5.33, 4.75, and 5.26. The top gap is only 0.08, below the 0.30 reserve threshold.",
        "natural_evidence_zh": "早中晚净负荷均值为 5.33、4.75、5.26，最高和第二高只差 0.08，低于 0.30 的预留阈值。",
        "target_caption": "Early, middle, and late net loads are 5.33, 4.75, and 5.26. The top gap is only 0.08, below the 0.30 reserve threshold.",
        "background_self_contained": True,
        "simulator_prior_required": False,
        "requires_reasoning": True,
        "review_naturalness_score": 5,
        "review_answerability_score": 5,
        "review_accuracy_risk": "low",
    }
    probe = {
        "row2": {
            "semantic_correct": False,
            "letter_correct": False,
            "label_letter_mismatch": True,
        }
    }

    review = module.review_self_row(row, probe)

    assert review["qa_seed_ready"] is True
    assert review["caption_train_ready"] is True
    assert review["needs_manual_error_attribution"] is True
    assert review["gpt_data_only_probe_status"] == "needs_manual_error_attribution"
    assert any(issue["severity"] == "diagnostic" for issue in review["issues"])


def test_case_review_flags_vague_variable_definition():
    module = load_module()
    row = {
        "id": "case1",
        "merge_source_name": "finrl",
        "task_family": "fin_domain_market_regime",
        "scene_zh": "市场分析师查看窗口。x0 是价格，x1 是市场背景价格信号，x2 是成交量。",
        "rule_zh": "收益接近零但波动较高时，按高波动横盘处理，阈值为 0.05。",
        "question_zh": "这段窗口属于哪种行情？",
        "options_zh": ["A. 偏多", "B. 高波动横盘", "C. 偏空", "D. 低波动横盘"],
        "answer_zh": "高波动横盘",
        "answer_label": "volatile sideways",
        "caption_zh": "总收益约 0.19%，波动约 0.065，因此是高波动横盘。",
        "caption_en": "Total return is about 0.19%, and volatility is about 0.065.",
    }

    review = module.review_case_row(row)

    assert review["qa_seed_ready"] is True
    assert any(issue["code"] == "vague_variable_definition" for issue in review["issues"])
