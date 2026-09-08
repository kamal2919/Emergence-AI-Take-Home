import unittest
import json
from pathlib import Path
from signaldesk.analysis import analyze
from signaldesk.llm import Enrichment, LLMError
from signaldesk.models import Candidate, Evidence
from signaldesk.sources.yc import collect_snapshot


def candidate(scores):
    return Candidate.from_dict({"name": "Test Co", "website": "https://example.com", "description": "A workflow tool.", "freshness_signal": "Launched.", "source_url": "https://example.com/source", "scores": scores})


class AnalysisTests(unittest.TestCase):
    def test_recommendation_bands(self):
        self.assertEqual(analyze(candidate({"workflow": 25, "wedge": 20, "demand": 20, "team": 15, "defensibility": 10, "execution": 10})).recommendation, "Take a meeting")
        self.assertEqual(analyze(candidate({"workflow": 15, "wedge": 12, "demand": 12, "team": 8, "defensibility": 5, "execution": 5})).recommendation, "Watch")
        self.assertEqual(analyze(candidate({"workflow": 10, "wedge": 10, "demand": 10, "team": 5, "defensibility": 5, "execution": 5})).recommendation, "Pass")

    def test_missing_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            Candidate.from_dict({"name": "Incomplete", "website": "https://example.com"})

    def test_invalid_score_is_rejected(self):
        with self.assertRaises(ValueError):
            analyze(candidate({"workflow": 26, "wedge": 20, "demand": 20, "team": 15, "defensibility": 10, "execution": 10}))

    def test_research_set_is_assignment_sized(self):
        fixture = Path(__file__).parents[1] / "data" / "yc_ai_workflows.json"
        self.assertGreaterEqual(len(json.loads(fixture.read_text())["candidates"]), 10)
        self.assertLessEqual(len(json.loads(fixture.read_text())["candidates"]), 20)

    def test_llm_cannot_cite_unsupplied_evidence(self):
        with self.assertRaises(LLMError):
            Enrichment.from_response({
                "team_summary": "Not established.", "product_summary": "A workflow tool.", "market_summary": "A market.",
                "risks": ["A risk."], "open_questions": ["A question."], "source_urls": ["https://not-supplied.example"],
            }, candidate({"workflow": 10, "wedge": 10, "demand": 10, "team": 5, "defensibility": 5, "execution": 5}), "test", "test-model")

    def test_valid_llm_enrichment_keeps_score_deterministic(self):
        c = candidate({"workflow": 10, "wedge": 10, "demand": 10, "team": 5, "defensibility": 5, "execution": 5})
        enrichment = Enrichment.from_response({
            "team_summary": "Not established in supplied evidence.", "product_summary": "A workflow tool.", "market_summary": "A market.",
            "risks": ["A risk."], "open_questions": ["A question."], "source_urls": [c.source_url],
        }, c, "test", "test-model")
        self.assertEqual(analyze(c, enrichment).total, 45)

    def test_evidence_defaults_to_the_freshness_claim(self):
        c = candidate({"workflow": 10, "wedge": 10, "demand": 10, "team": 5, "defensibility": 5, "execution": 5})
        self.assertEqual(c.evidence, [Evidence("Launched.", "https://example.com/source")])


if __name__ == "__main__":
    unittest.main()
