from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.eval.collect_natural_qcc_gpu_result_manifest import SAFE_RELATIVE_FILES, has_unsafe_path


class CollectNaturalQccGpuResultManifestTest(unittest.TestCase):
    def test_safe_file_list_excludes_checkpoints(self):
        joined = "\n".join(SAFE_RELATIVE_FILES)

        self.assertNotIn("final_model", joined)
        self.assertNotIn("pytorch_model.bin", joined)
        self.assertNotIn("safetensors", joined)
        self.assertIn("generate_eval_test_clean/predictions.jsonl", joined)
        self.assertIn("generate_eval_test_clean/rule_qa/qa_metrics.json", joined)

    def test_unsafe_path_detection(self):
        self.assertTrue(has_unsafe_path([{"path": "run/final_model/pytorch_model.bin"}]))
        self.assertTrue(has_unsafe_path([{"path": "run/checkpoint-10/model.safetensors"}]))
        self.assertFalse(has_unsafe_path([{"path": "run/generate_eval_test_clean/predictions.jsonl"}]))


if __name__ == "__main__":
    unittest.main()
