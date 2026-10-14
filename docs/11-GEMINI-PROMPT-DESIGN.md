# 11 — Gemini and Prompt Design

## Provider boundary

obackend/app/services/gemini.pyo is the only module importing the official ogoogle-genaio SDK. It loads oGEMINI_API_KEYo and oGEMINI_MODELo from settings, requests structured output, parses it into Pydantic models, applies a request timeout, and retries transient rate-limit, timeout, and server failures at most twice. Provider diagnostics log the error class, status, and safe message without logging keys or prompt/disclosure text.

The two model-backed tasks are disclosure structuring and claim comparison. Retrieval, label-to-chunk mapping, citation validation, score calculation, and report assembly are Python code.

## Disclosure structuring

odisclosure_extract_v1.mdo requests a concise invention summary and candidate claims for human review. It treats disclosure content as data rather than instructions, preserves details, avoids inventing specifications, and uses temperature 0.1 to reduce variation.

## Claim comparison

The workflow defaults to prompt v2; v1 remains selectable for comparison. The model receives one reviewed claim and only that claim's useful retrieved passages. Passages are labeled oP1o, oP2o, and so on. Python maps returned labels to retrieved chunk IDs and discards labels not supplied. The prompt tells the model not to repeat passage labels in narrative text; Python also replaces any that remain with source filename and page.

The configured model defaults to ogemini-2.5-flasho. Gemini is used for exactly two tasks: disclosure structuring and evidence-bounded claim comparison. Retrieval, citation validation and score arithmetic stay in Python. The public demo warns users that disclosure text and retrieved excerpts are sent to Gemini and should be fictional or public.

- **v1** returns shared/missing elements and a coverage estimate.
- **v2** splits the claim into technical elements, excluding preambles and claim references. Each element is oexplicito, oinferredo, opartialo, or omissingo; inferred/partial explanations and support labels are returned. Python computes coverage from those statuses (1, 0.75, 0.5, 0), averaging and scaling to 0–100.

Both prompts treat passages as evidence data, distinguish explicit statements from inference, prohibit invented details and legal novelty/patentability conclusions, and say the output is for human review.

## Validation and evaluation

Structured responses are parsed and validated. Citations are checked against the retrieved passages for the same claim. The v1/v2 comparison script reuses each case's retrieval across three runs per version; its current settings and results are in `oEVALUATION.mdo](./EVALUATION.md) and ooutputs/prompt_comparison.mdo. This small evaluation measures schema validity and run-to-run consistency; it does not establish model accuracy.
