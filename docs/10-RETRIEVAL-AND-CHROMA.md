# 10 — Retrieval and ChromaDB

## Purpose and storage

Retrieval finds passages in the local uploaded corpus that may relate to each reviewed claim. It narrows what a reviewer should inspect; it does not determine legal prior-art status, novelty, or patentability.

- ChromaDB uses a persistent local client, one cosine-distance collection, and its local default embedding function.
- Data is under the project-root `data/` directory and excluded from Git.
- The vector-store service is the only module that imports ChromaDB.
- Raw cosine distance is retained in internal search results.

## Search behavior

Search each reviewed claim separately. `top_k` defaults to 4 and accepts 1–10. Convert cosine distance `d` using:

```text
similarity = clamp(round((1 - d) * 100), 0, 100)
```

Only passages at or above `MIN_SIMILARITY` are useful; its default is **50**. Retrieval requests use `top_k` (default `DEFAULT_TOP_K=4`, maximum 10) before applying the threshold. These configurable values are retrieval controls, not calibrated probabilities. Threshold 50 was selected as the lowest tested value where both evaluation no-answer claims returned no passages; see [`EVALUATION.md`](./EVALUATION.md).

`ClaimRetrieval` keeps useful passages and the number dropped below threshold. Results carry chunk/document IDs, filename, title, page, excerpt, similarity, and raw distance. Re-indexing a document replaces its old chunks.

## Evaluation

The current labeled retrieval evaluation uses `top_k=10` without threshold filtering to calculate Recall@1 and Recall@4. It also reports a 30–60 threshold sweep. Recall, threshold counts, dataset, chunk size, and overlap are in [`EVALUATION.md`](./EVALUATION.md). Similarity is not a calibrated measure of relevance.
