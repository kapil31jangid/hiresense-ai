from fastapi import APIRouter, Depends, Request
from typing import Dict, Any

from app.common.context import get_request_id
from app.api.auth import get_current_user, UserContext
from app.common.runtime import build_runtime_state

router = APIRouter()

@router.get("/health", response_model=Dict[str, str])
def get_health():
    return {
        "request_id": get_request_id(),
        "status": "ok"
    }

@router.get("/ready", response_model=Dict[str, Any])
def get_ready(request: Request):
    runtime = getattr(request.app.state, "runtime", None) or build_runtime_state()
    return {
        "request_id": get_request_id(),
        "status": "ready",
        "dependencies": runtime.dependency_statuses(),
    }

@router.get("/me", response_model=Dict[str, Any])
def get_me(current_user: UserContext = Depends(get_current_user)):
    return {
        "request_id": get_request_id(),
        "user": {
            "user_id": current_user.user_id,
            "role": current_user.role,
            "tenant_id": current_user.tenant_id
        }
    }
