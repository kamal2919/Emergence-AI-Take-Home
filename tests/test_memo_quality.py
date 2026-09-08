"""Hand-labelled memo quality checks against the research fixture."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from signaldesk.analysis import analyze
from signaldesk.models import Candidate
from signaldesk.render import render_memo


FIXTURE = Path(__file__).parent / "fixtures" / "memo_quality_labels.json"
DATA = Path(__file__).parents[1] / "data" / "yc_ai_workflows.json"


def _load_candidates() -> dict[str, Candidate]:
    raw = json.loads(DATA.read_text())
    return {item["name"]: Candidate.from_dict(item) for item in raw["candidates"]}


class MemoQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = _load_candidates()
        cls.labels = json.loads(FIXTURE.read_text())

    def test_labelled_set_size(self):
        self.assertGreaterEqual(len(self.labels), 3)
        self.assertLessEqual(len(self.labels), 5)

    def test_hand_labelled_memo_quality(self):
        for label in self.labels:
            with self.subTest(company=label["company"]):
                candidate = self.candidates[label["company"]]
                analysis = analyze(candidate)
                memo = render_memo(analysis)
                memo_lower = memo.lower()

                self.assertEqual(analysis.recommendation, label["expected_recommendation"])
                low, high = label["expected_score_range"]
                self.assertGreaterEqual(analysis.total, low)
                self.assertLessEqual(analysis.total, high)
                self.assertGreaterEqual(len(candidate.evidence), label["min_evidence_records"])
                for theme in label["required_evidence_themes"]:
                    self.assertIn(theme, memo_lower)
                for phrase in label["changes_mind_must_include"]:
                    self.assertIn(phrase, memo_lower)
                self.assertLessEqual(len(memo.splitlines()), label["max_memo_lines"])


if __name__ == "__main__":
    unittest.main()
