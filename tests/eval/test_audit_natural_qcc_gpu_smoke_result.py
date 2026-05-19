from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.eval.audit_natural_qcc_gpu_smoke_result import build_decision


BASELINE = {
    "natural_oracle": 1.0,
    "generic_caption": 0.0,
    "statistical_caption": 0.0,
    "question_only": 0.2,
}


class AuditNaturalQccGpuSmokeResultTest(unittest.TestCase):
    def test_build_decision_incomplete_blocks_claims(self):
        decision = build_decision(audit_pass=False, generated_acc=None, baseline=BASELINE)

        self.assertEqual(decision["status"], "incomplete_or_blocked")
        self.assertFalse(decision["beats_all_non_oracle_baselines"])
        self.assertEqual(decision["claim_scope"], "No training-result claim allowed.")

    def test_build_decision_complete_but_no_improvement(self):
        decision = build_decision(audit_pass=True, generated_acc=0.1, baseline=BASELINE)

        self.assertEqual(decision["status"], "smoke_no_improvement_over_local_non_oracle_baselines")
        self.assertFalse(decision["beats_question_only"])
        self.assertEqual(decision["oracle_gap"], 0.9)

    def test_build_decision_complete_and_improves(self):
        decision = build_decision(audit_pass=True, generated_acc=0.4, baseline=BASELINE)

        self.assertEqual(decision["status"], "smoke_improves_over_local_non_oracle_baselines")
        self.assertEqual(decision["baseline_max_non_oracle"], 0.2)
        self.assertTrue(decision["beats_all_non_oracle_baselines"])
        self.assertTrue(decision["beats_question_only"])
        self.assertEqual(decision["claim_scope"], "AIOps smoke only; not a cross-domain method claim.")


if __name__ == "__main__":
    unittest.main()
