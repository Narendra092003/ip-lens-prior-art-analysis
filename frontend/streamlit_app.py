"""Streamlit interface for IP Lens. API access stays behind HTTP requests."""

from __future__ import annotations

import sys
from pathlib import Path

import requests
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import get_settings
from frontend.demo_controls import (
    DEMO_MAX_CLAIMS,
    access_code_is_valid,
    claim_count_is_allowed,
    upload_sizes_are_allowed,
    uploads_are_enabled,
)
from frontend.report_display import claim_status_display, display_citations

st.set_page_config(
    page_title="IP Lens: AI Agent Platform for Patent & Prior-Art Analysis",
    page_icon="🔎",
    layout="wide",
)

settings = get_settings()
api_base_url = settings.api_base_url
demo_mode = settings.demo_mode
demo_uploads_enabled = uploads_are_enabled(demo_mode, settings.demo_allow_uploads)

st.markdown(
    """
    <style>
      .block-container { padding-top: 2rem; padding-bottom: 2.5rem; max-width: 1440px; }
      [data-testid="stMetric"] { background: #f4f7fb; border: 1px solid #e2e8f0;
        border-radius: 12px; padding: 14px 16px; }
      .ip-card { background: #fff; border: 1px solid #dce4ee; border-radius: 14px;
        padding: 1rem 1.15rem; margin: .35rem 0 1rem; }
      .ip-badge { display: inline-block; border-radius: 999px; padding: .25rem .65rem;
        font-weight: 650; font-size: .82rem; margin-bottom: .55rem; }
      .status-evidence { color: #17663a; background: #e7f5ec; }
      .status-no-supporting-passage { color: #805600; background: #fff4d6; }
      .status-no-evidence { color: #315a89; background: #e8f1fb; }
      .status-unsupported { color: #9a3434; background: #fdeaea; }
      .tech-label { display: inline-block; border: 1px solid #d9e2ec; background: #f4f7fb;
        border-radius: 999px; padding: .2rem .55rem; margin: .15rem .2rem .15rem 0;
        font-size: .78rem; color: #34445a; }
      .step-number { color: #426b9a; font-size: .8rem; font-weight: 700;
        letter-spacing: .08em; text-transform: uppercase; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("IP Lens: AI Agent Platform for Patent & Prior-Art Analysis")
st.caption(
    "Multi-agent prior-art search, claim comparison and novelty-risk triage "
    "for technology disclosures"
)
if demo_mode:
    st.warning(
        "Public demo: fictional data only. Text is sent to the Gemini API. "
        "Do not paste confidential disclosures."
    )


def api_get(path: str) -> requests.Response | None:
    try:
        return requests.get(f"{api_base_url}{path}", timeout=4)
    except requests.RequestException:
        return None


health_response = api_get("/health")
api_ready = health_response is not None and health_response.ok
health_payload: dict = {}
if api_ready:
    try:
        health_payload = health_response.json()
    except (ValueError, AttributeError):
        health_payload = {}

corpus_response = api_get("/api/corpus") if api_ready else None
passage_count: int | None = None
if corpus_response is not None and corpus_response.ok:
    try:
        passage_count = corpus_response.json().get("passage_count", 0)
    except (ValueError, AttributeError):
        passage_count = None

settings_response = api_get("/api/settings") if api_ready else None
public_settings: dict = {}
if settings_response is not None and settings_response.ok:
    try:
        public_settings = settings_response.json()
    except (ValueError, AttributeError):
        public_settings = {}

with st.sidebar:
    st.header("System")
    st.caption(f"API endpoint: {api_base_url}")
    if api_ready:
        st.success("API online")
    else:
        st.error("API unavailable")
        st.caption("Start with `uv run uvicorn backend.app.main:app --reload --port 8001`.")

    if api_ready and health_payload:
        if health_payload.get("gemini_configured") is True:
            st.success("Gemini configured")
        else:
            st.warning("Gemini not configured")
    elif api_ready:
        st.warning("Gemini status unavailable")
    else:
        st.caption("Gemini status unavailable until the API is running.")

    if settings.access_code:
        submitted_access_code = st.text_input(
            "Demo access code", type="password", key="demo_access_code"
        )
        access_allowed = access_code_is_valid(submitted_access_code, settings.access_code)
        if access_allowed:
            st.success("Access code accepted")
        else:
            st.caption("Enter the access code to enable disclosure extraction and analysis.")
    else:
        access_allowed = True

    st.metric("Indexed passages", passage_count if passage_count is not None else "—")
    if passage_count is None and api_ready:
        st.caption("Corpus count unavailable from the API.")

    st.markdown("**Active analysis settings**")
    if public_settings:
        st.caption(
            f"Similarity threshold: {public_settings.get('min_similarity', '—')}% · "
            "minimum passage similarity for retrieval."
        )
        st.caption(f"Default top_k: {public_settings.get('default_top_k', '—')}")
        st.caption(
            f"Default prompt: {public_settings.get('default_prompt_version', '—')} · "
            f"maximum claims: {public_settings.get('max_claims', '—')}"
        )
        st.caption(
            "Indexed languages: "
            + ", ".join(public_settings.get("index_languages", []))
        )
        st.caption(
            f"Chunk size / overlap: {public_settings.get('chunk_size', '—')} / "
            f"{public_settings.get('chunk_overlap', '—')}"
        )
        st.caption(f"Gemini model: {public_settings.get('gemini_model', '—')}")
    else:
        st.caption("Active settings unavailable until the API responds.")

    st.markdown("**Tech stack**")
    st.markdown(
        "".join(
            f'<span class="tech-label">{label}</span>'
            for label in ("LangGraph", "FastAPI", "ChromaDB", "Gemini", "Streamlit")
        ),
        unsafe_allow_html=True,
    )

with st.expander("How it works", expanded=True):
    step_columns = st.columns(4)
    steps = [
        (
            "Build the corpus",
            "Upload patent documents; text is extracted page by page, drawings and non-English pages are skipped, and passages are indexed in ChromaDB.",
        ),
        (
            "Structure the disclosure",
            "A Gemini agent turns the invention disclosure into a summary and candidate claims for you to review and edit.",
        ),
        (
            "Compare each claim",
            "The LangGraph workflow retrieves passages for each claim, and a second Gemini agent compares them element by element; every citation is validated in code.",
        ),
        (
            "Review the report",
            "A transparent novelty-risk triage score with per-claim evidence, sources and limitations, exportable as JSON and Markdown.",
        ),
    ]
    for index, (title, description) in enumerate(steps, start=1):
        with step_columns[index - 1]:
            st.markdown(f'<div class="step-number">Step {index}</div>', unsafe_allow_html=True)
            st.markdown(f"**{title}**")
            st.caption(description)

if "disclosure_summary" not in st.session_state:
    st.session_state.disclosure_summary = ""
if "reviewed_claims" not in st.session_state:
    st.session_state.reviewed_claims = []

st.header("① Corpus")
st.caption(
    "Searchable patent PDF, TXT and Markdown text is indexed page by page. "
    "Drawing pages and pages excluded by the configured language filter are skipped."
)
corpus_metric, corpus_upload = st.columns([1, 3])
with corpus_metric:
    st.metric("Indexed passages", passage_count if passage_count is not None else "—")
with corpus_upload:
    uploaded_files = st.file_uploader(
        "Upload patent documents",
        type=["pdf", "txt", "md"],
        accept_multiple_files=True,
        help="Supported formats: searchable PDF, TXT, and Markdown.",
        disabled=not demo_uploads_enabled,
    )
    if demo_mode and not demo_uploads_enabled:
        st.caption("Uploads are disabled for this public demo.")
    demo_file_sizes_allowed = upload_sizes_are_allowed(
        [uploaded.size for uploaded in uploaded_files or []], demo_mode
    )
    if uploaded_files and not demo_file_sizes_allowed:
        st.error("Public demo uploads are limited to 2 MB per file.")
    if st.button(
        "Upload and index",
        disabled=(
            not api_ready
            or not uploaded_files
            or not demo_uploads_enabled
            or not demo_file_sizes_allowed
        ),
    ):
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
                                "Pages excluded by language": item.get("excluded_language_page_count", 0),
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
if passage_count == 0:
    st.info("No documents are indexed yet. Upload searchable documents to get started.")
elif passage_count is None and api_ready:
    st.error("Could not load the corpus count from the API.")

st.header("② Invention disclosure")
st.caption(
    "Paste a technology disclosure describing the problem, components and how they work together. "
    "Text is sent to the Gemini API, so use only fictional or public material. "
    "Review and edit candidate claims before analysis."
)
disclosure_text = st.text_area(
    "Invention disclosure",
    key="disclosure_text",
    height=200,
    placeholder="Describe the problem, components, how they work together, and any technical advantages.",
)
if st.button(
    "Extract summary and candidate claims",
    disabled=not api_ready or not disclosure_text.strip() or not access_allowed,
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
            extracted_claims = extracted["claims"]
            if demo_mode and len(extracted_claims) > DEMO_MAX_CLAIMS:
                st.warning(
                    f"Public demo mode keeps the first {DEMO_MAX_CLAIMS} candidate claims."
                )
                extracted_claims = extracted_claims[:DEMO_MAX_CLAIMS]
            st.session_state.reviewed_claims = extracted_claims
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

st.header("③ Analysis")
st.caption("Choose a comparison prompt, then run claim-by-claim retrieval and evidence review.")
if st.session_state.disclosure_summary:
    st.subheader("Invention summary")
    st.write(st.session_state.disclosure_summary)
    st.subheader("Candidate claims for review and editing")
    edited_claims: list[str] = []
    remove_index: int | None = None
    for index, claim in enumerate(st.session_state.reviewed_claims):
        claim_column, remove_column = st.columns([10, 1])
        with claim_column:
            edited = st.text_input(
                f"Claim {index + 1}", value=claim, key=f"reviewed_claim_{index}"
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

    if st.button(
        "Add claim",
        key="add_reviewed_claim",
        disabled=not claim_count_is_allowed(len(edited_claims) + 1, demo_mode),
    ):
        st.session_state.reviewed_claims = [*edited_claims, ""]
        st.rerun()
    else:
        st.session_state.reviewed_claims = edited_claims

    prompt_column, run_column = st.columns([1, 3])
    with prompt_column:
        prompt_version = st.selectbox(
            "Comparison prompt version",
            options=["v1", "v2"],
            index=1,
            help="v1 compares claim features; v2 adds structured element checks and conservative evidence handling.",
        )
    with run_column:
        st.caption(
            "v1: feature comparison. v2: structured element comparison with more explicit "
            "evidence and uncertainty checks."
        )
        run_analysis = st.button(
            "Run analysis",
            disabled=(
                not api_ready
                or not access_allowed
                or not disclosure_text.strip()
                or not st.session_state.reviewed_claims
                or not claim_count_is_allowed(len(st.session_state.reviewed_claims), demo_mode)
                or any(not claim.strip() for claim in st.session_state.reviewed_claims)
            ),
        )
    if run_analysis:
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

st.header("④ Results")
st.caption("A transparent triage view of the uploaded corpus, with claim-level evidence and limitations.")
if "analysis_result" in st.session_state:
    analysis_result = st.session_state.analysis_result
    report = analysis_result.get("report", {})
    exports = analysis_result.get("exports", {})
    claims = report.get("claims", [])
    analysis_settings = report.get("analysis_settings", {})
    risk_score = report.get("risk_score")
    risk_band = report.get("risk_band", "Not scored")
    durations = report.get("durations_ms", {})
    measured_durations = [
        value for value in durations.values() if isinstance(value, (int, float))
    ]
    total_duration_seconds = sum(measured_durations) / 1000
    analysis_time = (
        f"{total_duration_seconds:.1f} s" if measured_durations else "Not recorded"
    )
    evidence_count = sum(item.get("evidence_status") == "evidence" for item in claims)
    no_support_count = sum(
        item.get("evidence_status") == "no_supporting_passage" for item in claims
    )

    metric_columns = st.columns(5)
    metric_columns[0].metric(
        "Novelty-risk score",
        "Not scored" if risk_score is None else f"{risk_score}/100",
        delta=f"{risk_band} band",
    )
    metric_columns[1].metric("Claims analysed", len(claims))
    metric_columns[2].metric("Claims with evidence", evidence_count)
    metric_columns[3].metric("No supporting passage", no_support_count)
    metric_columns[4].metric("Analysis time", analysis_time)

    st.markdown(
        "**Claim status legend**　"
        '<span class="ip-badge status-evidence">Evidence</span> '
        '<span class="ip-badge status-no-supporting-passage">No supporting passage</span> '
        '<span class="ip-badge status-no-evidence">No evidence</span> '
        '<span class="ip-badge status-unsupported">Unsupported</span>',
        unsafe_allow_html=True,
    )

    score_components = report.get("score_components", {})
    st.subheader("Novelty-risk triage score")
    st.metric("Risk score", "Not scored" if risk_score is None else f"{risk_score}/100", delta=risk_band)
    component_columns = st.columns(2)
    coverage_component = score_components.get("max_claim_coverage")
    similarity_component = score_components.get("best_cited_retrieval_similarity")
    component_columns[0].metric(
        "Maximum claim coverage",
        "Not scored" if coverage_component is None else f"{coverage_component}/100",
    )
    component_columns[1].metric(
        "Best cited retrieval similarity",
        "Not scored" if similarity_component is None else f"{similarity_component}/100",
    )
    st.caption(f"Formula: `{score_components.get('formula', '')}`")

    st.subheader("Claim-by-claim findings")
    for index, finding in enumerate(claims, start=1):
        status_key = finding.get("evidence_status", "unsupported")
        status_label, status_explanation = claim_status_display(
            finding, analysis_settings.get("min_similarity", 0)
        )
        badge_class = {
            "evidence": "status-evidence",
            "no_supporting_passage": "status-no-supporting-passage",
            "no_evidence": "status-no-evidence",
            "unsupported": "status-unsupported",
        }.get(status_key, "status-unsupported")
        with st.container(border=True):
            st.markdown(
                f'<span class="ip-badge {badge_class}">{status_label}</span>',
                unsafe_allow_html=True,
            )
            st.markdown(f"### Claim {index}")
            st.write(finding.get("claim_text", ""))
            st.caption(status_explanation)
            coverage = finding.get("coverage_estimate")
            st.caption(
                "Coverage estimate: Not assessed"
                if coverage is None
                else f"Coverage estimate: {coverage}/100"
            )
            elements_columns = st.columns(2)
            with elements_columns[0]:
                st.markdown("**Shared elements**")
                shared = finding.get("shared_elements", [])
                if shared:
                    for element in shared:
                        st.markdown(f"- {element}")
                else:
                    st.caption("None reported.")
            with elements_columns[1]:
                st.markdown("**Missing elements**")
                missing = finding.get("missing_elements", [])
                if missing:
                    for element in missing:
                        st.markdown(f"- {element}")
                else:
                    st.caption("None reported.")

            st.markdown("**Citations**")
            citations = display_citations(finding.get("citations", []))
            if citations:
                for citation in citations:
                    st.markdown(
                        f"- **{citation.get('filename', 'Unknown file')}** · "
                        f"page {citation.get('page', '?')} · "
                        f"similarity {citation.get('retrieval_similarity', '?')}"
                    )
                    if citation.get("combines_adjacent_passages"):
                        st.caption("Combines adjacent passages with overlapping excerpts.")
                    with st.expander("View cited passage"):
                        st.write(citation.get("excerpt", ""))
            else:
                st.caption("No citations.")

    st.markdown("**Limitations**")
    st.write(report.get("limitations", ""))
    st.markdown("**Analysis settings**")
    setting_columns = st.columns(5)
    setting_columns[0].metric("Prompt version", analysis_settings.get("comparison_prompt_version", "—"))
    setting_columns[1].metric("Gemini model", analysis_settings.get("gemini_model", "—"))
    setting_columns[2].metric("Similarity threshold", analysis_settings.get("min_similarity", "—"))
    setting_columns[3].metric("top_k", analysis_settings.get("top_k", "—"))
    setting_columns[4].metric("Corpus passages", analysis_settings.get("corpus_passage_count", "—"))

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
    st.caption("Run an analysis to see claim findings, evidence, score components and report downloads.")

st.divider()
st.caption(
    "Research aid for human review. Not legal advice or a patentability decision. "
    "Searches only the uploaded documents."
)
