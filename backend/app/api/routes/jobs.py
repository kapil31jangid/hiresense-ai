from fastapi import APIRouter, Depends, Query, status
from typing import Optional

from app.common.schemas import JobCreate, JobResponse, JobListResponse, JobResponseData
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
    items = JobService.list_jobs(
        status=status,
        limit=limit,
        page_token=page_token,
        created_after=created_after
    )
    return JobListResponse(
        request_id=get_request_id(),
        items=items,
        next_page_token=None
    )

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, current_user=Depends(get_current_user)):
    job_data = JobService.get_job(job_id)
    return JobResponse(
        request_id=get_request_id(),
        job=job_data
    )
