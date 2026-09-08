import re
from .analysis import Analysis


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _changes_mind(analysis: Analysis) -> list[str]:
    c = analysis.candidate
    if analysis.recommendation == "Take a meeting":
        return [
            "A reference customer cannot quantify the time or cost saved.",
            "Deployment requires a bespoke services engagement rather than a repeatable integration.",
            "Reliability or regulatory controls fail the buyer's production requirements.",
        ]
    if analysis.recommendation == "Watch":
        return [
            "A repeatable customer deployment with a measurable outcome is demonstrated.",
            "A clear buyer and durable distribution or integration advantage emerges.",
            "The team shows it can manage the principal reliability or compliance risk.",
        ]
    return [
        "The company identifies a high-frequency workflow with a named economic buyer.",
        "A credible adoption signal or customer reference appears.",
        "The product develops a wedge beyond a broad, interchangeable agent claim.",
    ]


def render_memo(analysis: Analysis) -> str:
    c = analysis.candidate
    dimensions = [
        ("workflow", "workflow pain & buyer clarity", 25),
        ("wedge", "wedge & implementation", 20),
        ("demand", "evidence of demand", 20),
        ("team", "team", 15),
        ("defensibility", "defensibility", 10),
        ("execution", "execution / risk", 10),
    ]
    score_rows = "\n".join(
        f"| {label.title()} | {c.scores[key]}/{maximum} |"
        for key, label, maximum in dimensions
    )
    enriched = analysis.enrichment
    risks = "\n".join(
        f"- {risk}" for risk in (enriched.risks if enriched else c.risk_notes)
    )
    changes = "\n".join(f"- {item}" for item in _changes_mind(analysis))
    team = (
        enriched.team_summary
        if enriched
        else (
            c.founder_signal
            or "Not captured in this research pass; validate before relying on team quality."
        )
    )
    product = enriched.product_summary if enriched else c.description
    market = enriched.market_summary if enriched else c.market_note
    questions = (
        "\n".join(f"- {item}" for item in enriched.open_questions)
        if enriched
        else "- Validate the source-backed claims with customer references and product diligence."
    )
    llm_note = (
        f"Synthesized with `{enriched.model}` through `{enriched.provider}`; "
        "deterministic scoring remained unchanged."
        if enriched
        else "Not run for this replay; the memo uses the deterministic research snapshot."
    )
    return f'''# {c.name} — {analysis.recommendation}

**Thesis score: {analysis.total}/100**  
**Website:** [{c.website}]({c.website})  
**Evidence:** [YC company page]({c.source_url})

## The call

**{analysis.recommendation}.** {product} The current call reflects the
specificity of the workflow, available public evidence, and the risks below—not a
claim that the available evidence is complete.

## What it does

{product}

## Team

{team}

## Market and why now

{market}

## Evidence observed

{_render_evidence(c.evidence)}

## AI synthesis

{llm_note}

## Scorecard

| Dimension | Score |
| --- | ---: |
{score_rows}
| **Total** | **{analysis.total}/100** |

## Risks / open questions

{risks}

### Questions to validate

{questions}

## What would change my mind

{changes}
'''


def _render_evidence(evidence: list) -> str:
    return "\n".join(
        f"- {item.claim} ([source]({item.source_url}))"
        for item in evidence
    )
