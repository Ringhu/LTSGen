from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.generate.build_natural_qcc_evidence_only_sft import evidence_text, style_repaired_evidence_text, transform_row


class BuildNaturalQccEvidenceOnlySftTest(unittest.TestCase):
    def test_evidence_text_strips_answer_label_suffix(self):
        row = {
            "natural_evidence_caption": (
                "CPU starts near 0.00 and ends near 0.00, supporting a flat trend. "
                "Answer label: flat."
            )
        }

        self.assertEqual(evidence_text(row), "CPU starts near 0.00 and ends near 0.00, supporting a flat trend.")

    def test_qcond_transform_preserves_question_but_removes_label_target(self):
        row = {
            "id": "row1",
            "values": [[0.0, 1.0]],
            "scene_en": "A grid operator reviews a window.",
            "variables_en": ["x0 max rho", "x1 demand"],
            "question": "Which half has higher demand?",
            "options": ["A. first half higher", "B. second half higher", "C. similar", "D. cannot determine"],
            "natural_evidence_caption": "The first-half mean is 1.00 and the second-half mean is 2.00. Answer label: second half higher.",
            "answer": "B",
            "answer_label": "second half higher",
            "task_family": "window_compare",
            "merge_source_name": "unit",
            "meta": {},
        }

        out = transform_row(row, prompt_control="qcond")

        self.assertIn("Question: Which half has higher demand?", out["prompt"])
        self.assertNotIn("Options:", out["prompt"])
        self.assertNotIn("Answer label:", out["output"])
        self.assertEqual(out["target_caption"], "The first-half mean is 1.00 and the second-half mean is 2.00.")
        self.assertTrue(out["meta"]["question_conditioned"])

    def test_qcond_transform_can_include_options_without_target_leak(self):
        row = {
            "id": "row1",
            "values": [[0.0, 1.0]],
            "scene_en": "A grid operator reviews a window.",
            "variables_en": ["x0 max rho", "x1 demand"],
            "question": "Which half has higher demand?",
            "options": ["A. first half higher", "B. second half higher", "C. similar", "D. cannot determine"],
            "natural_evidence_caption": "The first-half mean is 1.00 and the second-half mean is 2.00. Answer label: second half higher.",
            "answer": "B",
            "answer_label": "second half higher",
            "task_family": "window_compare",
            "merge_source_name": "unit",
            "meta": {},
        }

        out = transform_row(row, prompt_control="qcond", include_options_in_prompt=True)

        self.assertIn("Options: A. first half higher; B. second half higher", out["prompt"])
        self.assertNotIn("Answer label:", out["output"])
        self.assertEqual(out["target_caption"], "The first-half mean is 1.00 and the second-half mean is 2.00.")
        self.assertTrue(out["meta"]["include_options_in_prompt"])

    def test_no_question_transform_removes_question(self):
        row = {
            "id": "row1",
            "values": [[0.0, 1.0]],
            "scene_en": "A traffic operator reviews a window.",
            "variables_en": ["x0 speed", "x1 queue"],
            "question": "Which variable changes more?",
            "natural_evidence_caption": "Speed changes by 12.00, while queue changes by 2.00.",
            "answer": "A",
            "answer_label": "speed changes more strongly",
            "task_family": "cross_relation",
            "merge_source_name": "unit",
            "meta": {},
        }

        out = transform_row(row, prompt_control="no_question")

        self.assertNotIn("Question:", out["prompt"])
        self.assertIn("Scene: A traffic operator reviews a window.", out["prompt"])
        self.assertFalse(out["meta"]["question_conditioned"])

    def test_style_repair_adds_uniform_numeric_evidence(self):
        row = {
            "id": "row1",
            "values": [[0.0, 1.0]],
            "scene_en": "A water operator reviews a service window.",
            "variables_en": ["x0 pressure", "x1 flow"],
            "question": "Which part is most variable?",
            "options": ["A. middle", "B. early", "C. late", "D. similar thirds"],
            "natural_evidence_caption": "The window is split into three equal sections and selects early.",
            "answer": "B",
            "answer_label": "early",
            "task_family": "water_flow_volatility",
            "merge_source_name": "water",
            "support_slots": {
                "region_stds": {"early": 18.410378, "middle": 1.814184, "late": 1.822276},
                "answer_label": "early",
                "window_start": 0,
                "window_end": 256,
            },
            "meta": {},
        }

        evidence = style_repaired_evidence_text(row)
        out = transform_row(row, prompt_control="qcond", style_repair=True)

        self.assertIn("Evidence:", evidence)
        self.assertIn("Decision rule:", evidence)
        self.assertIn("Therefore, early.", evidence)
        self.assertIn("early=18.41", evidence)
        self.assertIn("Evidence, Decision rule, Therefore", out["prompt"])
        self.assertTrue(out["meta"]["style_repair"])


if __name__ == "__main__":
    unittest.main()
