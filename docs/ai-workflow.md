# AI-assisted working trail

This is a contemporaneous summary of the work used to build this submission, not
a reconstructed prompt diary.

## Where AI helped

- I used an AI coding assistant to decompose the take-home prompt, compare a few
  possible scopes, and draft the initial Python project structure.
- I asked it to challenge an overbuilt design. That led to three explicit cuts:
  no job queue, no vector database, and no React UI.
- I used it to propose unit-test cases for missing evidence and recommendation
  boundaries. I reviewed the final scoring behavior and wrote the thesis/rubric
  decisions myself.
- I used AI to help turn structured facts into memo language. The repository keeps
  source URLs and deterministic scores so prose is not treated as evidence.

## Checks I applied

1. Every checked-in candidate has a source page and a dated research snapshot.
2. The output labels missing founder information as unknown.
3. The score is deterministic and tested; recommendation bands are test-covered.
4. Each memo includes a reason the current conclusion could change.
5. The optional LLM stage is source-bounded, schema-validated, and records model
   provenance. It can improve synthesis but cannot invent a score or source.

## What I would do next

For a second iteration, I would add a source adapter for one public feed and run
the LLM synthesis stage with human review of every memo. A small hand-labelled
memo-quality fixture now lives in `tests/fixtures/memo_quality_labels.json` with
coverage for claim support, recommendation consistency, and skimmable memo length.
