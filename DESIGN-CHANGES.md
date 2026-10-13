# Design Changes (v2, 13 October 2026)

The original architecture is unchanged: two Gemini-backed agents, deterministic retrieval, citation validation and scoring in Python, coordinated by LangGraph. These changes make the scope fit a 5-day build and make every portfolio claim provable.

| # | Change | Why | Where |
|---|---|---|---|
| 1 | DOCX extraction moved to a stretch goal | Saves time; PDF and TXT/Markdown cover the demo and evaluation | Spec §2, §2a, §5, §6, §8, §10, §12; docs 01, 02, 08, 09 |
| 2 | Added a small real-patent demo set (5–8 published PDFs, downloaded manually, listed in `examples/REAL_PATENTS.md`, not committed) | "Patent documents" becomes true without adding patent-office APIs; agricultural machinery patents fit the target role | Spec §2, §11; docs 01, 09, 17 |
| 3 | Minimum required evaluation: Recall@1/@4 on 10–15 labeled claims, threshold counts, prompt v1 vs v2, timings | Turns "benchmarked prompt pipelines" into a statement backed by real numbers | Spec §9, §10, §12; docs 11, 15 |
| 4 | Added `claim_compare_v2.md` and `scripts/compare_prompts.py` | A concrete before/after prompt improvement to discuss | Spec §9, §11; doc 11 |
| 5 | Per-node and total timing logged and returned | Any speed claim must be measured, not assumed | Spec §4, §6; doc 12 |
| 6 | Model-provider boundary: one module, two task functions, project-owned Pydantic types | Shows how confidential disclosures could use an approved in-company model | Spec §4, §10; docs 02, 11, 14 |
| 7 | Enterprise deployment note on confidential data | Public API use is only acceptable for fictional or public material | Doc 14 |
| 8 | One Git commit per phase | Repository history documents how the project was built | Spec §9; doc 19 |
| 9 | 5-day plan with a cut line, cut order and daily explain-it check | Interview on 21 October 2026 | Doc 19 |
| 10 | Interview guidance: honest answers on AI-assisted building, confidentiality and speed; claims allowed only once evidence exists | Prevents over-claiming | Doc 17 |
| 11 | Fixed broken reference `docs/00-DOCUMENTATION-INDEX.md` → `docs/00-README.md` | The file did not exist | Spec header |

## Not changed (deliberately)

- No patent-office crawling or public patent APIs. Out of scope for 5 days and not needed to demonstrate the workflow.
- No OCR. Scanned PDFs are reported as unsupported.
- The 65/35 triage score remains an unvalidated heuristic and is labelled as such.
