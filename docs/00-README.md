# IP Lens: AI Agent Platform for Patent & Prior-Art Analysis — Documentation Index

**Project:** IP Lens: AI Agent Platform for Patent & Prior-Art Analysis

**Purpose:** A structured specification for building a portfolio-quality patent-analysis demo one service at a time.
**Primary reader:** A developer building the project with Visual Studio Code and an AI coding assistant.

## Source of truth

[`../PROJECT_SPECIFICATION.md`](../PROJECT_SPECIFICATION.md) owns the product scope, technical requirements, API contracts, acceptance criteria, and ordered implementation phases. The documents below explain those requirements in more detail. If they ever disagree, follow the project specification and correct the supporting document.

[`PROJECT_OVERVIEW.md`](./PROJECT_OVERVIEW.md) describes the implemented modules, routes, status values, settings and deployment. It is checked against the current code.

## Reading order

### Part 1 — Understand the project

| Document | What it covers |
|---|---|
| [01 — Project Overview](./01-PROJECT-OVERVIEW.md) | User problem, MVP scope, intended demo, and limits |
| [02 — Tech Stack](./02-TECH-STACK.md) | Each technology's job and why it is used |
| [03 — Architecture](./03-ARCHITECTURE.md) | Components, boundaries, and data flow |
| [04 — Agent Design](./04-AGENT-DESIGN.md) | Specialist roles, inputs, outputs, and guardrails |
| [05 — Flow Walkthrough](./05-FLOW-WALKTHROUGH.md) | One example disclosure traced through the system |

### Part 2 — Prepare and build

| Document | What it covers |
|---|---|
| [06 — Project Structure](./06-PROJECT-STRUCTURE.md) | Repository layout and separation of responsibilities |
| [07 — Getting Started](./07-GETTING-STARTED.md) | Beginner setup for Windows, Visual Studio Code, and AI chat |
| [19 — Build Order](./19-BUILD-ORDER.md) | Phases and the 5-day plan, from setup to the interview demo |

### Part 3 — Implement each service

| Document | What it covers |
|---|---|
| [08 — API Design](./08-API-DESIGN.md) | Endpoints, request/response shapes, and errors |
| [09 — Document Ingestion Service](./09-DOCUMENT-INGESTION-SERVICE.md) | File validation, extraction, page metadata, and chunking |
| [10 — Retrieval and ChromaDB](./10-RETRIEVAL-AND-CHROMA.md) | Persistent vector storage, similarity, and filtering |
| [11 — Gemini and Prompt Design](./11-GEMINI-PROMPT-DESIGN.md) | Structured model calls and prompt boundaries |
| [12 — LangGraph Workflow](./12-LANGGRAPH-WORKFLOW.md) | Typed graph state, nodes, and no-evidence path |
| [13 — Data Model and Reports](./13-DATA-MODEL-AND-REPORTS.md) | Stable IDs, citations, score fields, JSON and Markdown exports |

### Part 4 — Verify and present

| Document | What it covers |
|---|---|
| [14 — Security and Data Handling](./14-SECURITY-AND-DATA-HANDLING.md) | Secrets, uploaded content, Gemini data flow, and limitations |
| [15 — Testing and Evaluation](./15-TESTING-AND-EVALUATION.md) | Focused checks and honest retrieval/prompt evaluation |
| [16 — Running Locally](./16-LOCAL-RUNNING.md) | Local startup commands and troubleshooting |
| [17 — Interview Demo](./17-INTERVIEW-DEMO.md) | A concise, reproducible portfolio walkthrough |
| [18 — Glossary and References](./18-GLOSSARY-AND-REFERENCES.md) | Key terms and official technical sources |

## Design conventions

- Changes from the first version are listed in [`../DESIGN-CHANGES.md`](../DESIGN-CHANGES.md).
- The initial corpus consists only of documents uploaded by the user. No patent-office crawler or internet search is part of this MVP.
- Every displayed evidence citation must resolve to a retrieved chunk and retain its filename and page marker.
- A similarity value is retrieval metadata, not a probability that a passage is legally relevant.
- If no claim has a valid citation, the report returns a null score and `Not scored`.
- Fictional example data must be labeled synthetic. Report evaluation results only after running the evaluation and reviewing the outputs.
- The application is a research aid for human review, not legal advice or a patentability decision.

