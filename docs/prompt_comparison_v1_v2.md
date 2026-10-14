# Prompt comparison: v1 and v2

- Date: 2026-10-14
- Gemini model: `gemini-3.5-flash-lite`
- Corpus passages at run time: 4643
- MIN_SIMILARITY: 50
- top_k: 4
- Chunk size / overlap: 1200 / 180
- Attempts: 3 per case and prompt version
- Pause between Gemini calls: 4 seconds
- Retrieval is performed once per case; both prompts and all runs use the same useful passages.
- Coverage is shown only for evidence findings; other statuses are shown as not assessed.

### v1

- Schema-valid rate: 21/21 (100.0%)
- Total discarded citations: 0
- Status agreement (all 3 runs agree): 6/7 cases
- Coverage spread (cases with coverage: 6): mean 7.5, maximum 25
- Claim-reference elements: 7 across all runs

### v2

- Schema-valid rate: 21/21 (100.0%)
- Total discarded citations: 0
- Status agreement (all 3 runs agree): 6/7 cases
- Coverage spread (cases with coverage: 6): mean 2.0, maximum 12
- Claim-reference elements: 0 across all runs

#### Demo cases

| Case ID | Source | v1 run 1 | v1 run 2 | v1 run 3 | v2 run 1 | v2 run 2 | v2 run 3 |
|---|---|---|---|---|---|---|---|
| fictional-demo-claim-01 | demo | evidence / 65 | evidence / 80 | evidence / 80 | evidence / 79 | evidence / 79 | evidence / 79 |
| fictional-demo-claim-02 | demo | evidence / 35 | evidence / 50 | evidence / 25 | evidence / 44 | evidence / 50 | evidence / 38 |
| fictional-demo-claim-03 | demo | evidence / 25 | evidence / 20 | no_supporting_passage / — | evidence / 19 | no_supporting_passage / — | evidence / 19 |
| fictional-demo-claim-04 | demo | no_supporting_passage / — | no_supporting_passage / — | no_supporting_passage / — | no_supporting_passage / — | no_supporting_passage / — | no_supporting_passage / — |

#### Held Out cases

| Case ID | Source | v1 run 1 | v1 run 2 | v1 run 3 | v2 run 1 | v2 run 2 | v2 run 3 |
|---|---|---|---|---|---|---|---|
| q01 | held_out | evidence / 100 | evidence / 100 | evidence / 100 | evidence / 100 | evidence / 100 | evidence / 100 |
| q03 | held_out | evidence / 100 | evidence / 100 | evidence / 100 | evidence / 100 | evidence / 100 | evidence / 100 |
| q09 | held_out | evidence / 100 | evidence / 100 | evidence / 100 | evidence / 100 | evidence / 100 | evidence / 100 |
