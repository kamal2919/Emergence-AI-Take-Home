# Research snapshot

`yc_ai_workflows.json` is a manually bounded, dated snapshot of public YC company
pages collected for the take-home. It is intentionally not represented as a live
YC API. The `source_url` on every record is the provenance link used by the memo
renderer; descriptions are concise paraphrases of those public pages.

Each candidate includes multiple claim-level `evidence` records tied to the same
public source page, plus a dated raw snapshot in `data/raw/yc-page-snapshot.json`.

The snapshot is a starting point for triage, not a claim of comprehensive market
coverage. Founder fields are populated from the public YC page metadata where
available.
