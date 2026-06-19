from fastapi import Request
from typing import Dict, Any

from app.common.errors import HireSenseException
from app.common.context import get_tenant_id
from app.common.runtime import build_runtime_state

class UserContext:
    def __init__(self, user_id: str, role: str, tenant_id: str):
        self.user_id = user_id
        self.role = role
        self.tenant_id = tenant_id


def _normalize_role(raw_role: Any) -> str:
    role = str(raw_role or "RECRUITER").upper()
    if role not in {"ADMIN", "RECRUITER"}:
        return "RECRUITER"
    return role

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
    tenant_id = get_tenant_id() or "tenant_001"

    runtime = getattr(request.app.state, "runtime", None) or build_runtime_state()
    environment = getattr(runtime.settings, "environment", "development")
    demo_auth_enabled = (
        str(environment).lower() != "production"
        and str(getattr(runtime.settings, "demo_auth_enabled", "true")).lower() == "true"
    )
    if demo_auth_enabled:
        demo_tokens = {
            "recruiter_token": UserContext("user_recruiter_001", "RECRUITER", tenant_id),
            "admin_token": UserContext("user_admin_001", "ADMIN", tenant_id),
        }
        if token in demo_tokens:
            return demo_tokens[token]

    if not runtime.firebase_ready:
        raise HireSenseException(
            status_code=503,
            code="FIREBASE_NOT_READY",
            message="Firebase authentication is not configured."
        )

    try:
        from firebase_admin import auth as firebase_auth
    except Exception as exc:
        raise HireSenseException(
            status_code=503,
            code="FIREBASE_NOT_READY",
            message="Firebase authentication is not available.",
            details={"reason": str(exc)},
        ) from exc

    try:
        decoded = firebase_auth.verify_id_token(token, check_revoked=False)
        user_id = decoded.get("uid") or decoded.get("user_id") or "firebase_user"
        role = _normalize_role(decoded.get("role") or decoded.get("custom_claims", {}).get("role"))
        firebase_tenant = decoded.get("tenant_id") or decoded.get("tenantId") or get_tenant_id()
        tenant_id = firebase_tenant or runtime.settings.firebase_project_id or runtime.settings.google_project_id or "tenant_001"
        return UserContext(user_id=user_id, role=role, tenant_id=tenant_id)
    except Exception as exc:
        raise HireSenseException(
            status_code=401,
            code="UNAUTHORIZED",
            message="Invalid Firebase ID token.",
            details={"reason": str(exc)},
        ) from exc

def require_admin(request: Request) -> UserContext:
    user = get_current_user(request)
    if user.role != "ADMIN":
        raise HireSenseException(
            status_code=401,  # Under api_contracts.md, the pipeline returns 401 UNAUTHORIZED for admin routes
            code="UNAUTHORIZED",
            message="This endpoint is restricted to administrator accounts only."
        )
    return user
