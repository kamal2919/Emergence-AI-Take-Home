import unittest
import json
import os
import tempfile
from dataclasses import replace
from unittest.mock import Mock
from pathlib import Path
from signaldesk.analysis import analyze
from signaldesk.cli import _build_parser, _enrich_all, _load_checkpoint, _write_checkpoint
from signaldesk.llm import LLMConfig
from signaldesk.llm import Enrichment, LLMError
from signaldesk.models import Candidate, Evidence
from signaldesk.sources.yc import collect_snapshot


def candidate(scores):
    return Candidate.from_dict({"name": "Test Co", "website": "https://example.com", "description": "A workflow tool.", "freshness_signal": "Launched.", "source_url": "https://example.com/source", "scores": scores})


class AnalysisTests(unittest.TestCase):
    def test_default_llm_configuration_targets_gemini(self):
        previous_endpoint = os.environ.pop("SIGNALDESK_LLM_ENDPOINT", None)
        previous_model = os.environ.pop("SIGNALDESK_LLM_MODEL", None)
        try:
            args = _build_parser().parse_args([
                "run", "--input", "data/input.json", "--output", "outputs", "--llm"
            ])
        finally:
            if previous_endpoint is not None:
                os.environ["SIGNALDESK_LLM_ENDPOINT"] = previous_endpoint
            if previous_model is not None:
                os.environ["SIGNALDESK_LLM_MODEL"] = previous_model
        self.assertEqual(
            args.llm_endpoint,
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        )
        self.assertEqual(args.llm_model, "gemini-3.6-flash")
        self.assertEqual(args.llm_workers, 1)

    def test_llm_checkpoint_reuses_valid_grounded_synthesis(self):
        c = candidate({"workflow": 10, "wedge": 10, "demand": 10, "team": 5, "defensibility": 5, "execution": 5})
        enrichment = Enrichment.from_response({
            "team_summary": "Not established in supplied evidence.", "product_summary": "A workflow tool.", "market_summary": "A market.",
            "risks": ["A risk."], "open_questions": ["A question."], "source_urls": [c.source_url],
        }, c, "https://provider.example/chat/completions", "test-model")
        config = LLMConfig("https://provider.example/chat/completions", "test-model")
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "llm-checkpoint.json"
            _write_checkpoint(checkpoint, [c], {c.source_url: enrichment})
            restored = _load_checkpoint(checkpoint, [c], config)
        self.assertEqual(restored[c.source_url], enrichment)

    def test_llm_batch_checkpoints_successes_before_reporting_failures(self):
        first = candidate({"workflow": 10, "wedge": 10, "demand": 10, "team": 5, "defensibility": 5, "execution": 5})
        second = replace(
            first,
            name="Second Co",
            source_url="https://example.com/second",
            evidence=[Evidence("Launched.", "https://example.com/second")],
        )
        enrichment = Enrichment.from_response({
            "team_summary": "Not established in supplied evidence.", "product_summary": "A workflow tool.", "market_summary": "A market.",
            "risks": ["A risk."], "open_questions": ["A question."], "source_urls": [first.source_url],
        }, first, "https://provider.example/chat/completions", "test-model")
        client = Mock()
        client.config = LLMConfig("https://provider.example/chat/completions", "test-model")
        client.enrich.side_effect = [enrichment, RuntimeError("rate limited")]
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                _enrich_all([first, second], client, Path(directory), workers=1)
            checkpoint = json.loads((Path(directory) / "llm-checkpoint.json").read_text())
        self.assertEqual(len(checkpoint["entries"]), 1)

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
