from dataclasses import dataclass
from typing import Any, Mapping


REQUIRED_FIELDS = {
    "name",
    "website",
    "description",
    "freshness_signal",
    "source_url",
    "scores",
}
SCORE_FIELDS = {
    "workflow",
    "wedge",
    "demand",
    "team",
    "defensibility",
    "execution",
}


@dataclass(frozen=True)
class Evidence:
    """A single claim paired with the public URL from which it came."""

    claim: str
    source_url: str
    retrieved_at: str | None = None

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Evidence":
        if not value.get("claim") or not value.get("source_url"):
            raise ValueError("Evidence records require a non-empty claim and source_url.")
        return cls(
            claim=value["claim"],
            source_url=value["source_url"],
            retrieved_at=value.get("retrieved_at"),
        )


@dataclass(frozen=True)
class Candidate:
    name: str
    website: str
    description: str
    freshness_signal: str
    source_url: str
    founder_signal: str | None
    market_note: str
    risk_notes: list[str]
    scores: dict[str, int]
    evidence: list[Evidence]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Candidate":
        missing = REQUIRED_FIELDS - value.keys()
        if missing:
            raise ValueError(f"{value.get('name', 'candidate')}: missing fields {sorted(missing)}")
        if missing_scores := SCORE_FIELDS - value["scores"].keys():
            raise ValueError(f"{value['name']}: missing score fields {sorted(missing_scores)}")
        evidence_fields = (
            "name",
            "website",
            "description",
            "freshness_signal",
            "source_url",
        )
        if not all(value[key] for key in evidence_fields):
            raise ValueError(f"{value.get('name', 'candidate')}: required evidence is blank")
        evidence = [Evidence.from_dict(item) for item in value.get("evidence", [])]
        if not evidence:
            evidence = [
                Evidence(
                    claim=value["freshness_signal"],
                    source_url=value["source_url"],
                )
            ]
        return cls(
            name=value["name"],
            website=value["website"],
            description=value["description"],
            freshness_signal=value["freshness_signal"],
            source_url=value["source_url"],
            founder_signal=value.get("founder_signal"),
            market_note=value.get("market_note", "Market detail needs validation."),
            risk_notes=value.get("risk_notes", ["Validate with a customer reference."]),
            scores=value["scores"],
            evidence=evidence,
        )
