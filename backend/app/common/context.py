import contextvars
from typing import Optional

# Context variables for tracing and multi-tenant scoping
request_id_ctx = contextvars.ContextVar("request_id", default="")
tenant_id_ctx = contextvars.ContextVar("tenant_id", default="")

def get_request_id() -> str:
    return request_id_ctx.get()

def set_request_id(request_id: str) -> None:
    request_id_ctx.set(request_id)

def get_tenant_id() -> str:
    return tenant_id_ctx.get()

def set_tenant_id(tenant_id: str) -> None:
    tenant_id_ctx.set(tenant_id)
