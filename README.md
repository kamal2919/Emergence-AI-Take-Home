# SignalDesk

SignalDesk is a deliberately small, evidence-first pipeline for triaging seed-stage
AI workflow companies. It turns a researched candidate set into consistent,
decision-ready investment memos.

## Thesis

We invest in seed-stage, vertical AI workflow products that replace a measurable,
high-frequency operational job for an SMB or mid-market team. A strong candidate
has a narrow initial workflow, an implementation path that does not require a
large services team, and at least one observable adoption, launch, or technical
signal. We do **not** reward a generic "agent platform" merely for using AI.

The thesis and rubric live in [docs/thesis.md](docs/thesis.md). It is intentionally
narrow: it makes a score useful and makes a pass meaningful.

## Quick start

No package installation or API key is required for the replayable research snapshot.

```bash
python3 -m signaldesk run --input data/yc_ai_workflows.json --output outputs
```

The command validates inputs, calculates a deterministic thesis score, and writes
one Markdown memo per company plus an index. Generated outputs are committed so a
reviewer does not need to rerun the pipeline.

### Run the LLM synthesis stage

The default run is deterministic. To add evidence-grounded LLM synthesis, set a
key in your shell (never in the repository) and pass `--llm`:

```bash
export SIGNALDESK_LLM_API_KEY='your-key-here'
python3 -m signaldesk run --input data/yc_ai_workflows.json --output outputs-llm --llm
```

The adapter uses an OpenAI-compatible chat-completions endpoint by default. Any
compatible provider can be used without a code change:

```bash
python3 -m signaldesk run --input data/yc_ai_workflows.json --output outputs-llm --llm \
  --llm-endpoint 'https://provider.example/v1/chat/completions' --llm-model 'provider-model'
```

The model is constrained to the supplied candidate evidence, returns strict JSON
Schema output,
and cannot change the deterministic thesis score. Successful LLM runs write
`llm-provenance.json` alongside the memos, recording the model, endpoint, source
URLs, and structured synthesis without recording any secret.

### Refresh public-source evidence

The included source set uses a bounded list of public YC company pages. Refresh a
dated metadata snapshot before a final submission run:

```bash
python3 -m signaldesk source-yc \
  --seed data/yc_company_urls.json \
  --output data/raw/yc-page-snapshot.json
```

The adapter captures only public page title, description, retrieval time, and a
content hash. It never asks an LLM to browse or infer a missing fact.

If your local Python installation has a certificate-store issue, set
`SIGNALDESK_CA_BUNDLE` to a trusted local CA bundle; this preserves TLS
verification rather than bypassing it.

### Preflight before an LLM run

Use a dry run to confirm the candidate count, endpoint, model, and API-key
environment-variable name. It makes no model call, does not read the key's value,
and writes no files:

```bash
python3 -m signaldesk run --input data/yc_ai_workflows.json --output outputs-llm \
  --llm --dry-run
```

```bash
python3 -m unittest discover -s tests -v
```

## Design choices

- **One source, deeply:** the included snapshot is limited to YC company pages.
  Each claim in a memo retains a URL back to the raw research record.
- **Evidence before prose:** the pipeline refuses missing name, website,
  description, source URL, or freshness signal. Unknown founder details are shown
  as unknown rather than invented.
- **Deterministic first pass:** score calculation is code, not model intuition.
  This keeps recommendations reproducible and lets an investment partner challenge
  the rubric instead of reverse-engineering a prompt.
- **Grounded LLM synthesis:** the optional model stage receives only the supplied
  evidence, returns schema-validated JSON, and may not change a score. Human
  review is required for externally material claims.

## Project layout

```text
data/          public-source research snapshot and provenance
docs/          investment thesis, architecture, and honest AI-workflow trail
signaldesk/    sourcing validation, analysis/scoring, and memo rendering
outputs/       committed, reviewable memos
data/raw/      dated public-source snapshots created by source adapters
tests/         unit tests for scoring and input validation
```

## Five-minute walkthrough

1. State the thesis and why a broad AI thesis would not be investable.
2. Run the command above against the YC research snapshot.
3. Open `outputs/leaping-ai.md`: show raw evidence, scoring breakdown, and the
   recommendation.
4. Change a score input in a scratch copy to show that the recommendation is
   driven by an inspectable rubric, not opaque model prose.
5. Show `docs/ai-workflow.md` and `docs/architecture.md`: what AI helped with,
   what was verified, and the intentional scope cuts.

Use [docs/walkthrough-script.md](docs/walkthrough-script.md) for a timed demo and
[docs/submission-checklist.md](docs/submission-checklist.md) before sharing.
