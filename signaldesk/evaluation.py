"""Deterministic quality checks for generated investment memos."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .analysis import Analysis


@dataclass(frozen=True)
class EvaluationResult:
    company: str
    passed: bool
    issues: list[str]


def evaluate(analysis: Analysis) -> EvaluationResult:
    candidate = analysis.candidate
    issues: list[str] = []

    if not candidate.evidence:
        issues.append("No claim-level evidence was captured.")
    if any(not item.claim or not item.source_url for item in candidate.evidence):
        issues.append("An evidence record is incomplete.")
    if analysis.recommendation not in {"Pass", "Watch", "Take a meeting"}:
        issues.append("Recommendation is not one of the allowed calls.")
    if not 0 <= analysis.total <= 100:
        issues.append("Thesis score is outside the 0-100 range.")
    if analysis.enrichment:
        allowed = {item.source_url for item in candidate.evidence} | {candidate.website}
        if not set(analysis.enrichment.source_urls).issubset(allowed):
            issues.append("LLM enrichment cited a source outside the evidence records.")

    return EvaluationResult(
        company=candidate.name,
        passed=not issues,
        issues=issues,
    )


def evaluate_all(analyses: list[Analysis]) -> list[dict]:
    return [asdict(evaluate(analysis)) for analysis in analyses]
