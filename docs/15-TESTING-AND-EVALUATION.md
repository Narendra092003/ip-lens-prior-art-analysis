# 15 — Testing and Evaluation

## Minimum required evaluation (5-day plan)

| Measure | Data | Output |
|---|---|---|
| Recall@1 and Recall@4 | 10–15 hand-labeled query claims in `examples/eval/retrieval_labels.json` | Table in `docs/EVALUATION.md` with settings used |
| Threshold effect | Same set | Relevant vs irrelevant passages kept at `MIN_SIMILARITY` |
| Prompt v1 vs v2 | 6–8 cases in `examples/eval/compare_cases.json` | Schema-valid rate, discarded citations, reviewer note per case |
| Timing | 5 runs of the demo disclosure | Median and maximum end-to-end time, slowest step |

Label the retrieval set *before* tuning settings, then keep it fixed. Write the numbers exactly as the scripts print them, including weak results; explaining a weak Recall@4 and what you would change is a strong interview answer.

## Keep tests and evaluations distinct

Automated tests check deterministic behavior and contracts. Evaluations inspect retrieval and language-model quality against labeled examples. A passing test suite does not prove that novelty assessments are legally correct.

## Focused test layers

| Layer | Examples | External services? |
|---|---|---|
| Unit | Text extraction, page markers, chunk boundaries, ID generation, score bands, citation validation | No |
| Service | Chroma indexing/replacement/count/search, threshold filtering | Local Chroma only |
| API | Upload limits, invalid requests, health response, error mapping, report shape | Fake Gemini or mocks |
| Workflow | Claim-by-claim routing, no-evidence branch, model failure, citation rejection | Fake Gemini by default |
| UI smoke | Upload screen, disclosure review, results and export paths | Local API; fictional files |

## Retrieval evaluation

Create a hand-labeled synthetic corpus where each query claim is linked to expected relevant chunk IDs. Report:

- **Recall@k:** expected relevant chunks retrieved within the first `k` results.
- **Citation validity:** citations in returned reports that resolve to a chunk supplied for that same claim.
- **Threshold effects:** relevant and irrelevant passage counts retained at the configured `MIN_SIMILARITY`.

Keep the dataset and script small and reviewable. Record the dataset version, `top_k`, threshold, and actual results. Do not fabricate a benchmark in the README or interview.

## Claim-comparison review

Evaluate Gemini outputs separately with a human-reviewed set of claim/evidence examples. Review whether shared and missing elements are supported by the cited passage, whether the model expresses uncertainty, and whether unsupported statements appear. Do not describe citation support quality or claim-element accuracy as measured until that review has been performed and documented.

## Prompt comparisons

Version each prompt. When comparing prompt versions, use the same synthetic examples and report the schema-valid rate, invalid/unknown citation count, and reviewer findings side by side. Never compare results from different corpora without labeling the change.

