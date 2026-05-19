from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.generate.build_natural_qcc_no_question_control import build_no_question_prompt, transform_row


class BuildNaturalQccNoQuestionControlTest(unittest.TestCase):
    def test_prompt_removes_question_but_keeps_scene_and_variables(self):
        prompt = (
            "You are a question-conditioned time-series evidence captioner.\n\n"
            "Scene: A grid operator reviews a window.\n"
            "Variables: x0 max rho; x1 demand\n"
            "Question: Which period has the highest stress?"
        )

        control_prompt, info = build_no_question_prompt(prompt)

        self.assertNotIn("Question:", control_prompt)
        self.assertIn("Scene: A grid operator reviews a window.", control_prompt)
        self.assertIn("Variables: x0 max rho; x1 demand", control_prompt)
        self.assertEqual(info["removed_question"], "Which period has the highest stress?")

    def test_transform_row_marks_prompt_control(self):
        row = {
            "id": "row1",
            "values": [[0.0]],
            "prompt": "Scene: Test scene\nVariables: x0\nQuestion: Hidden question?",
            "output": "Answer label: stable.",
            "meta": {"merge_source_name": "unit"},
        }

        transformed, _ = transform_row(row)

        self.assertNotIn("Question:", transformed["prompt"])
        self.assertEqual(transformed["output"], row["output"])
        self.assertEqual(transformed["meta"]["prompt_control"], "no_question")
        self.assertFalse(transformed["meta"]["question_conditioned"])
        self.assertEqual(transformed["meta"]["removed_question_en"], "Hidden question?")


if __name__ == "__main__":
    unittest.main()
