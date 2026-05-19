from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.eval.audit_natural_qcc_gpu_qcond_vs_noquestion import decision


class AuditNaturalQccGpuQcondVsNoQuestionTest(unittest.TestCase):
    def test_incomplete_blocks_comparison_claim(self):
        qcond = {"audit_pass": False, "generated_accuracy": None}
        noq = {"audit_pass": True, "generated_accuracy": 0.2}

        result = decision(qcond, noq, min_gap=0.05)

        self.assertEqual(result["status"], "incomplete_or_blocked")
        self.assertEqual(result["claim_scope"], "No q-conditioning training comparison allowed.")

    def test_positive_gap(self):
        qcond = {"audit_pass": True, "generated_accuracy": 0.5}
        noq = {"audit_pass": True, "generated_accuracy": 0.4}

        result = decision(qcond, noq, min_gap=0.05)

        self.assertEqual(result["status"], "qconditioning_gap_positive")
        self.assertAlmostEqual(result["qcond_minus_no_question"], 0.1)

    def test_no_gap(self):
        qcond = {"audit_pass": True, "generated_accuracy": 0.4}
        noq = {"audit_pass": True, "generated_accuracy": 0.4}

        result = decision(qcond, noq, min_gap=0.05)

        self.assertEqual(result["status"], "no_qconditioning_gap")
        self.assertEqual(result["qcond_minus_no_question"], 0.0)


if __name__ == "__main__":
    unittest.main()
