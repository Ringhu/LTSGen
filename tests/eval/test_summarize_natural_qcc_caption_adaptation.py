from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.eval.summarize_natural_qcc_caption_adaptation import as_float, markdown


class SummarizeNaturalQccCaptionAdaptationTest(unittest.TestCase):
    def test_as_float_rounds_and_handles_missing(self):
        self.assertEqual(as_float("0.12345"), 0.1235)
        self.assertIsNone(as_float(None))
        self.assertIsNone(as_float("not-a-number"))

    def test_markdown_lists_diagnostics_and_key_read(self):
        report = {
            "probe_results": "probe.json",
            "diagnostics": [
                {
                    "name": "nearest_caption_question_conditioned",
                    "kind": "train_split_nearest_caption_probe",
                    "qa_accuracy": 0.4615,
                    "evidence_shape_rate": 0.7692,
                    "answer_label_only_rate": 0.0,
                    "quality_gate_pass": False,
                }
            ],
            "summary": {
                "claim_scope": "local_caption_adaptation_diagnostic_not_final_qcc_training",
                "nearest_qcond_qa_minus_no_question": 0.2307,
                "nearest_qcond_quality_minus_no_question": -0.1539,
                "local_ranker_qcond_answer_label_only_rate": 1.0,
            },
        }

        text = markdown(report)

        self.assertIn("nearest_caption_question_conditioned", text)
        self.assertIn("0.4615", text)
        self.assertIn("0.2307", text)
        self.assertIn("not_final_qcc_training", text)


if __name__ == "__main__":
    unittest.main()
