## Ingestion

- Corpus: 50 published patents, 1,603 pages. 48 indexed; 2 rejected because they are German-language publications.
- Drawing sheets (sheet markers or figure labels with fewer than 40 words) are skipped. This reduced the index from 4,803 to 4,611 chunks and removes figure-label noise; a few figure pages with useful labels are skipped as well.
- Bulk ingestion time: about 2.2 minutes on a laptop.

## Retrieval and threshold

**Setup.** Corpus of 4,643 passages: 48 real published patents plus 5 synthetic agricultural documents. Chunk size 1,200, overlap 180, `top_k` 10 during evaluation. 15 hand-labelled claims (`examples/eval/retrieval_labels.json`): 13 with a labelled relevant passage, 2 with no relevant document (q14, q15). A chunk counts as relevant only if it comes from the labelled file and contains the labelled phrase.

**Results (chunk level).** Recall@1: 1/13 (7.7%). Recall@4: 10/13 (76.9%).
Recall@1 is low partly because other chunks of the correct document, which don't contain the exact labelled phrase, often rank first. Document-level results: Recall@1: 12/13 (92.3%). Recall@4: 13/13 (100.0%). The highest non-relevant chunk came from the same labelled file for 11 of 13 claims.

**Threshold sweep** (similarity = clamp(round((1 − cosine distance) × 100), 0, 100)):

| Threshold | Relevant chunks kept (top 10) | Non-relevant chunks kept (top 4) | No-answer claims returning a passage |
|---|---|---|---|
| 30 | 17 | 44 | 2/2 |
| 35 | 17 | 40 | 1/2 |
| 40 | 15 | 40 | 1/2 |
| 45 | 14 | 40 | 1/2 |
| 50 | 13 | 32 | 0/2 |
| 55 | 9 | 25 | 0/2 |
| 60 | 8 | 20 | 0/2 |

**Decision.** The original default of 35 let unrelated patents through (for example, an animation-processing patent scored 40 for a tractor-transmission claim), so the system would almost never report "no evidence". `MIN_SIMILARITY` is now **50**: the lowest tested threshold at which both no-answer claims return no passages.

**Trade-off.** At 50, 4 of 17 relevant chunks are dropped, including the best match for q10, the most heavily paraphrased claim (similarity 49). Missing relevant prior art is the more serious error in IP work, so the threshold was not raised further. With only 15 labelled claims, this is an indicative calibration, not a validated setting.

The synthetic agricultural documents differ strongly in topic from the real patents in the corpus (electronics, medical, robotics, energy), which makes document-level retrieval easier than it would be in a corpus of closely related agricultural patents.

## Prompt v1 observations (claim comparison)

Observed on a real run of `claim_compare_v1` against the demo disclosure:

- Lists the claim's reference "The system of claim 1" as a shared element; it is not a technical feature.
- Presents equivalences as plain matches, e.g. "an implement controller (or hitch controller)", without marking them as inferred rather than explicitly stated.
- A partially covered feature ("within a selected operating band" vs the prior art's "within a selected range") is listed as fully missing instead of partially covered.
- Disclosure extraction is not deterministic: two extractions of the same disclosure produced differently ordered and worded claims.

These observations define the changes for `claim_compare_v2`.

## Prompt v2 observations (claim comparison)

**What v2 changes.** v2 splits each claim into single-feature technical elements and judges each one separately as `explicit`, `inferred`, `partial` or `missing`, with supporting passage labels. Claim references such as "The system of claim 1" are excluded. Coverage is calculated in Python from the element statuses (explicit = 1, inferred = 0.75, partial = 0.5, missing = 0, averaged and scaled to 0–100). Comparison runs at temperature 0.1. v1 is unchanged and remains the workflow default.

**First iteration.** The first v2 prompt merged several features into compound elements (for example "transmission ratio and selected operating band during work and turns"), so one new feature caused the whole element to be marked missing: the all-or-nothing problem returned at element level. A prompt-only change (one feature per element; conditions split from the actions they control) fixed the splitting.

**Results on the demo claims** (`examples/demo_claims.json`), two runs:

| Claim | Run 1 | Run 2 |
|---|---|---|
| 01 (components incl. optical sensor) | evidence, 83 | evidence, 83 |
| 02 (transmission and operating band) | evidence, 50 | evidence, 25 |
| 03 (sequence enabled only after optical confirmation) | evidence, 19 | no supporting passage |
| 04 (operator prompt when sensor obscured) | no supporting passage | no supporting passage |

**Improvements over v1**
- Claim references are no longer treated as elements.
- Known features are cited even when another element of the claim is new (claim 03, run 1: stored headland sequence cited from synthetic document 4; optical confirmation and observation count marked missing).
- Each judgement is visible per element, which makes the result easier for a reviewer to check.
- Claims 01 and 04 gave identical results in both runs.

**Remaining issues**
- Individual element judgements still change between runs at temperature 0.1: claim 03's stored-sequence element was judged covered in run 1 and missing in run 2; claim 02's operating-band element changed in the same way. Calculating coverage in code stabilises the formula, not the judgements feeding it.
- v2 marked the stored headland sequence as "inferred" although synthetic document 4 states it explicitly; the judgement is cautious rather than wrong.
- Retrieval limit: claim 03's approach-region condition is described in synthetic document 4 ("pass-end region", page 1), but that passage was not among the top 4 retrieved for the whole claim. Marking it missing was therefore correct given the evidence supplied. Retrieving per element is a likely improvement.

**Caveat.** v2 was developed on these same four demo claims. The formal v1-versus-v2 comparison must also include claims that were not used for tuning, and should repeat each run to measure stability.