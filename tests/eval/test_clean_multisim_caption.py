from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tslm/scripts"))

from generate_multisim_v5_smoke import clean_caption


class CleanMultisimCaptionTest(unittest.TestCase):
    def test_does_not_truncate_option_word_inside_evidence_sentence(self):
        text = (
            "The early, middle, and late options split the local window into three equal time sections. "
            "The minimum water pressure is about 54.72 near step 0 of the local window, supporting the early part of the window."
        )

        self.assertIn("minimum water pressure", clean_caption(text, max_sentences=2))

    def test_truncates_prompt_echo(self):
        text = (
            "The intervention-minus-factual stress difference ranges from 0.37 to 0.45 above baseline "
            "You are a question-conditioned time-series evidence captioner. Given the time series, scene, variables, and question"
        )

        cleaned = clean_caption(text, max_sentences=2)

        self.assertIn("0.37 to 0.45", cleaned)
        self.assertNotIn("You are a", cleaned)

    def test_truncates_chinese_continuation_after_complete_english_sentence(self):
        text = (
            "The demand-spike detector uses absolute z-score 3 as the pronounced-spike cutoff. "
            "The strongest candidate has absolute z-score about 2.74, supporting no pronounced spike."
            "规则：需求峰值检测器使用绝对z分数3作为显著峰值的截止值。"
        )

        cleaned = clean_caption(text, max_sentences=3)

        self.assertIn("2.74", cleaned)
        self.assertNotRegex(cleaned, r"[\u3400-\u9fff]")


if __name__ == "__main__":
    unittest.main()
