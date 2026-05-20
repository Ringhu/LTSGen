import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.generate.merge_natural_qcc_positive_sets import summarize
from scripts.generate.select_natural_qcc_expansion_candidates import load_exclude_ids, select_rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


class NaturalQccExpansionUtilsTest(unittest.TestCase):
    def test_load_exclude_ids_combines_existing_jsonl_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            first = tmp_path / "first.jsonl"
            second = tmp_path / "second.jsonl"
            missing = tmp_path / "missing.jsonl"
            write_jsonl(first, [{"id": "row-a"}, {"id": "row-b"}])
            write_jsonl(second, [{"id": "row-b"}, {"id": "row-c"}])

            self.assertEqual(load_exclude_ids([first, second, missing]), {"row-a", "row-b", "row-c"})

    def test_select_rows_skips_excluded_ids(self):
        rows = [
            {"id": "a1", "merge_source_name": "grid2op", "task_family": "trend", "split": "train"},
            {"id": "a2", "merge_source_name": "grid2op", "task_family": "trend", "split": "train"},
            {"id": "b1", "merge_source_name": "grid2op", "task_family": "extrema", "split": "train"},
        ]

        selected = select_rows(rows, per_source=3, seed=7, exclude_ids={"a1", "b1"})

        self.assertEqual([row["id"] for row in selected], ["a2"])

    def test_merge_summary_reports_duplicate_ids_and_required_fields(self):
        valid = {
            "id": "row-1",
            "values": [[1.0]],
            "question": "Which condition holds?",
            "options": ["A. one", "B. two", "C. three", "D. four"],
            "answer": "A",
            "answer_label": "one",
            "support_slots": {"x": 1},
            "merge_source_name": "traffic",
            "split": "test",
        }
        duplicate = dict(valid)
        missing = dict(valid, id="row-2", values=[])

        summary = summarize([valid, duplicate, missing])

        self.assertEqual(summary["duplicate_id_count"], 1)
        self.assertEqual(summary["by_source"], {"traffic": 3})
        self.assertEqual(summary["missing_required_count"], 1)


if __name__ == "__main__":
    unittest.main()
