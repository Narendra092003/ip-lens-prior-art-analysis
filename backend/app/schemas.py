"""Pydantic contracts for the IP Lens API and analysis records."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class HealthResponse(ContractModel):
    status: Literal["ok"] = "ok"
    gemini_configured: bool


class CorpusResponse(ContractModel):
    passage_count: int = Field(ge=0)
    storage_mode: Literal["local_chroma"] = "local_chroma"
    embedding_mode: str = "ChromaDB local default embedding function"


class IndexedDocument(ContractModel):
    document_id: str
    filename: str
    title: str
    passage_count: int = Field(ge=0)
    skipped_page_count: int = Field(default=0, ge=0)
    excluded_language_page_count: int = Field(default=0, ge=0)


class DocumentFailure(ContractModel):
    filename: str
    error: str


class DocumentUploadResponse(ContractModel):
    indexed: list[IndexedDocument] = Field(default_factory=list)
    failures: list[DocumentFailure] = Field(default_factory=list)


class DisclosureExtractRequest(ContractModel):
    disclosure_text: str = Field(min_length=1, max_length=100_000)


class DisclosureExtractResponse(ContractModel):
    invention_summary: str
    claims: list[str]


class AnalysisRequest(ContractModel):
    disclosure_text: str = Field(min_length=1, max_length=100_000)
    # TODO(Phase 15): enforce Settings.max_claims in the analysis route.
    reviewed_claims: list[str] = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=10)


class ReviewedClaim(ContractModel):
    claim_id: str
    text: str = Field(min_length=1)


class EvidenceCitation(ContractModel):
    chunk_id: str
    document_id: str
    title: str
    filename: str
    page: int = Field(ge=1)
    excerpt: str
    retrieval_similarity: int = Field(ge=0, le=100)


class ClaimFinding(ContractModel):
    claim_id: str
    claim_text: str
    evidence_status: Literal["evidence", "no_evidence"]
    coverage_estimate: int | None = Field(default=None, ge=0, le=100)
    shared_elements: list[str] = Field(default_factory=list)
    missing_elements: list[str] = Field(default_factory=list)
    assessment: str
    uncertainty: str
    citations: list[EvidenceCitation] = Field(default_factory=list)


class ScoreComponents(ContractModel):
    max_claim_coverage: int | None = Field(default=None, ge=0, le=100)
    best_cited_retrieval_similarity: int | None = Field(default=None, ge=0, le=100)
    formula: str = "round(0.65 * max_claim_coverage + 0.35 * best_cited_retrieval_similarity)"


class AnalysisReport(ContractModel):
    analysis_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    invention_summary: str
    reviewed_claims: list[ReviewedClaim]
    risk_score: int | None = Field(default=None, ge=0, le=100)
    risk_band: Literal["Low", "Moderate", "High", "Not scored"]
    score_components: ScoreComponents
    claims: list[ClaimFinding]
    durations_ms: dict[str, float] = Field(default_factory=dict)
    limitations: str

    @model_validator(mode="after")
    def validate_report_consistency(self) -> "AnalysisReport":
        if (self.risk_score is None) != (self.risk_band == "Not scored"):
            raise ValueError('risk_score must be null if and only if risk_band is "Not scored"')

        reviewed_claim_ids = {claim.claim_id for claim in self.reviewed_claims}
        finding_claim_ids = {finding.claim_id for finding in self.claims}
        if not finding_claim_ids.issubset(reviewed_claim_ids):
            raise ValueError("every finding claim_id must match a reviewed claim")

        return self


class ErrorResponse(ContractModel):
    detail: str
