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

**What v2 changes.** v2 splits each claim into single-feature technical elements and judges each one separately as `explicit`, `inferred`, `partial` or `missing`, with supporting passage labels. Claim references such as "The system of claim 1" are excluded. Coverage is calculated in Python from the element statuses (explicit = 1, inferred = 0.75, partial = 0.5, missing = 0, averaged and scaled to 0–100). Comparison runs at temperature 0.1. v2 is now the workflow and API default; v1 remains available by explicit selection.

**First iteration.** The first v2 prompt merged several features into compound elements (for example "transmission ratio and selected operating band during work and turns"), so one new feature caused the whole element to be marked missing: the all-or-nothing problem returned at element level. A prompt-only change (one feature per element; conditions split from the actions they control) fixed the splitting.

**Initial two-run check on the demo claims** (`examples/demo_claims.json`; superseded by the seven-case comparison below):

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
- Element-level run-to-run changes are not fully recorded in the initial two-run table. **[unverified]** The earlier reviewer note that claim 03's stored-sequence element and claim 02's operating-band element changed between particular runs cannot be checked from the stored comparison output. Calculating coverage in code stabilizes the formula, not the model judgments feeding it.
- The sample report labels the stored headland sequence as inferred, although synthetic document 4 explicitly describes and claims a stored headland sequence. In that sample, the element appears to have been under-classified.
- Retrieval limit: claim 03's source describes position approaching a "pass-end region" on synthetic document 4 page 2, but that text was not among the top-four passages retrieved for the claim. Marking the approach-region feature missing was therefore consistent with the evidence supplied to that run. Retrieving per element is a possible improvement.

**Caveat.** v2 was developed on the four demo claims. The seven-case comparison below adds three held-out claims and repeats each prompt three times; its size and held-out case difficulty limit what it can establish.

## Prompt comparison (v1 vs v2)

**Setup.** 7 cases: the 4 demo claims (used while developing v2) and 3 held-out claims from the labelled set (q01, q03, q09). Retrieval run once per case; each prompt run 3 times on the same passages. Model `gemini-3.5-flash-lite`, `MIN_SIMILARITY` 50, `top_k` 4, 4-second pause between calls. Script: `scripts/compare_prompts.py`.

| Measure | v1 | v2 |
|---|---|---|
| Schema-valid results | 21/21 | 21/21 |
| Discarded citations | 0 | 0 |
| Cases with the same status in all 3 runs | 6/7 | 6/7 |
| Coverage spread across runs, mean | 7.5 | 2.0 |
| Coverage spread across runs, maximum | 25 | 12 |
| Claim references reported as elements | 7 | 0 |

**Findings.**

- v2's coverage is more stable in this sample: mean spread 2.0 vs 7.5. Demo claim 01 scored 65 / 80 / 80 with v1 and 79 / 79 / 79 with v2.
- v2 reported no claim references as elements; v1 reported seven across its runs.
- Both versions gave mixed statuses for demo claim 03: `evidence` and `no_supporting_passage` occurred across its three runs. This comparison output does not report which element caused each status.

**Limitations.**

- The held-out claims scored 100 in every run with both prompts. They are single-feature claims closely matching one passage. These results do not show whether the changes generalize to harder cases.
- The script measures schema validity and run-to-run consistency, not correctness; correctness was reviewed manually below.
- Seven cases and three runs per case is a small sample, using one model.

**Reviewer notes (v2).** Checked against the synthetic source documents, sample report, and comparison results. Per-run element details that are not present in those records are marked.

- **Demo 01 — Correct.** The synthetic tractor documents describe controllers, an operator terminal, and position sensing. None of the five synthetic documents describes a forward optical row-end sensor; it is the only missing element in the sample report.
- **Demo 02 — Partly correct.** Synthetic document 1 describes forming an engine-load estimate and adjusting the transmission ratio to maintain engine load within a selected range. That is not the same as keeping travel response within a selected operating band. The document does not describe this load-responsive ratio control during a turn. v2 coverage was 44, 50, and 38. **[unverified]** The comparison output does not show enough element-level detail to confirm that the variation came specifically from the operating-band element.
- **Demo 03 — Partly correct.** Synthetic document 4 describes a stored headland sequence and says a sequence may start when position approaches a pass-end region; this text is on source page 2, not page 1. The top-four retrieved passages in the comparison run were from page 3 or other documents and did not include that condition. The synthetic documents do not describe optical confirmation of row termination or a configured observation count. The sample report labels the stored-sequence element inferred and marks the other listed conditions missing. **[unverified]** The available comparison table does not expose the element labels for all three runs, so the claim that the stored-sequence element changed between inferred and missing, or caused the status flip, cannot be confirmed.
- **Demo 04 — Correct.** No synthetic prior-art document describes requesting confirmation because an optical sensor is obscured or observations disagree. Document 4 does pause when implement lift is not confirmed, which is a different condition.
- **q01 — Correct.** Synthetic document 1 explicitly describes adjusting the transmission ratio based on engine load, including in its claims. Both prompts returned coverage 100 in all three runs.
- **q03 — Correct.** Synthetic document 2 states that the controller raises the hitch by a bounded amount when measured draft exceeds the upper edge of a target band. Both prompts returned coverage 100 in all three runs.
- **q09 — Correct.** Synthetic document 5 claim 1 describes selecting a field or road target and adjusting tire pressure toward it. Both prompts returned coverage 100 in all three runs.

**Decision.** v2 is the workflow and API default, based on lower observed coverage spread and no claim-reference elements in this small comparison. v1 remains available for comparison.
