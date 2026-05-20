from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.eval.evaluate_natural_qcc_semantic_predictions import answer_from_caption


class EvaluateNaturalQccSemanticPredictionsTest(unittest.TestCase):
    def test_contextual_temporal_phrase_avoids_option_list_trap(self):
        row = {
            "answer": "D",
            "answer_label": "early",
            "options": ["A. middle", "B. late", "C. similar thirds", "D. early"],
        }
        caption = (
            "The window is split into early, middle, and late thirds. Their standard "
            "deviations are 422.20, 0.00, and 0.00, supporting the early part of the window."
        )

        pred_answer, pred_label, reason = answer_from_caption(row, caption)

        self.assertEqual((pred_answer, pred_label), ("D", "early"))
        self.assertTrue(reason.startswith("semantic_context_pattern:"))

    def test_temporal_label_list_without_context_is_ambiguous(self):
        row = {
            "answer": "D",
            "answer_label": "early",
            "options": ["A. middle", "B. late", "C. similar thirds", "D. early"],
        }
        caption = "The options are early, middle, and late."

        pred_answer, _, reason = answer_from_caption(row, caption)

        self.assertEqual(pred_answer, "")
        self.assertEqual(reason, "ambiguous_label_list")

    def test_numeric_similar_halves(self):
        row = {
            "answer": "A",
            "answer_label": "similar halves",
            "options": ["A. similar halves", "B. first half higher", "C. second half higher", "D. cannot determine"],
        }
        caption = (
            "Rule: if the two half-window means differ by less than 5% of the larger mean, "
            "treat them as similar. The first-half memory mean is 797,644.80, and the second-half mean is 801,177.60."
        )

        self.assertEqual(answer_from_caption(row, caption), ("A", "similar halves", "semantic_numeric_similar_halves"))

    def test_zero_gap_maps_to_no_material_change(self):
        row = {
            "answer": "C",
            "answer_label": "no material pressure change",
            "options": [
                "A. pressure increases",
                "B. pressure decreases",
                "C. no material pressure change",
                "D. cannot determine",
            ],
        }
        caption = "Factual event-window pressure mean is 80.66, baseline mean is 80.66, and the gap is 0.00."

        self.assertEqual(answer_from_caption(row, caption), ("C", "no material pressure change", "semantic_numeric_zero_gap"))

    def test_rule_hypothesis_does_not_override_observed_false_flag(self):
        row = {
            "answer": "C",
            "answer_label": "moderate combined stress",
            "options": [
                "A. critical combined stress",
                "B. stable combined state",
                "C. moderate combined stress",
                "D. unclear combined state",
            ],
        }
        caption = (
            "Stress rule: scores below -50 with a mid-window event indicate moderate combined stress "
            "when the severe-low-pressure flag is false; if that flag is true, classify as critical combined stress. "
            "The combined stress score is -66.31, the event timing label is middle, and the severe-low-pressure flag is False."
        )

        self.assertEqual(answer_from_caption(row, caption), ("C", "moderate combined stress", "semantic_numeric_moderate_combined_stress"))

    def test_stable_water_service_from_observed_pressure(self):
        row = {
            "answer": "B",
            "answer_label": "stable water service",
            "options": ["A. leak-stressed network", "B. stable water service", "C. low-pressure risk", "D. unclear hydraulic state"],
        }
        caption = (
            "Service-state rule: minimum pressure below 50 suggests low-pressure risk; stable pressure above that level "
            "with no leak-stress evidence suggests stable water service. Mean pressure is 83.38, minimum pressure is 58.37, and mean flow is 11.21."
        )

        self.assertEqual(answer_from_caption(row, caption), ("B", "stable water service", "semantic_numeric_stable_water_service"))

    def test_traffic_recovery_numeric_persistent_congestion(self):
        row = {
            "answer": "C",
            "answer_label": "persistent congestion",
            "options": [
                "A. traffic speed recovers",
                "B. traffic speed overshoots",
                "C. congestion persists",
                "D. no event recovery",
            ],
        }
        caption = (
            "Recovery rule: if post-event speed returns close to pre-event speed, classify as speed recovers; "
            "if it rises above pre-event speed, classify as speed overshoot; if it remains close to event speed "
            "and far below pre-event speed, classify as persistent congestion. Pre-event mean speed is 41.51, "
            "event mean is 12.94, and post-event mean speed is 14.36."
        )

        self.assertEqual(answer_from_caption(row, caption), ("C", "congestion persists", "semantic_numeric_persistent_congestion"))

    def test_pressure_recovery_numeric_recovers(self):
        row = {
            "answer": "D",
            "answer_label": "pressure recovers",
            "options": [
                "A. persistent pressure stress",
                "B. pressure overshoot",
                "C. no event recovery",
                "D. pressure recovers",
            ],
        }
        caption = (
            "Recovery rule: post-event pressure above pre-event pressure is overshoot; if event pressure is lower "
            "than pre-event pressure and post-event pressure rises above event pressure without exceeding pre-event "
            "pressure, classify as pressure recovers; if post-event pressure does not rise above event pressure and "
            "remains below pre-event pressure, classify as persistent pressure stress. Pre-event mean is 80.79, "
            "event mean is 80.64, and post-event mean is 80.72."
        )

        self.assertEqual(answer_from_caption(row, caption), ("D", "pressure recovers", "semantic_numeric_pressure_recovers"))


if __name__ == "__main__":
    unittest.main()
