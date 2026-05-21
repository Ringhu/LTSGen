from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tslm.scripts.generate_multisim_v5_smoke import clean_caption


class GenerateMultisimV5SmokeTest(unittest.TestCase):
    def test_clean_caption_keeps_evidence_after_leading_answer_prefix(self):
        raw = (
            'Answer: The memory working set has a relative difference of 0.3% '
            "between the first and second half of the window, which is below "
            "the 5% threshold.\n"
        )

        cleaned = clean_caption(raw, max_sentences=2)

        self.assertNotIn("Answer:", cleaned)
        self.assertIn("relative difference of 0.3%", cleaned)
        self.assertIn("5% threshold", cleaned)

    def test_clean_caption_rewrites_time_series_evidence_marker(self):
        raw = "Answer: Rising\nTime series evidence:\nx0 rises from 1.2 to 23.0."

        cleaned = clean_caption(raw, max_sentences=2)

        self.assertEqual(cleaned, "Rising Evidence: x0 rises from 1.2 to 23.0.")

    def test_clean_caption_still_truncates_prompt_echo(self):
        raw = "CPU starts at 0.0 and ends at 0.0. Question: Is CPU flat?"

        cleaned = clean_caption(raw, max_sentences=2)

        self.assertEqual(cleaned, "CPU starts at 0.0 and ends at 0.0.")


if __name__ == "__main__":
    unittest.main()
