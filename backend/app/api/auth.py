from fastapi import Request
from typing import Dict, Any

from app.common.errors import HireSenseException
from app.common.context import get_tenant_id

class UserContext:
    def __init__(self, user_id: str, role: str, tenant_id: str):
        self.user_id = user_id
        self.role = role
        self.tenant_id = tenant_id

def get_current_user(request: Request) -> UserContext:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HireSenseException(
            status_code=401,
            code="UNAUTHORIZED",
            message="Bearer token is missing in the Authorization header."
        )
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HireSenseException(
            status_code=401,
            code="UNAUTHORIZED",
            message="Invalid Authorization header format. Must be Bearer <token>."
        )
        
    token = parts[1]
    
    # Mock authentication token routing
    tenant_id = get_tenant_id() or "tenant_001"
    if token == "admin_token":
        return UserContext(user_id="user_admin_001", role="ADMIN", tenant_id=tenant_id)
    elif token == "recruiter_token":
        return UserContext(user_id="user_recruiter_001", role="RECRUITER", tenant_id=tenant_id)
    else:
        raise HireSenseException(
            status_code=401,
            code="UNAUTHORIZED",
            message="Invalid bearer token."
        )

def require_admin(request: Request) -> UserContext:
    user = get_current_user(request)
    if user.role != "ADMIN":
        raise HireSenseException(
            status_code=401,  # Under api_contracts.md, the pipeline returns 401 UNAUTHORIZED for admin routes
            code="UNAUTHORIZED",
            message="This endpoint is restricted to administrator accounts only."
        )
    return user
