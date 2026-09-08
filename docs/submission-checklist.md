# Submission checklist

## Before recording the video

- [ ] Review every candidate claim against its linked YC source.
- [ ] Run the unit tests: `python3 -m unittest discover -s tests -v`.
- [ ] Refresh `data/raw/yc-page-snapshot.json` if the source data is stale.
- [ ] Run the deterministic pipeline and check `outputs/evaluation.json`.
- [ ] Configure an API key locally and run the LLM synthesis into `outputs-llm/`.
- [ ] Read all model-synthesized text; correct or remove any unsupported wording.
- [ ] Ensure `.env` is not tracked by Git.

## Before sharing the repository

- [ ] Commit the raw source snapshot, deterministic outputs, evaluation report,
  and (after review) the LLM outputs/provenance report.
- [ ] Add a concise commit history that reflects the actual working process.
- [ ] Create the private GitHub repository and add `chiragmakkar` and
  `hari@emsoft.com` as collaborators, as requested in the assignment.
- [ ] Confirm a clean clone can run the deterministic pipeline without a key.
- [ ] Record the five-minute walkthrough using `docs/walkthrough-script.md`.

## Do not do

- [ ] Do not commit an API key, `.env`, or raw credential-bearing command output.
- [ ] Do not claim an LLM researched or verified facts it did not receive.
- [ ] Do not expand scope with a dashboard, worker queue, or vector database.
