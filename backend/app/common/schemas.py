from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any, Dict
from datetime import datetime
from enum import Enum

# Standard Pydantic Base Config
class BaseModelWithConfig(BaseModel):
    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True
    )

# Enums
class SourceType(str, Enum):
    TEXT = "TEXT"
    FILE = "FILE"

class JobStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"

class RankingStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class AlertStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"

class AlertSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class PipelineStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class FreshnessStatus(str, Enum):
    FRESH = "FRESH"
    DELAYED = "DELAYED"
    STALE = "STALE"

# Jobs
class JobCreate(BaseModelWithConfig):
    title: str
    source_type: SourceType
    description_text: str
    location: Optional[str] = None
    employment_type: Optional[str] = None

class JobUpdate(BaseModelWithConfig):
    title: Optional[str] = None
    description_text: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    status: Optional[JobStatus] = None

class JobResponseData(BaseModelWithConfig):
    job_id: str
    title: str
    status: JobStatus
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    confidence_score: float
    created_at: str
    updated_at: Optional[str] = None
    description_text: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    role_intelligence: Dict[str, Any] = Field(default_factory=dict)
    embedding_metadata: Dict[str, Any] = Field(default_factory=dict)
    requirement_version: int = 1

class JobResponse(BaseModelWithConfig):
    request_id: str
    job: JobResponseData

class JobListItem(BaseModelWithConfig):
    job_id: str
    title: str
    status: JobStatus
    candidate_count: int = 0
    created_at: str

class JobListResponse(BaseModelWithConfig):
    request_id: str
    items: List[JobListItem]
    next_page_token: Optional[str] = None

class JobRequirementItem(BaseModelWithConfig):
    requirement_type: str
    canonical_value: str
    source_text: str
    source_span_start: Optional[int] = None
    source_span_end: Optional[int] = None
    confidence_score: float

class JobRequirementsData(BaseModelWithConfig):
    job_id: str
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    confidence_score: float
    role_intelligence: Dict[str, Any] = Field(default_factory=dict)
    requirement_evidence: List[JobRequirementItem] = Field(default_factory=list)
    embedding_metadata: Dict[str, Any] = Field(default_factory=dict)
    updated_at: Optional[str] = None
    requirement_version: int = 1

class JobRequirementsResponse(BaseModelWithConfig):
    request_id: str
    job_requirements: JobRequirementsData

# Candidates
class CandidateCreate(BaseModelWithConfig):
    full_name: str
    source_type: SourceType
    resume_file_name: Optional[str] = None
    email: Optional[str] = None
    source_text: Optional[str] = None
    source_data: Optional[Dict[str, Any]] = None

class CandidateResponseData(BaseModelWithConfig):
    candidate_id: str
    full_name: str
    normalized_skills: List[str] = Field(default_factory=list)
    years_of_experience: float
    confidence_score: float
    parsing_status: str = "COMPLETED"
    created_at: str
    updated_at: str
    # Challenge schema fields
    profile: Dict[str, Any] = Field(default_factory=dict)
    career_history: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    redrob_signals: List[str] = Field(default_factory=list)
    embedding_metadata: Dict[str, Any] = Field(default_factory=dict)

class CandidateResponse(BaseModelWithConfig):
    request_id: str
    candidate: CandidateResponseData

class CandidateListItem(BaseModelWithConfig):
    candidate_id: str
    full_name: str
    confidence_score: float
    parsing_status: str = "COMPLETED"
    updated_at: str

class CandidateListResponse(BaseModelWithConfig):
    request_id: str
    items: List[CandidateListItem]
    next_page_token: Optional[str] = None

class CandidateDetailData(BaseModelWithConfig):
    candidate_id: str
    full_name: str
    normalized_skills: List[str] = Field(default_factory=list)
    behavioral_signals: List[str] = Field(default_factory=list)
    parsing_status: str = "COMPLETED"
    updated_at: str
    # Challenge schema fields
    profile: Dict[str, Any] = Field(default_factory=dict)
    career_history: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    redrob_signals: List[str] = Field(default_factory=list)
    embedding_metadata: Dict[str, Any] = Field(default_factory=dict)

class CandidateDetailResponse(BaseModelWithConfig):
    request_id: str
    candidate: CandidateDetailData

class CandidateUpdate(BaseModelWithConfig):
    full_name: Optional[str] = None
    email: Optional[str] = None
    normalized_skills: Optional[List[str]] = None
    years_of_experience: Optional[float] = None
    confidence_score: Optional[float] = None
    profile: Optional[Dict[str, Any]] = None
    career_history: Optional[List[Dict[str, Any]]] = None
    education: Optional[List[Dict[str, Any]]] = None
    skills: Optional[List[str]] = None
    redrob_signals: Optional[List[str]] = None

class CandidateEvidenceItem(BaseModelWithConfig):
    candidate_experience_evidence_id: str
    candidate_id: str
    evidence_type: str
    canonical_value: str
    source_text: str
    source_span_start: Optional[int] = None
    source_span_end: Optional[int] = None
    created_at: str

class CandidateEvidenceResponse(BaseModelWithConfig):
    request_id: str
    candidate_id: str
    evidence: List[CandidateEvidenceItem]


# Rankings
class RankingCreate(BaseModelWithConfig):
    job_id: str
    candidate_ids: List[str]
    ranking_strategy: str

class RankingResponseData(BaseModelWithConfig):
    ranking_id: str
    job_id: str
    status: RankingStatus
    candidate_count: int
    created_at: str

class RankingResponse(BaseModelWithConfig):
    request_id: str
    ranking: RankingResponseData

class RankingCandidateItem(BaseModelWithConfig):
    candidate_id: str
    rank_position: int
    fit_score: float
    confidence_score: float
    missing_required_skills: List[str] = Field(default_factory=list)
    top_match_reasons: List[str] = Field(default_factory=list)

class RankingCandidatesResponse(BaseModelWithConfig):
    request_id: str
    ranking_id: str
    items: List[RankingCandidateItem]

class RankingCandidateResponse(BaseModelWithConfig):
    request_id: str
    ranking_id: str
    candidate: RankingCandidateItem

class RankingExportResponse(BaseModelWithConfig):
    request_id: str
    ranking_id: str
    file_name: str
    content_type: str
    download_url: str
    generated_at: str

# Semantic Search
class SemanticSearchRequest(BaseModelWithConfig):
    job_id: str
    top_k: int = 25

class SemanticSearchItem(BaseModelWithConfig):
    candidate_id: str
    semantic_score: float
    embedding_version: str

class SemanticSearchResponse(BaseModelWithConfig):
    request_id: str
    job_id: str
    items: List[SemanticSearchItem]

class SemanticJobSearchRequest(BaseModelWithConfig):
    candidate_id: str
    top_k: int = 25

class SemanticJobSearchItem(BaseModelWithConfig):
    job_id: str
    semantic_score: float
    embedding_version: str

class SemanticJobSearchResponse(BaseModelWithConfig):
    request_id: str
    candidate_id: str
    items: List[SemanticJobSearchItem]

class EmbeddingsRefreshRequest(BaseModelWithConfig):
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None

class EmbeddingsRefreshResponse(BaseModelWithConfig):
    request_id: str
    status: str
    refreshed_count: int

class IndexesRebuildRequest(BaseModelWithConfig):
    entity_type: Optional[str] = None

class IndexesRebuildResponse(BaseModelWithConfig):
    request_id: str
    status: str
    rebuilt_indexes: List[str]

class IndexStatusItem(BaseModelWithConfig):
    status: str
    vector_count: int
    embedding_version: str
    last_rebuilt_at: Optional[str] = None

class IndexesStatusResponse(BaseModelWithConfig):
    request_id: str
    indexes: Dict[str, IndexStatusItem]

# Analytics
class AnalyticsSummary(BaseModelWithConfig):
    active_jobs: int
    parsed_candidates: int
    active_alert_count: int
    low_confidence_rankings: int
    average_fit_score: float

class AnalyticsResponse(BaseModelWithConfig):
    request_id: str
    analytics_last_updated_at: str
    freshness_status: FreshnessStatus
    summary: AnalyticsSummary

# Alerts
class AlertItem(BaseModelWithConfig):
    alert_id: str
    alert_type: str
    status: AlertStatus
    severity: AlertSeverity
    title: str
    message: str
    created_at: str
    job_id: Optional[str] = None

class AlertsResponse(BaseModelWithConfig):
    request_id: str
    items: List[AlertItem]

# AI Explanations
class AIExplanationRequest(BaseModelWithConfig):
    ranking_id: str
    candidate_id: str

class AIGroundingData(BaseModelWithConfig):
    skills_used: List[str] = Field(default_factory=list)
    missing_required_skills: List[str] = Field(default_factory=list)

class AIExplanationResponse(BaseModelWithConfig):
    request_id: str
    ranking_id: str
    candidate_id: str
    confidence_score: float
    explanation: str
    grounding: AIGroundingData

# Pipelines
class PipelineRunRequest(BaseModelWithConfig):
    job_id: str
    trigger_mode: str

class PipelineRunResponse(BaseModelWithConfig):
    request_id: str
    pipeline_run_id: str
    status: PipelineStatus
