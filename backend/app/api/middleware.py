import time
import uuid
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.common.context import set_request_id, set_tenant_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hiresense_api")

class TracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            # Generate prefix-based request ID as per contracts
            request_id = f"req_{uuid.uuid4().hex[:12]}"
            
        set_request_id(request_id)
        
        # Scopes tenant if tenant header present
        tenant_id = request.headers.get("X-Tenant-ID", "tenant_001")
        set_tenant_id(tenant_id)
        
        # Log mutation details if it's a POST, PATCH, PUT request
        is_mutation = request.method in ("POST", "PUT", "PATCH", "DELETE")
        if is_mutation:
            logger.info(f"[Mutation] request_id={request_id} method={request.method} path={request.url.path}")
        else:
            logger.info(f"[Request] request_id={request_id} method={request.method} path={request.url.path}")
            
        start_time = time.time()
        response = None
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"[Unhandled Exception] request_id={request_id} error={str(e)}")
            raise e
        finally:
            process_time = time.time() - start_time
            if response is not None:
                logger.info(f"[Response] request_id={request_id} status_code={response.status_code} duration={process_time:.4f}s")
            else:
                logger.info(f"[Response] request_id={request_id} failed duration={process_time:.4f}s")
            
        # Attach request_id to response headers
        if response is not None:
            response.headers["X-Request-ID"] = request_id
        return response
