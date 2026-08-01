from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple


def _load_dotenv_from_workspace():
    # Walk up from this file's directory to locate and parse the `.env` file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):
        env_path = os.path.join(current_dir, ".env")
        if os.path.isfile(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip()
                            # Strip quotes if present
                            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                                val = val[1:-1]
                            os.environ[key] = val
            except Exception:
                pass
            break
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            break
        current_dir = parent_dir

_load_dotenv_from_workspace()


@dataclass(frozen=True)
class AppSettings:
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "HireSense AI"))
    demo_auth_enabled: str = field(default_factory=lambda: os.getenv("DEMO_AUTH_ENABLED", "true"))
    google_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    gemini_model_name: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash"))
    embedding_model_name: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2"))
    ai_provider_mode: str = field(default_factory=lambda: os.getenv("AI_PROVIDER_MODE", "gemini"))
    supabase_url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    supabase_anon_key: str = field(default_factory=lambda: os.getenv("SUPABASE_ANON_KEY", ""))
    supabase_service_role_key: str = field(default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
    supabase_jwt_secret: str = field(default_factory=lambda: os.getenv("SUPABASE_JWT_SECRET", ""))
    faiss_index_dir: str = field(default_factory=lambda: os.getenv("FAISS_INDEX_DIR", "backend/data/faiss"))
    cloud_run_service_name: str = field(default_factory=lambda: os.getenv("CLOUD_RUN_SERVICE_NAME", ""))
    cloud_run_region: str = field(default_factory=lambda: os.getenv("CLOUD_RUN_REGION", "asia-south1"))
    challenge_dataset_dir: str = field(default_factory=lambda: os.getenv("CHALLENGE_DATASET_DIR", ""))
    challenge_candidates_path: str = field(default_factory=lambda: os.getenv("CHALLENGE_CANDIDATES_PATH", ""))
    challenge_sample_candidates_path: str = field(default_factory=lambda: os.getenv("CHALLENGE_SAMPLE_CANDIDATES_PATH", ""))
    challenge_schema_path: str = field(default_factory=lambda: os.getenv("CHALLENGE_SCHEMA_PATH", ""))
    challenge_sample_submission_path: str = field(default_factory=lambda: os.getenv("CHALLENGE_SAMPLE_SUBMISSION_PATH", ""))
    challenge_index_path: str = field(default_factory=lambda: os.getenv("CHALLENGE_INDEX_PATH", "backend/data/challenge/candidate_index.json"))
    challenge_calibration_path: str = field(default_factory=lambda: os.getenv("CHALLENGE_CALIBRATION_PATH", "backend/data/challenge/sample_calibration.json"))
    challenge_submission_output_path: str = field(default_factory=lambda: os.getenv("CHALLENGE_SUBMISSION_OUTPUT_PATH", "backend/exports/official_submission.csv"))
    challenge_dataset_autoload: str = field(default_factory=lambda: os.getenv("CHALLENGE_DATASET_AUTOLOAD", "false"))


@dataclass
class RuntimeState:
    settings: AppSettings
    gemini_ready: bool = False
    faiss_ready: bool = False
    database_mode: str = "in_memory"
    gemini_status: str = "not_configured"
    faiss_status: str = "ok"

    def dependency_statuses(self) -> Dict[str, str]:
        return {
            "database": self.database_mode,
            "gemini": self.gemini_status,
            "ai_provider": self.gemini_status,
            "faiss": self.faiss_status,
        }

    def should_use_gemini(self) -> bool:
        return self.settings.ai_provider_mode.lower() == "gemini"


def _probe_gemini(settings: AppSettings) -> Tuple[bool, str]:
    if settings.ai_provider_mode.lower() == "gemini" and settings.google_api_key.strip() and settings.gemini_model_name.strip():
        return True, "configured"
    return False, "not_configured"


@lru_cache(maxsize=1)
def load_settings() -> AppSettings:
    return AppSettings()


@lru_cache(maxsize=1)
def build_runtime_state() -> RuntimeState:
    settings = load_settings()
    gemini_ready, gemini_status = _probe_gemini(settings)

    runtime = RuntimeState(
        settings=settings,
        gemini_ready=gemini_ready,
        faiss_ready=True,
        database_mode="in_memory",
        gemini_status=gemini_status,
        faiss_status="ok",
    )
    return runtime
