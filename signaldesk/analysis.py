from dataclasses import dataclass
from .models import Candidate
from .llm import Enrichment

MAXIMA = {"workflow": 25, "wedge": 20, "demand": 20, "team": 15, "defensibility": 10, "execution": 10}


@dataclass(frozen=True)
class Analysis:
    candidate: Candidate
    total: int
    recommendation: str
    enrichment: Enrichment | None = None


def analyze(candidate: Candidate, enrichment: Enrichment | None = None) -> Analysis:
    for dimension, maximum in MAXIMA.items():
        score = candidate.scores[dimension]
        if not isinstance(score, int) or not 0 <= score <= maximum:
            raise ValueError(f"{candidate.name}: {dimension} must be an integer from 0 to {maximum}")
    total = sum(candidate.scores.values())
    recommendation = "Take a meeting" if total >= 75 else "Watch" if total >= 55 else "Pass"
    return Analysis(candidate=candidate, total=total, recommendation=recommendation, enrichment=enrichment)
