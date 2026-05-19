from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.eval.audit_natural_qcc_caption_quality import quality_for_row, summarize


GOLD = {
    "id": "row-1",
    "split": "test",
    "merge_source_name": "grid2op",
    "task_family": "trend",
    "answer_label": "late stress",
    "options": [
        "A. early stress",
        "B. late stress",
        "C. flat",
        "D. unclear",
    ],
}


class AuditNaturalQccCaptionQualityTest(unittest.TestCase):
    def test_detects_answer_label_only_caption(self):
        row = quality_for_row(
            {
                "id": "row-1",
                "pred_caption": "A locally trained question-conditioned caption ranker selected this answer label. Answer label: late stress.",
            },
            GOLD,
            caption_field="pred_caption",
            min_caption_chars=40,
        )

        self.assertTrue(row["answer_label_only"])
        self.assertFalse(row["has_numeric_evidence"])
        self.assertFalse(row["evidence_shaped"])

    def test_accepts_numeric_evidence_caption(self):
        row = quality_for_row(
            {
                "id": "row-1",
                "pred_caption": (
                    "The first half mean is 0.42 while the second half mean is 0.87, "
                    "so the stress is concentrated late in the window."
                ),
            },
            GOLD,
            caption_field="pred_caption",
            min_caption_chars=40,
        )

        self.assertFalse(row["answer_label_only"])
        self.assertTrue(row["has_numeric_evidence"])
        self.assertTrue(row["evidence_shaped"])

    def test_plain_sentence_initial_a_is_not_option_leak(self):
        row = quality_for_row(
            {
                "id": "row-1",
                "pred_caption": (
                    "A dispatcher sees the first half mean at 0.42 and the second half "
                    "mean at 0.87, indicating late stress."
                ),
            },
            GOLD,
            caption_field="pred_caption",
            min_caption_chars=40,
        )

        self.assertFalse(row["option_letter_leak"])

    def test_summary_gate_requires_evidence_shape_and_low_answer_label_rate(self):
        good = quality_for_row(
            {
                "id": "row-1",
                "pred_caption": "The early value is 0.20 and the late value is 0.91, so the late segment is higher.",
            },
            GOLD,
            caption_field="pred_caption",
            min_caption_chars=40,
        )
        bad = quality_for_row(
            {"id": "row-2", "pred_caption": "Answer label: late stress."},
            {**GOLD, "id": "row-2"},
            caption_field="pred_caption",
            min_caption_chars=40,
        )

        metrics = summarize([good, bad], min_evidence_shape_rate=0.8, max_answer_label_only_rate=0.2)

        self.assertEqual(metrics["n"], 2)
        self.assertEqual(metrics["evidence_shape_rate"], 0.5)
        self.assertFalse(metrics["quality_gate_pass"])


if __name__ == "__main__":
    unittest.main()
