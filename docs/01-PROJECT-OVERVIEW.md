# 01 — Project Overview

## What are we building?

IP Lens is a local analysis tool that helps a technology researcher compare an invention disclosure with a collection of patent documents they provide. It extracts or accepts reviewed claims, searches the uploaded corpus for relevant passages, compares claim elements with those passages, and presents an evidence-linked novelty-risk triage report.

The project demonstrates a practical multi-agent workflow. Some steps use Gemini for language tasks; parsing, searching, citation validation, and score calculation remain deterministic application code.

## The problem

Patent documents are long and use specialized language. A researcher may need to find passages relevant to several claim elements and preserve the sources supporting each observation. A semantic search result alone is not enough: the analyst needs to inspect the passage, its source, the limits of the comparison, and cases where the search found no useful evidence.

## Intended user and demo

Local use is for one user, such as a student, inventor, or analyst preparing an early research review. The labeled evaluation and public container demo use fictional disclosures and synthetic prior-art documents. A local user may separately download published patents listed in `examples/REAL_PATENTS.md`; those files are not included in the container or public demo. No corpus represents all prior art. See [`PROJECT_OVERVIEW.md`](./PROJECT_OVERVIEW.md) for the implementation checked against the current code.

## MVP capabilities

- Upload searchable PDF, TXT, and Markdown files. DOCX is unsupported.
- Extract text and page/source markers, chunk it, and index it in persistent local ChromaDB.
- Enter an invention disclosure and use Gemini to propose a summary and candidate claims.
- Let the user review or edit those claims before starting analysis.
- Retrieve passages separately for each reviewed claim.
- Compare retrieved evidence with the claim and validate cited chunk IDs.
- Show score components, uncertainty, missing elements, and source excerpts.
- Export the same validated report as JSON and Markdown.

## Deliberate limits

The app does not crawl patent offices, search the public web, OCR scanned PDFs, provide enterprise authentication, or run as a multi-tenant service. A single-container public demo is available with fictional seed documents and optional safeguards. The app does not provide legal advice, decide patentability, or guarantee novelty. Its corpus is exactly the documents uploaded or synthetically seeded for that run.

## Why this is a good portfolio project

It combines document processing, vector retrieval, API design, a typed agent workflow, structured model outputs, citation provenance, evaluation, and a usable interface. The interview story is strongest when it demonstrates a complete workflow and explains its limits, not when it makes unsupported claims about accuracy or coverage.

## Success criteria

The project is ready to present when a clean local setup can ingest the fictional corpus, analyze a reviewed disclosure, show source-linked findings, export a report, survive a restart without losing its indexed corpus, and explain what the score does and does not mean. The detailed acceptance criteria are in [`../PROJECT_SPECIFICATION.md`](../PROJECT_SPECIFICATION.md).

