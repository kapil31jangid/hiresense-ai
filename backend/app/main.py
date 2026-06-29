import os
import tempfile
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError

logging.getLogger("faiss.loader").setLevel(logging.WARNING)

from app.api.middleware import TracingMiddleware
from app.common.context import get_request_id
from app.common.errors import HireSenseException, format_error_response
from app.common.runtime import build_runtime_state, load_settings
from app.api.routes import (
    health, jobs, candidates, rankings, semantic_search, ai, analytics, alerts, pipeline
)

settings = load_settings()
runtime_state = build_runtime_state()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Keep startup idempotent while still surfacing runtime wiring in app state.
    app.state.settings = load_settings()
    app.state.runtime = build_runtime_state()
    # Seed demo data into in-memory stores (no-op if data already present)
    try:
        from app.demo_seeder import seed_demo_data
        seed_demo_data()
    except Exception:
        pass  # Never block startup due to seeding errors
    yield


app = FastAPI(
    title="HireSense AI API Service",
    description="recruiter-facing communication layer and backend intelligence gateway",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.settings = settings
app.state.runtime = runtime_state

# Register Tracing and Context Middleware
app.add_middleware(TracingMiddleware)


# Custom Exception Handler for App Exceptions
@app.exception_handler(HireSenseException)
async def hiresense_exception_handler(request: Request, exc: HireSenseException):
    req_id = get_request_id()
    error_content = format_error_response(
        request_id=req_id,
        code=exc.code,
        message=exc.message,
        details=exc.details
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_content
    )

# Custom Exception Handler for Request Validation Errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = get_request_id()
    
    # Check if the validation error is in query params or path params vs JSON body
    first_loc = exc.errors()[0]["loc"] if exc.errors() else []
    error_code = "INVALID_REQUEST"
    if "query" in first_loc:
        error_code = "INVALID_QUERY"
        
    error_msg = "; ".join([f"{'.'.join(str(l) for l in err['loc'])}: {err['msg']}" for err in exc.errors()])
    
    error_content = format_error_response(
        request_id=req_id,
        code=error_code,
        message=f"Request validation failed: {error_msg}",
        details={
            "errors": exc.errors()
        }
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_content
    )

# Fallback for Generic Unhandled Exceptions (Internal Server Error)
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    req_id = get_request_id()
    logging.exception(f"Unhandled exception during request {req_id}: {exc}")
    error_content = format_error_response(
        request_id=req_id,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred. Please contact system support.",
        details={"original_error": str(exc)}
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_content
    )

# Include all API V1 routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(candidates.router, prefix="/api/v1")
app.include_router(rankings.router, prefix="/api/v1")
app.include_router(semantic_search.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(pipeline.router, prefix="/api/v1")


def _download_export_from_gcs(filename: str) -> str | None:
    runtime = getattr(app.state, "runtime", None) or build_runtime_state()
    if not runtime.gcs_ready or runtime.gcs_client is None:
        return None

    bucket_name = runtime.settings.gcs_bucket_name or runtime.settings.google_cloud_project
    if not bucket_name:
        return None

    try:
        bucket = runtime.gcs_client.bucket(bucket_name)
        blob = bucket.blob(f"exports/{filename}")
        if not blob.exists():
            return None
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, filename)
        blob.download_to_filename(temp_path)
        return temp_path
    except Exception:
        return None


# Route to serve exported CSV shortlist files
@app.get("/exports/{filename}", tags=["Exports"])
def download_export(filename: str):
    gcs_path = _download_export_from_gcs(filename)
    if gcs_path:
        return FileResponse(
            path=gcs_path,
            media_type="text/csv",
            filename=filename
        )

    # Local dev fallback: serve from backend/exports/ directory
    local_exports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "exports")
    local_exports_dir = os.path.normpath(local_exports_dir)
    local_path = os.path.join(local_exports_dir, filename)
    if os.path.isfile(local_path):
        return FileResponse(
            path=local_path,
            media_type="text/csv",
            filename=filename
        )

    req_id = get_request_id()
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=format_error_response(
            request_id=req_id,
            code="EXPORT_FILE_NOT_FOUND",
            message="The requested export shortlist file was not found."
        )
    )
