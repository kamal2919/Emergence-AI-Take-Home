# Five-minute walkthrough script

## 0:00–0:35 — Frame the decision

"I built SignalDesk to triage seed-stage AI workflow companies. The thesis is
narrow: recurring operational work, a named buyer, a repeatable implementation
path, and observable evidence of demand. I intentionally did not build a UI,
queue, or vector database because they do not improve the first investment
decision."

Open `docs/thesis.md` and show the six scoring dimensions.

## 0:35–1:20 — Show sourcing and provenance

Run:

```bash
SIGNALDESK_CA_BUNDLE=/etc/ssl/cert.pem python3 -m signaldesk source-yc \
  --seed data/yc_company_urls.json \
  --output data/raw/yc-page-snapshot.json
```

Open `data/raw/yc-page-snapshot.json`. Explain that the source layer is bounded
to 12 YC company pages and stores public title, description, retrieval time, and
a content hash before analysis.

## 1:20–2:05 — Show the pipeline run

Run the deterministic version first:

```bash
python3 -m signaldesk run --input data/yc_ai_workflows.json --output outputs
```

Open `outputs/index.md` and `outputs/evaluation.json`. Explain that scores are
code-driven and that the output gate rejects an invalid recommendation, score, or
missing claim-level evidence.

## 2:05–3:20 — Walk through one startup

Open `outputs/leaping-ai.md`.

Point out, in order: the recommendation, source link, claim-level evidence,
scorecard, risks, and what would change the decision. Say explicitly: "A high
score earns a diligence conversation, not an investment decision."

## 3:20–4:20 — Show the LLM role and controls

Run the preflight:

```bash
python3 -m signaldesk run --input data/yc_ai_workflows.json \
  --output outputs-llm --llm --dry-run
```

Show `signaldesk/llm.py`. Explain that the LLM sees only supplied evidence,
returns strict JSON Schema, must cite an allowed source, and cannot change the
deterministic score. After an actual configured run, show
`outputs-llm/llm-provenance.json`.

## 4:20–5:00 — Show honest AI workflow and close

Open `docs/ai-workflow.md` and `docs/architecture.md`. Explain what AI helped
with, what was verified, and why the system deliberately stops at a usable v1.

Close with: "The next iteration would add a second source and a small
hand-labelled memo-quality evaluation set only after validating that a partner
finds the existing output useful."
