# Architecture

```text
allow-listed public company pages
        |
        v
dated raw snapshot  ---> research record with claim-level evidence
                                      |
                                      v
                             normalized candidates
                                                        |
                                          optional, schema-validated LLM synthesis
                                                        |
                                                        v
                                             deterministic thesis scoring
                                                        |
                                                        v
                                           Markdown memos + index.md
```

The three boundaries are deliberately plain:

1. **Sourcing** accepts a bounded research snapshot. A production adapter can
   fetch an allowed public feed and save a dated snapshot before analysis.
2. **Analysis** preserves raw evidence, assigns an inspectable score, and creates
   explicit open questions. The optional LLM summarizes only the supplied
   evidence, must cite an allowed URL, and has its structured response preserved
   in `llm-provenance.json`; it cannot alter the score.
3. **Recommendation** renders a short memo from the analysis. It contains the
   call, reasons, risks, and what would change the call.

This avoids a queue, vector database, frontend, and autonomous browser agent:
none changes the partner's ability to judge a startup in the first version.
