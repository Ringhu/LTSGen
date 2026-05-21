import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/eval/run_natural_qcc_seed_smoke_v1.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_natural_qcc_seed_smoke_v1", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_local_preflight_detects_output_truncation():
    module = load_module()
    rows = [
        {
            "id": "row1",
            "prompt": " ".join(["prompt"] * 8),
            "output": " ".join(["evidence"] * 20),
        }
    ]

    summary = module.summarize_preflight(rows, max_text_length=12, max_prompt_length=20)

    assert summary["zero_output_kept"] == 0
    assert summary["output_truncated"] == 1
    assert summary["gate_pass"] is False


def test_caption_quality_requires_target_focus():
    module = load_module()
    target = "Mean x0 is 5.00 and peak x1 is 9.00, indicating high demand pressure."
    focused = "Mean x0 is 5.00 and peak x1 is 9.00, indicating high demand pressure."
    generic = "The compact window has 12 blocks. Generic summary: x0 mean 4.91, x1 mean 3.20."

    focused_q = module.caption_quality(focused, target)
    generic_q = module.caption_quality(generic, target)

    assert focused_q["quality_pass"] is True
    assert generic_q["evidence_shaped"] is True
    assert generic_q["answer_focused"] is False
    assert generic_q["quality_pass"] is False


def test_no_question_prompt_removes_question_and_options():
    module = load_module()
    row = {
        "id": "row2",
        "prompt": "Scene: abc\nVariables: x0 value\nQuestion: choose one?\nOptions: A. one; B. two",
        "values": [[1.0]],
        "output": "x0 is 1.00.",
    }

    transformed = module.sft_row(row, no_question=True)

    assert "Question:" not in transformed["prompt"]
    assert "Options:" not in transformed["prompt"]
    assert transformed["meta"]["prompt_control"] == "no_question"
