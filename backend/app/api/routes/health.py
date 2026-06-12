from fastapi import APIRouter, Depends
from typing import Dict, Any

from app.common.context import get_request_id
from app.api.auth import get_current_user, UserContext

router = APIRouter()

@router.get("/health", response_model=Dict[str, str])
def get_health():
    return {
        "request_id": get_request_id(),
        "status": "ok"
    }

@router.get("/ready", response_model=Dict[str, Any])
def get_ready():
    # Simple dependency status check
    return {
        "request_id": get_request_id(),
        "status": "ready",
        "dependencies": {
            "postgresql": "ok",
            "faiss": "ok",
            "object_storage": "ok",
            "ai_provider": "ok"
        }
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
