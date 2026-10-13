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
st.caption("Disclosure extraction and claim review will be added in a later phase.")

st.header("Results")
st.caption("Claim findings, evidence, and report exports will be added in a later phase.")
