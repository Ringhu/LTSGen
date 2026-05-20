from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.eval.check_natural_qcc_gpu_smoke_preflight import summarize_token_budget


class FakeTokenizer:
    eos_token_id = 0

    def __call__(self, text, add_special_tokens=False):
        return {"input_ids": list(range(len(str(text).split())))}

    def decode(self, ids, skip_special_tokens=True):
        visible = [idx for idx in ids if not (skip_special_tokens and idx == self.eos_token_id)]
        return " ".join(f"tok{idx}" for idx in visible)


class CheckNaturalQccGpuSmokePreflightTest(unittest.TestCase):
    def test_token_budget_detects_zero_output_supervision(self):
        rows = [
            {
                "id": "row-long-prompt",
                "prompt": " ".join(["prompt"] * 227),
                "output": "Evidence: value 1.0.",
            }
        ]
        path = Path(self.create_jsonl(rows))

        summary = summarize_token_budget(
            path,
            tokenizer=FakeTokenizer(),
            max_text_length=224,
            max_prompt_length=320,
            add_eos=True,
        )

        self.assertEqual(summary["zero_output_kept"], 1)
        self.assertEqual(summary["output_truncated"], 1)
        self.assertEqual(summary["eos_only_supervision"], 1)
        self.assertEqual(summary["examples"][0]["output_kept_tokens"], 0)

    def test_token_budget_passes_when_full_output_fits(self):
        rows = [
            {
                "id": "row-fits",
                "prompt": " ".join(["prompt"] * 30),
                "output": "Evidence: value 1.0 Decision rule Therefore",
            }
        ]
        path = Path(self.create_jsonl(rows))

        summary = summarize_token_budget(
            path,
            tokenizer=FakeTokenizer(),
            max_text_length=80,
            max_prompt_length=60,
            add_eos=True,
        )

        self.assertEqual(summary["zero_output_kept"], 0)
        self.assertEqual(summary["output_truncated"], 0)
        self.assertEqual(summary["prompt_truncated"], 0)
        self.assertGreater(summary["examples"][0]["labels_non_ignored"], 1)

    def create_jsonl(self, rows):
        import json
        import tempfile

        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
        with handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")
        return handle.name


if __name__ == "__main__":
    unittest.main()
