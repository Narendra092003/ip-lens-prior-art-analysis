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
from frontend.report_display import claim_status_display, display_citations

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

    prompt_version = st.selectbox(
        "Comparison prompt version",
        options=["v1", "v2"],
        index=1,
        help="Choose which claim-comparison prompt to use for this analysis.",
    )
    if st.button(
        "Run analysis",
        disabled=(
            not api_ready
            or not disclosure_text.strip()
            or not st.session_state.reviewed_claims
            or any(not claim.strip() for claim in st.session_state.reviewed_claims)
        ),
    ):
        analysis_payload = {
            "disclosure_text": disclosure_text,
            "invention_summary": st.session_state.disclosure_summary,
            "reviewed_claims": [
                {"claim_id": f"claim-{index}", "text": claim}
                for index, claim in enumerate(st.session_state.reviewed_claims, start=1)
            ],
            "prompt_version": prompt_version,
        }
        try:
            with st.spinner("Retrieving passages and comparing reviewed claims…"):
                analysis_response = requests.post(
                    f"{api_base_url}/api/analyses",
                    json=analysis_payload,
                    timeout=(5, 300),
                )
            if analysis_response.ok:
                st.session_state.analysis_result = analysis_response.json()
                st.success("Analysis completed.")
            else:
                try:
                    detail = analysis_response.json().get("detail", "")
                except (ValueError, AttributeError):
                    detail = ""
                if analysis_response.status_code == 400 and "At most" in detail:
                    st.error(f"Too many claims. {detail}")
                elif analysis_response.status_code == 400:
                    st.error(detail or "The analysis request is invalid. Review the disclosure and claims.")
                elif analysis_response.status_code == 429:
                    st.error("Gemini is rate limited. Wait briefly, then try again.")
                elif analysis_response.status_code == 503 and "configured" in detail.lower():
                    st.error("Gemini is not configured. Set GEMINI_API_KEY in .env and restart the API.")
                elif analysis_response.status_code in {502, 503, 504}:
                    st.error("The model provider could not complete the analysis. Try again later.")
                else:
                    st.error(detail or f"Analysis failed (HTTP {analysis_response.status_code}).")
        except requests.RequestException:
            st.error("The analysis request failed. Confirm the API is running and try again.")

st.header("Results")
if "analysis_result" in st.session_state:
    analysis_result = st.session_state.analysis_result
    report = analysis_result.get("report", {})
    exports = analysis_result.get("exports", {})

    risk_score = report.get("risk_score")
    risk_band = report.get("risk_band", "Not scored")
    score_label = "Not scored" if risk_score is None else f"{risk_score}/100"
    st.subheader(f"Risk band: {risk_band}")
    st.metric("Novelty-risk triage score", score_label)
    score_components = report.get("score_components", {})
    coverage_component = score_components.get("max_claim_coverage")
    similarity_component = score_components.get("best_cited_retrieval_similarity")
    component_columns = st.columns(2)
    with component_columns[0]:
        st.metric(
            "Maximum claim coverage",
            "Not scored" if coverage_component is None else f"{coverage_component}/100",
        )
    with component_columns[1]:
        st.metric(
            "Best cited retrieval similarity",
            "Not scored" if similarity_component is None else f"{similarity_component}/100",
        )
    st.caption(f"Formula: `{score_components.get('formula', '')}`")
    st.info("The score is a triage heuristic over the uploaded documents, not a legal conclusion.")

    analysis_settings = report.get("analysis_settings", {})
    st.subheader("Settings")
    setting_columns = st.columns(5)
    setting_columns[0].metric("Prompt version", analysis_settings.get("comparison_prompt_version", "—"))
    setting_columns[1].metric("Gemini model", analysis_settings.get("gemini_model", "—"))
    setting_columns[2].metric("MIN_SIMILARITY", analysis_settings.get("min_similarity", "—"))
    setting_columns[3].metric("top_k", analysis_settings.get("top_k", "—"))
    setting_columns[4].metric("Corpus passages", analysis_settings.get("corpus_passage_count", "—"))

    for index, finding in enumerate(report.get("claims", []), start=1):
        status_key = finding.get("evidence_status", "unsupported")
        status_label, status_explanation = claim_status_display(
            finding,
            analysis_settings.get("min_similarity", 0),
        )
        with st.expander(f"Claim {index} · {status_label}"):
            st.write(finding.get("claim_text", ""))
            st.markdown(f"**Status: {status_label}.** {status_explanation}")
            coverage = finding.get("coverage_estimate")
            st.write(
                "Coverage estimate: Not assessed"
                if coverage is None
                else f"Coverage estimate: {coverage}/100"
            )

            st.markdown("**Shared elements**")
            shared = finding.get("shared_elements", [])
            if shared:
                for element in shared:
                    st.text(f"• {element}")
            else:
                st.caption("None reported.")

            st.markdown("**Missing elements**")
            missing = finding.get("missing_elements", [])
            if missing:
                for element in missing:
                    st.text(f"• {element}")
            else:
                st.caption("None reported.")

            st.markdown("**Citations**")
            citations = display_citations(finding.get("citations", []))
            if citations:
                for citation in citations:
                    st.write(
                        f"{citation.get('filename', 'Unknown file')} · "
                        f"page {citation.get('page', '?')} · "
                        f"retrieval similarity {citation.get('retrieval_similarity', '?')}"
                    )
                    if citation.get("combines_adjacent_passages"):
                        st.caption("Combines adjacent passages with overlapping excerpts.")
                    st.text(citation.get("excerpt", ""))
            else:
                st.caption("No citations.")

    st.markdown("**Limitations**")
    st.write(report.get("limitations", ""))
    durations = report.get("durations_ms", {})
    total_duration_seconds = sum(
        value for value in durations.values() if isinstance(value, (int, float))
    ) / 1000
    st.caption(f"Total analysis duration: {total_duration_seconds:.1f} seconds")

    download_columns = st.columns(2)
    with download_columns[0]:
        st.download_button(
            "Download JSON report",
            data=exports.get("json_export", ""),
            file_name="ip_lens_report.json",
            mime="application/json",
            disabled=not exports.get("json_export"),
        )
    with download_columns[1]:
        st.download_button(
            "Download Markdown report",
            data=exports.get("markdown_export", ""),
            file_name="ip_lens_report.md",
            mime="text/markdown",
            disabled=not exports.get("markdown_export"),
        )
else:
    st.caption("Run an analysis to see claim findings, evidence, score components, and report downloads.")
