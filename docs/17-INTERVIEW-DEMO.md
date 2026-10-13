# 17 — Interview Demo

## One-minute project description

> IP Lens is a local, evidence-linked prior-art analysis prototype. A user uploads patent documents, reviews claims extracted from a technology disclosure, and gets claim-by-claim comparisons against passages retrieved from that uploaded corpus. LangGraph coordinates the workflow; FastAPI exposes it; ChromaDB stores local embeddings; Gemini structures and compares text; Streamlit presents the evidence. The score is a transparent triage heuristic, not a legal patentability decision.

## Demo flow

1. Show the application title and the data-handling notice.
2. Upload two synthetic prior-art examples and two real published patents from `examples/REAL_PATENTS.md`; point out per-file ingestion status and corpus count.
3. Enter the synthetic disclosure and show proposed claims.
4. Edit or confirm the claims to demonstrate analyst control.
5. Start analysis and follow one claim from retrieved passage to comparison and validated citation.
6. Open the original excerpt and note the filename/page.
7. Show a claim with no useful evidence or explain the `Not scored` behavior if the full corpus has no valid citations.
8. Explain the 65/35 triage formula and download JSON/Markdown.
9. Show `docs/EVALUATION.md`: the real Recall@k, the prompt v1-vs-v2 table, and the measured timings.

## What to emphasize

- Source provenance is retained from extraction through the report.
- The user, not the model, approves claims before analysis.
- No-evidence results are explicit; the system does not treat missing evidence as low risk.
- The score is deterministic once claim coverage and cited retrieval similarity exist.
- The search scope is limited to documents in the local uploaded corpus.
- Prompt outputs are validated and citations are checked in application code.
- The model SDK is isolated in one module, so confidential use could switch to an approved in-company model.

## Questions to prepare for

**Why multiple agents?** The disclosure-structuring and claim-comparison roles solve different language tasks and return different typed outputs. Retrieval and scoring remain ordinary code.

**How do you know it works?** Show the retrieval evaluation method and actual collected results. Explain that model comparison quality needs a separate human-reviewed evaluation.

**Does it determine novelty?** No. It is an early research aid over a limited corpus, not a legal analysis or patentability decision.

**Did you write it yourself?** Answer honestly: you wrote the specification and design decisions, built it phase by phase with an AI coding assistant, reviewed and tested every phase, and can explain each file. The Git history shows one commit per phase.

**Could this be used with real invention disclosures?** Not as built: the MVP sends text to the public Gemini API. For confidential disclosures, the model call would move to approved infrastructure inside the company, which only requires replacing the provider module.

**How fast is it?** Quote only the measured median and maximum from `docs/EVALUATION.md`, and name the slowest step.

**What would you build next?** Improve the labeled corpus, measure retrieval recall and comparison support, and only then consider a public patent source or OCR as a separately scoped feature.

## Claims you can make once the evidence exists

| Statement | Only when |
|---|---|
| "Built a multi-agent workflow" | The end-to-end demo runs |
| "Benchmarked prompt pipelines" | The v1-vs-v2 table is in `docs/EVALUATION.md` |
| "Recall@4 of X on a labeled synthetic set" | The script printed X |
| "Tested on real patent documents" | The real-patent demo set was ingested and analysed |
| "Analysis takes about N seconds" | N is the measured median |

## Claims not to make

Do not claim production readiness, search against patent-office repositories, exhaustive prior-art coverage, legal accuracy, a measured benchmark that has not been collected, or that vector similarity itself proves claim overlap.

