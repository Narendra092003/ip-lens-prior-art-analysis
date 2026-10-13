# IP Lens — Multi-Agent Prior-Art Search & Novelty Triage

**Evidence-linked analysis of user-provided patent literature for technology disclosures.**

IP Lens is a portfolio project specification for a local application built with Python, LangGraph, FastAPI, ChromaDB, Gemini, and Streamlit. It structures an invention disclosure, retrieves relevant passages from documents the user uploads, and prepares a provisional novelty-risk triage report for human review.

This package is a design and implementation guide; it is not a claim that the application has already been built. The system does not search the open web, decide patentability, or provide legal advice.

## Start here

1. Read [`PROJECT_SPECIFICATION.md`](./PROJECT_SPECIFICATION.md), the source of truth for scope and acceptance criteria.
2. Use [`docs/00-README.md`](./docs/00-README.md) to navigate the numbered design documents.
3. Follow [`docs/07-GETTING-STARTED.md`](./docs/07-GETTING-STARTED.md) to open the workspace in Visual Studio Code.
4. Implement only the current phase in [`docs/19-BUILD-ORDER.md`](./docs/19-BUILD-ORDER.md), which also holds the 5-day plan.
5. See [`DESIGN-CHANGES.md`](./DESIGN-CHANGES.md) for what changed from the first version and why.

On this machine, the prepared clean implementation workspace is `C:\Users\HP\Documents\Codex\2026-10-13\ip-lens-step-by-step`. If using this ZIP as a fresh workspace, extract it and use the included `IP-Lens-Project` folder as the project root. Keep the completed `ip-lens` folder as a reference copy and keep the planning/output folder separate.

