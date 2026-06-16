from fastapi import APIRouter, Depends, Query, File, UploadFile, Form, status
from typing import Optional

from app.common.schemas import (
    CandidateCreate, CandidateUpdate, CandidateResponse, CandidateListResponse, 
    CandidateDetailResponse, CandidateEvidenceResponse, SourceType
)
from app.common.context import get_request_id
from app.api.auth import get_current_user
from app.modules.candidate.service import CandidateService

router = APIRouter(prefix="/candidates", tags=["Candidates"])

@router.post("", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
def create_candidate(data: CandidateCreate, current_user=Depends(get_current_user)):
    cand_data = CandidateService.create_candidate(data)
    return CandidateResponse(
        request_id=get_request_id(),
        candidate=cand_data
    )

@router.post("/upload", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def upload_candidate_resume(
    full_name: str = Form(...),
    email: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    # Process multipart file upload
    data = CandidateCreate(
        full_name=full_name,
        source_type=SourceType.FILE,
        resume_file_name=file.filename,
        email=email
    )
    cand_data = CandidateService.create_candidate(data)
    return CandidateResponse(
        request_id=get_request_id(),
        candidate=cand_data
    )

@router.get("", response_model=CandidateListResponse)
def list_candidates(
    job_id: Optional[str] = Query(None, description="Filter candidates by job"),
    status: Optional[str] = Query(None, description="Filter by candidate status"),
    limit: int = Query(10, ge=1, le=100),
    page_token: Optional[str] = Query(None),
    current_user=Depends(get_current_user)
):
    items = CandidateService.list_candidates(
        job_id=job_id,
        status=status,
        limit=limit,
        page_token=page_token
    )
    return CandidateListResponse(
        request_id=get_request_id(),
        items=items,
        next_page_token=None
    )

@router.get("/{candidate_id}", response_model=CandidateDetailResponse)
def get_candidate(candidate_id: str, current_user=Depends(get_current_user)):
    cand_detail = CandidateService.get_candidate_detail(candidate_id)
    return CandidateDetailResponse(
        request_id=get_request_id(),
        candidate=cand_detail
    )

@router.patch("/{candidate_id}", response_model=CandidateResponse)
def update_candidate(
    candidate_id: str,
    data: CandidateUpdate,
    current_user=Depends(get_current_user)
):
    cand_detail = CandidateService.update_candidate(candidate_id, data)
    return CandidateResponse(
        request_id=get_request_id(),
        candidate=cand_detail
    )

@router.get("/{candidate_id}/resume-evidence", response_model=CandidateEvidenceResponse)
def get_candidate_resume_evidence(
    candidate_id: str,
    current_user=Depends(get_current_user)
):
    evidence = CandidateService.get_resume_evidence(candidate_id)
    return CandidateEvidenceResponse(
        request_id=get_request_id(),
        candidate_id=candidate_id,
        evidence=evidence
    )

@router.post("/{candidate_id}/reprocess", response_model=CandidateResponse)
def reprocess_candidate(
    candidate_id: str,
    current_user=Depends(get_current_user)
):
    cand_detail = CandidateService.reprocess_candidate(candidate_id)
    return CandidateResponse(
        request_id=get_request_id(),
        candidate=cand_detail
    )
