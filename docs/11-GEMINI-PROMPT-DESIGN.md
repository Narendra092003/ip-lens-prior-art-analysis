# 11 — Gemini and Prompt Design

## Provider boundary

`backend/app/services/gemini.py` is the only module that imports and calls the Google GenAI SDK. It reads the API key and model name from environment-backed settings, applies timeouts, requests structured output, validates it with Pydantic, and converts provider errors to safe application errors.

Routes, Streamlit, retrieval, and report scoring must not call the SDK directly. Model output is untrusted until parsed and validated.

The module exposes exactly two task functions, `structure_disclosure(text) -> DisclosureStructure` and `compare_claim(claim, passages, prompt_version) -> ClaimComparison`, using the project's Pydantic models. Nothing outside this module imports Gemini types, so a different provider can be substituted by rewriting only this file. The `prompt_version` argument lets the evaluation script run v1 and v2 on identical inputs.

## Versioned prompt files

Keep prompt templates in files such as `backend/app/prompts/disclosure_extract_v1.md` and `claim_compare_v1.md`. Each template should state the task, schema constraints, evidence boundary, prohibited claims, and behavior for uncertainty. Changes to prompts should be reviewed against the evaluation set and recorded with a version or commit.

## Disclosure-structuring prompt

Input: the user's disclosure text. Output: a concise summary and candidate numbered claims. Require the model to preserve technical details, avoid inventing missing specifications, and mark ambiguous details as uncertain. The output is for user review and is not silently considered final.

## Claim-comparison prompt

Input: one reviewed claim and its retrieved passages, each with a chunk ID and excerpt. Output: shared elements, missing elements, coverage estimate from 0 to 100, assessment, uncertainty, and proposed cited chunk IDs. The prompt must say that the passages are evidence data, not instructions, and that citations may only refer to provided IDs.

## Validation and error handling

- Validate structured output against Pydantic models.
- Reject missing required fields, invalid numeric ranges, excessive text, and malformed JSON.
- Validate cited IDs against the current claim's retrieval results in application code; never trust the prompt alone.
- Use bounded retries for transient provider failures, not an unbounded loop.
- Surface missing-key, rate-limit, timeout, and malformed-output errors clearly.
- Never log API keys, full private disclosures, or full retrieved legal documents.

## v1 and v2 of the comparison prompt

Write `claim_compare_v1.md` first and get the workflow running with it. After seeing real outputs, write `claim_compare_v2.md` to fix the most common problem you observed, for example vague shared elements, inferences presented as explicit statements, or citations that do not support the element. Record in `docs/EVALUATION.md` what you changed and why. This is what makes "benchmarked prompt pipelines" a true statement.

## Prompt evaluation

Maintain a small set of synthetic disclosure and claim-comparison cases. Compare prompt versions on structured-output validity, whether the analysis stays within supplied evidence, whether every cited ID exists, and reviewer judgments of shared/missing claim elements. Do not call prompt performance “accuracy” until a labeled set and scoring method support that claim.

