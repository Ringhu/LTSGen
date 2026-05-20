from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.eval.collect_natural_qcc_gpu_result_manifest import SAFE_RELATIVE_FILES, audit_items, has_unsafe_path, run_items


class CollectNaturalQccGpuResultManifestTest(unittest.TestCase):
    def test_safe_file_list_excludes_checkpoints(self):
        joined = "\n".join(SAFE_RELATIVE_FILES)

        self.assertNotIn("final_model", joined)
        self.assertNotIn("pytorch_model.bin", joined)
        self.assertNotIn("safetensors", joined)
        self.assertIn("generate_eval_test_clean/predictions.jsonl", joined)
        self.assertIn("generate_eval_test_clean/rule_qa/qa_metrics.json", joined)
        self.assertIn("generate_eval_test_clean/rule_qa/semantic_qa_metrics.json", joined)
        self.assertIn("natural_qcc_caption_quality_audit.json", joined)
        self.assertIn("natural_qcc_caption_quality_audit.rows.jsonl", joined)
        self.assertNotIn("natural_qcc_objective_completion_audit", joined)

    def test_run_items_can_require_semantic_qa_files(self):
        items = run_items(Path("run"), qa_kind="semantic")
        required = [item["path"] for item in items if item["required"]]

        self.assertIn("run/generate_eval_test_clean/rule_qa/semantic_qa_metrics.json", required)
        self.assertIn("run/generate_eval_test_clean/rule_qa/semantic_qa_predictions.jsonl", required)
        self.assertNotIn("run/generate_eval_test_clean/rule_qa/qa_metrics.json", required)

    def test_unsafe_path_detection(self):
        self.assertTrue(has_unsafe_path([{"path": "run/final_model/pytorch_model.bin"}]))
        self.assertTrue(has_unsafe_path([{"path": "run/checkpoint-10/model.safetensors"}]))
        self.assertFalse(has_unsafe_path([{"path": "run/generate_eval_test_clean/predictions.jsonl"}]))

    def test_manifest_requires_compare_and_objective_audits(self):
        items = audit_items(
            Path(".research/run/qcond_vs_noquestion.json"),
            Path(".research/run/objective_completion.json"),
        )
        paths = [item["path"] for item in items]

        self.assertIn(".research/run/qcond_vs_noquestion.json", paths)
        self.assertIn(".research/run/qcond_vs_noquestion.md", paths)
        self.assertIn(".research/run/objective_completion.json", paths)
        self.assertIn(".research/run/objective_completion.md", paths)
        self.assertTrue(all(item["required"] for item in items))


if __name__ == "__main__":
    unittest.main()
