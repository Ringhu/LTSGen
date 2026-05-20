from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.eval.audit_natural_qcc_slot_factuality import audit_one


def base_row(slots, *, answer_label):
    return {
        "id": "row-1",
        "split": "test",
        "merge_source_name": "unit",
        "task_family": "unit_task",
        "answer": "A",
        "answer_label": answer_label,
        "options": [f"A. {answer_label}", "B. distractor"],
        "support_slots": slots,
    }


class AuditNaturalQccSlotFactualityTest(unittest.TestCase):
    def test_region_std_passes_when_values_and_direction_match(self):
        gold = base_row(
            {
                "region_stds": {"early": 3.0, "middle": 1.0, "late": 2.0},
                "answer_label": "early",
                "window_start": 0,
                "window_end": 90,
            },
            answer_label="early",
        )
        pred = {
            "id": "row-1",
            "pred_caption": (
                "Evidence: section standard deviations are early=3.00, middle=1.00, late=2.00. "
                "Decision rule: choose the section with the largest standard deviation. Therefore, early."
            ),
        }

        row = audit_one(pred, gold, caption_field="pred_caption")

        self.assertTrue(row["slot_value_pass"])
        self.assertTrue(row["direction_pass"])
        self.assertTrue(row["overall_slot_factuality_pass"])

    def test_region_std_fails_when_values_imply_wrong_direction(self):
        gold = base_row(
            {
                "region_stds": {"early": 3.0, "middle": 1.0, "late": 2.0},
                "answer_label": "early",
                "window_start": 0,
                "window_end": 90,
            },
            answer_label="early",
        )
        pred = {
            "id": "row-1",
            "pred_caption": (
                "Evidence: section standard deviations are early=1.00, middle=4.00, late=2.00. "
                "Decision rule: choose the section with the largest standard deviation. Therefore, middle."
            ),
        }

        row = audit_one(pred, gold, caption_field="pred_caption")

        self.assertFalse(row["slot_value_pass"])
        self.assertEqual(row["predicted_direction"], "middle")
        self.assertFalse(row["direction_pass"])
        self.assertIn("slot_value_mismatch", row["failure_reasons"])
        self.assertIn("direction_mismatch", row["failure_reasons"])

    def test_extrema_horizon_mismatch_is_caught(self):
        gold = base_row(
            {
                "extrema_index": 809,
                "extrema_value": 1.119,
                "horizon": 2048,
                "window_start": 0,
                "window_end": 2048,
                "answer_label": "middle",
            },
            answer_label="middle",
        )
        pred = {
            "id": "row-1",
            "pred_caption": (
                "Evidence: the maximum value is 0.94 near local step 239 within the 512-step local window. "
                "Decision rule: split the local window into thirds. Therefore, middle."
            ),
        }

        row = audit_one(pred, gold, caption_field="pred_caption")

        self.assertFalse(row["slot_value_pass"])
        self.assertFalse(row["horizon_pass"])
        self.assertEqual(row["expected_horizon"], 2048)
        self.assertEqual(row["found_horizon"], 512)
        self.assertIn("horizon_mismatch", row["failure_reasons"])

    def test_counterfactual_diff_sign_fails_when_caption_reverses_direction(self):
        gold = base_row(
            {
                "mean_x0_diff": 0.067,
                "answer_label": "higher after intervention",
                "window_start": 0,
                "window_end": 256,
            },
            answer_label="higher after intervention",
        )
        pred = {
            "id": "row-1",
            "pred_caption": (
                "Evidence: mean intervention-minus-factual stress difference is -1.94. "
                "Decision rule: positive values mean average stress is higher after intervention. Therefore, lower."
            ),
        }

        row = audit_one(pred, gold, caption_field="pred_caption")

        self.assertFalse(row["slot_value_pass"])
        self.assertEqual(row["expected_direction"], "positive")
        self.assertEqual(row["predicted_direction"], "negative")
        self.assertFalse(row["direction_pass"])

    def test_half_window_mean_detects_wrong_values_even_if_label_is_similar(self):
        gold = base_row(
            {
                "first_mean": 797644.8,
                "second_mean": 801177.6,
                "answer_label": "similar halves",
                "window_start": 0,
                "window_end": 64,
            },
            answer_label="similar halves",
        )
        pred = {
            "id": "row-1",
            "pred_caption": (
                "Evidence: first-half mean is 1023.69, and second-half mean is -1024.87. "
                "Decision rule: compare the two half-window means. Therefore, similar halves."
            ),
        }

        row = audit_one(pred, gold, caption_field="pred_caption")

        self.assertFalse(row["slot_value_pass"])
        self.assertFalse(row["direction_pass"])
        self.assertFalse(row["overall_slot_factuality_pass"])


if __name__ == "__main__":
    unittest.main()
