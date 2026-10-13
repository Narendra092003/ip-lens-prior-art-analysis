"""Streamlit interface for the IP Lens corpus ingestion phase."""

from __future__ import annotations

import sys
from pathlib import Path

import requests
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import get_settings

settings = get_settings()
api_base_url = settings.api_base_url

st.set_page_config(page_title="IP Lens", page_icon="🔎", layout="wide")
st.title("IP Lens")
st.caption("Prior-art search and novelty-risk triage for human review")
st.info(
    "IP Lens is a research aid over documents you provide. It is not legal advice, "
    "a patentability decision, or a substitute for review by a qualified professional."
)


def api_get(path: str) -> requests.Response | None:
    try:
        return requests.get(f"{api_base_url}{path}", timeout=4)
    except requests.RequestException:
        return None


health_response = api_get("/health")
api_ready = health_response is not None and health_response.ok

status_column, model_column = st.columns(2)
with status_column:
    st.subheader("API status")
    if api_ready:
        st.success("API is running")
    else:
        st.error(
            f"API is not responding at {api_base_url}. Start it with "
            "`uv run uvicorn backend.app.main:app --reload`."
        )

with model_column:
    st.subheader("Gemini configuration")
    if api_ready:
        try:
            health_payload = health_response.json()
            if health_payload.get("gemini_configured") is True:
                st.success("Gemini is configured")
            else:
                st.warning("Gemini is not configured; model-backed features will be unavailable.")
        except (ValueError, AttributeError):
            st.warning("The API returned an unreadable health response.")
    else:
        st.caption("Unavailable until the API is running.")

st.header("Corpus")
uploaded_files = st.file_uploader(
    "Upload patent documents",
    type=["pdf", "txt", "md"],
    accept_multiple_files=True,
    help="Supported formats: searchable PDF, TXT, and Markdown.",
)

if st.button("Upload and index", disabled=not api_ready or not uploaded_files):
    multipart_files = [
        ("files", (uploaded.name, uploaded.getvalue(), uploaded.type or "application/octet-stream"))
        for uploaded in uploaded_files
    ]
    try:
        with st.spinner("Extracting, chunking, and indexing documents…"):
            upload_response = requests.post(
                f"{api_base_url}/api/documents",
                files=multipart_files,
                timeout=(5, 300),
            )
        if upload_response.ok:
            results = upload_response.json()
            indexed = results.get("indexed", [])
            failures = results.get("failures", [])
            if indexed:
                st.success(f"Indexed {len(indexed)} document(s).")
                st.dataframe(
                    [
                        {
                            "Title": item.get("title", ""),
                            "Filename": item.get("filename", ""),
                            "Passages": item.get("passage_count", 0),
                            "Drawing pages skipped": item.get("skipped_page_count", 0),
                            "Pages excluded by language": item.get(
                                "excluded_language_page_count", 0
                            ),
                        }
                        for item in indexed
                    ],
                    hide_index=True,
                    use_container_width=True,
                )
            if failures:
                st.warning(f"{len(failures)} document(s) could not be indexed:")
                for failure in failures:
                    st.markdown(
                        f"- **{failure.get('filename', 'Unknown file')}**: "
                        f"{failure.get('error', 'Unknown error')}"
                    )
            if not indexed and not failures:
                st.info("The API returned no per-file results.")
        else:
            st.error(f"Upload failed (HTTP {upload_response.status_code}). Check the API logs.")
    except requests.RequestException:
        st.error("The upload request failed. Confirm the API is still running and try again.")

corpus_response = api_get("/api/corpus") if api_ready else None
if corpus_response is not None and corpus_response.ok:
    try:
        passage_count = corpus_response.json().get("passage_count", 0)
        st.metric("Indexed passages", passage_count)
        if passage_count == 0:
            st.info("No documents are indexed yet. Upload searchable documents to get started.")
    except (ValueError, AttributeError):
        st.error("The API returned an unreadable corpus response.")
elif api_ready:
    st.error("Could not load the corpus count from the API.")

st.header("Disclosure")
st.caption(
    "Disclosure text is sent to the configured Gemini API for structured extraction. "
    "Review the generated summary and claims before using them."
)

if "disclosure_summary" not in st.session_state:
    st.session_state.disclosure_summary = ""
if "reviewed_claims" not in st.session_state:
    st.session_state.reviewed_claims = []

disclosure_text = st.text_area(
    "Invention disclosure",
    key="disclosure_text",
    height=220,
    placeholder="Describe the problem, components, how they work together, and any technical advantages.",
)

if st.button(
    "Extract summary and candidate claims",
    disabled=not api_ready or not disclosure_text.strip(),
):
    try:
        with st.spinner("Structuring the disclosure with Gemini…"):
            extraction_response = requests.post(
                f"{api_base_url}/api/disclosures/extract",
                json={"disclosure_text": disclosure_text},
                timeout=(5, 120),
            )
        if extraction_response.ok:
            extracted = extraction_response.json()
            st.session_state.disclosure_summary = extracted["invention_summary"]
            st.session_state.reviewed_claims = extracted["claims"]
            for index in range(100):
                st.session_state.pop(f"reviewed_claim_{index}", None)
            st.success("Disclosure structured. Review and edit the result below.")
        else:
            try:
                detail = extraction_response.json().get("detail", "")
            except ValueError:
                detail = ""
            if extraction_response.status_code == 503:
                st.error("Gemini is not configured. Set GEMINI_API_KEY in .env and restart the API.")
            elif extraction_response.status_code == 429:
                st.error("Gemini is rate limited. Wait briefly, then try again.")
            else:
                st.error(detail or f"Disclosure extraction failed (HTTP {extraction_response.status_code}).")
    except requests.RequestException:
        st.error("The extraction request failed. Confirm the API is running and try again.")

if st.session_state.disclosure_summary:
    st.subheader("Invention summary")
    st.write(st.session_state.disclosure_summary)
    st.subheader("Candidate claims for review")
    edited_claims: list[str] = []
    remove_index: int | None = None
    for index, claim in enumerate(st.session_state.reviewed_claims):
        claim_column, remove_column = st.columns([10, 1])
        with claim_column:
            edited = st.text_input(
                f"Claim {index + 1}",
                value=claim,
                key=f"reviewed_claim_{index}",
            )
            edited_claims.append(edited)
        with remove_column:
            st.write("")
            if st.button("Remove", key=f"remove_claim_{index}"):
                remove_index = index

    if remove_index is not None:
        st.session_state.reviewed_claims = [
            claim for index, claim in enumerate(edited_claims) if index != remove_index
        ]
        for index in range(len(edited_claims)):
            st.session_state.pop(f"reviewed_claim_{index}", None)
        st.rerun()

    if st.button("Add claim", key="add_reviewed_claim"):
        st.session_state.reviewed_claims = [*edited_claims, ""]
        st.rerun()
    else:
        st.session_state.reviewed_claims = edited_claims

st.header("Results")
st.caption("Claim findings, evidence, and report exports will be added in a later phase.")
