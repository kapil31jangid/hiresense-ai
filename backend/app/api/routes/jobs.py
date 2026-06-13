from fastapi import APIRouter, Depends, Query, status
from typing import Optional

from app.common.schemas import JobCreate, JobUpdate, JobResponse, JobListResponse, JobRequirementsResponse
from app.common.context import get_request_id
from app.api.auth import get_current_user
from app.modules.job.service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(data: JobCreate, current_user=Depends(get_current_user)):
    job_data = JobService.create_job(data)
    return JobResponse(
        request_id=get_request_id(),
        job=job_data
    )

@router.get("", response_model=JobListResponse)
def list_jobs(
    status: Optional[str] = Query(None, description="Filter jobs by status"),
    limit: int = Query(10, ge=1, le=100, description="Page size limit"),
    page_token: Optional[str] = Query(None, description="Pagination page token"),
    created_after: Optional[str] = Query(None, description="Filter jobs created after ISO timestamp"),
    current_user=Depends(get_current_user)
):
    items, next_page_token = JobService.list_jobs(
        status=status,
        limit=limit,
        page_token=page_token,
        created_after=created_after
    )
    return JobListResponse(
        request_id=get_request_id(),
        items=items,
        next_page_token=next_page_token
    )

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, current_user=Depends(get_current_user)):
    job_data = JobService.get_job(job_id)
    return JobResponse(
        request_id=get_request_id(),
        job=job_data
    )

@router.get("/{job_id}/requirements")
def get_job_requirements(job_id: str, current_user=Depends(get_current_user)):
    return JobRequirementsResponse(
        request_id=get_request_id(),
        job_requirements=JobService.get_requirements(job_id)
    )

@router.patch("/{job_id}", response_model=JobResponse)
def update_job(job_id: str, data: JobUpdate, current_user=Depends(get_current_user)):
    job_data = JobService.update_job(job_id, data)
    return JobResponse(
        request_id=get_request_id(),
        job=job_data
    )

@router.post("/{job_id}/reprocess", response_model=JobResponse)
def reprocess_job(job_id: str, current_user=Depends(get_current_user)):
    job_data = JobService.reprocess_job(job_id)
    return JobResponse(
        request_id=get_request_id(),
        job=job_data
    )
