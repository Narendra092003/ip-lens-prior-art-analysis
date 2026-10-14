# 15 — Testing and Evaluation

## Automated tests and evaluations

Automated tests verify deterministic contracts and code paths. Evaluations inspect retrieval and model behavior against labeled or reviewer-inspected examples. Passing tests do not demonstrate legal correctness or claim-element accuracy.

| Layer | Examples | External services? |
|---|---|---|
| Unit | Extraction, page markers, chunk boundaries, IDs, prompt metric calculations, score bands, citation validation | No Gemini calls |
| Service | Chroma indexing/replacement/count/search, threshold filtering | Local Chroma only |
| API | Upload limits, invalid requests, health response, error mapping, report shape | Fake Gemini or mocks |
| Workflow | Claim routing, four finding statuses, model failures, citation rejection | Fake Gemini by default |
| UI | Corpus upload, disclosure review, results and export paths | Local API and fictional files |

## Retrieval evaluation

`scripts/evaluate_retrieval.py` reads `examples/eval/retrieval_labels.json`, retrieves `top_k=10` without threshold filtering, and reports chunk-level and document-level Recall@1/4 plus the similarity threshold sweep. The current 15-claim evaluation has 13 labeled relevant claims and two no-answer claims. Collected settings and figures are in [`EVALUATION.md`](./EVALUATION.md); the threshold default is 50. Similarity is not a calibrated probability.

## Prompt comparison

`scripts/compare_prompts.py` reads seven cases: four demo cases used in v2 development and three held-out retrieval-label claims. It retrieves once per case, runs v1 and v2 three times each on the same passages, and reports schema validity, discarded citations, status agreement, coverage spread, and claim-reference elements. The collected run and source-checked reviewer notes are in [`EVALUATION.md`](./EVALUATION.md) and `../outputs/prompt_comparison.md`.

This comparison measures consistency and schema validity, not correctness. The held-out cases were easy, single-feature matches, and the sample is small. Aggregate timing across five complete demo analyses has not yet been collected; do not make an end-to-end performance claim until it is.

## Interpretation

Keep retrieval metrics separate from model-comparison judgments. Describe only what the collected results establish, identify the corpus, model, settings, and small sample, and do not claim generalization or legal accuracy.
