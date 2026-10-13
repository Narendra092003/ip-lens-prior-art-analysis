# 10 — Retrieval and ChromaDB

## Purpose

Find passages in the user's local uploaded corpus that may relate to each reviewed claim. Retrieval narrows what the analyst should inspect; it does not determine whether a document is legally prior art or whether a claim is novel.

## Storage design

- Use ChromaDB's persistent local client and one clearly named collection for patent-document chunks.
- Keep the database under the project `data/` directory and ignore that directory in Git.
- Store chunk text and the metadata defined in [`09-DOCUMENT-INGESTION-SERVICE.md`](./09-DOCUMENT-INGESTION-SERVICE.md).
- Use ChromaDB's local embedding function. Do not send corpus text to a separate embedding API.
- Preserve a raw cosine distance internally for debugging and evaluation.

## Search behavior

Run a separate semantic query for every reviewed claim. Default `top_k` is 4; accept values from 1 to 10. Convert Chroma's cosine distance `d` to the displayed retrieval-similarity value using:

```text
similarity = clamp(round((1 - d) * 100), 0, 100)
```

Only pass a passage to claim comparison when its converted value meets `MIN_SIMILARITY` (default 35 on a 0–100 scale). This is an adjustable retrieval filter, not a calibrated probability. It should be measured on a labeled synthetic corpus before making retrieval-quality claims.

## Result contract

Each search result includes the chunk ID, source document ID, filename, display title, page number, excerpt, raw distance, and converted retrieval similarity. The UI labels the percentage **retrieval similarity** and shows it beside the excerpt. It never labels it a likelihood of infringement, novelty, or relevance.

## Lifecycle operations

The service provides indexing, deletion/replacement by document identity, corpus counts, and search. Re-indexing a file removes its old chunk IDs before storing the new set. The vector-store layer is the only code that directly talks to ChromaDB; routes and Streamlit use service methods.

## Evaluation measures

Use a hand-labeled synthetic dataset with a query claim and expected relevant chunk IDs. Calculate Recall@k and inspect missed relevant passages. Tune `MIN_SIMILARITY` and chunk defaults using that dataset, record the settings, and keep the set small enough to review manually. Do not present retrieval similarity as a calibrated score.

