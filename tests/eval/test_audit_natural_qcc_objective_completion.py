from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.eval.audit_natural_qcc_objective_completion import objective_decision


BASE_CHECKS = {
    "dataset_schema_gate_pass": True,
    "positive_dataset_rows_present": True,
    "sft_split_files_present": True,
    "no_question_control_gate_pass": True,
    "probe_results_present": True,
    "oracle_evidence_baseline_present": True,
    "non_oracle_baselines_present": True,
    "oracle_caption_load_bearing": True,
    "qcond_gpu_audit_pass": True,
    "no_question_gpu_audit_pass": True,
    "qcond_generated_metrics_present": True,
    "no_question_generated_metrics_present": True,
    "qcond_vs_no_question_comparison_complete": True,
    "safe_result_manifest_pass": True,
    "safe_result_manifest_has_no_unsafe_paths": True,
}


class AuditNaturalQccObjectiveCompletionTest(unittest.TestCase):
    def test_incomplete_blocks_objective_completion(self):
        checks = dict(BASE_CHECKS)
        checks["qcond_gpu_audit_pass"] = False
        result = objective_decision(
            checks,
            {
                "qcond_beats_all_non_oracle_baselines": True,
                "qcond_minus_no_question": 0.2,
                "min_gap": 0.05,
            },
        )

        self.assertFalse(result["objective_complete"])
        self.assertEqual(result["status"], "incomplete_or_blocked")
        self.assertIn("qcond_gpu_audit_pass", result["blockers"])

    def test_complete_positive_qcc_signal(self):
        result = objective_decision(
            BASE_CHECKS,
            {
                "qcond_beats_all_non_oracle_baselines": True,
                "qcond_minus_no_question": 0.1,
                "min_gap": 0.05,
            },
        )

        self.assertTrue(result["objective_complete"])
        self.assertEqual(result["status"], "complete_positive_qcc_signal")
        self.assertTrue(result["qcond_gap_meets_min"])

    def test_complete_negative_signal(self):
        result = objective_decision(
            BASE_CHECKS,
            {
                "qcond_beats_all_non_oracle_baselines": False,
                "qcond_minus_no_question": -0.1,
                "min_gap": 0.05,
            },
        )

        self.assertTrue(result["objective_complete"])
        self.assertEqual(result["status"], "complete_negative_signal")
        self.assertFalse(result["qcond_beats_no_question"])


if __name__ == "__main__":
    unittest.main()
