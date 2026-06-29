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
    use_application_default_credentials: str = field(default_factory=lambda: os.getenv("USE_APPLICATION_DEFAULT_CREDENTIALS", "false"))
    google_cloud_project: str = field(default_factory=lambda: os.getenv("GOOGLE_CLOUD_PROJECT", ""))
    google_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    google_project_id: str = field(default_factory=lambda: os.getenv("GOOGLE_PROJECT_ID", ""))
    google_cloud_region: str = field(default_factory=lambda: os.getenv("GOOGLE_CLOUD_REGION", "asia-south1"))
    gemini_model_name: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash"))
    embedding_model_name: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2"))
    ai_provider_mode: str = field(default_factory=lambda: os.getenv("AI_PROVIDER_MODE", "gemini"))
    firebase_project_id: str = field(default_factory=lambda: os.getenv("FIREBASE_PROJECT_ID", ""))
    firebase_service_account_json: str = field(default_factory=lambda: os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", ""))
    firebase_api_key: str = field(default_factory=lambda: os.getenv("FIREBASE_API_KEY", ""))
    firebase_app_id: str = field(default_factory=lambda: os.getenv("FIREBASE_APP_ID", ""))
    firebase_auth_domain: str = field(default_factory=lambda: os.getenv("FIREBASE_AUTH_DOMAIN", ""))
    firebase_storage_bucket: str = field(default_factory=lambda: os.getenv("FIREBASE_STORAGE_BUCKET", ""))
    firebase_messaging_sender_id: str = field(default_factory=lambda: os.getenv("FIREBASE_MESSAGING_SENDER_ID", ""))
    faiss_index_dir: str = field(default_factory=lambda: os.getenv("FAISS_INDEX_DIR", "backend/data/faiss"))
    gcs_project_id: str = field(default_factory=lambda: os.getenv("GCS_PROJECT_ID", ""))
    gcs_bucket_name: str = field(default_factory=lambda: os.getenv("GCS_BUCKET_NAME", ""))
    gcs_credentials_json: str = field(default_factory=lambda: os.getenv("GCS_CREDENTIALS_JSON", ""))
    gcs_region: str = field(default_factory=lambda: os.getenv("GCS_REGION", "asia-south1"))
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
    firestore_enabled: str = field(default_factory=lambda: os.getenv("FIRESTORE_ENABLED", "true"))

    def firebase_credentials_dict(self) -> Optional[Dict[str, Any]]:
        raw = self.firebase_service_account_json.strip()
        if not raw:
            return None
        if os.path.exists(raw):
            with open(raw, "r", encoding="utf-8") as f:
                return json.load(f)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def gcs_credentials_dict(self) -> Optional[Dict[str, Any]]:
        raw = self.gcs_credentials_json.strip()
        if not raw:
            return None
        if os.path.exists(raw):
            with open(raw, "r", encoding="utf-8") as f:
                return json.load(f)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None


@dataclass
class RuntimeState:
    settings: AppSettings
    firebase_ready: bool = False
    firestore_ready: bool = False
    gcs_ready: bool = False
    gemini_ready: bool = False
    faiss_ready: bool = False
    database_mode: str = "not_configured"
    firebase_status: str = "not_configured"
    firestore_status: str = "not_configured"
    gcs_status: str = "not_configured"
    gemini_status: str = "not_configured"
    faiss_status: str = "ok"
    firebase_app: Any = None
    firestore_client: Any = None
    gcs_client: Any = None

    def dependency_statuses(self) -> Dict[str, str]:
        return {
            "firebase_auth": self.firebase_status,
            "firestore": self.firestore_status,
            "postgresql": self.firestore_status,
        "database": self.database_mode,
            "gcs": self.gcs_status,
            "object_storage": self.gcs_status,
            "gemini": self.gemini_status,
            "ai_provider": self.gemini_status,
            "faiss": self.faiss_status,
        }

    def should_use_gemini(self) -> bool:
        return self.settings.ai_provider_mode.lower() == "gemini"

    def should_use_application_default_credentials(self) -> bool:
        return str(self.settings.use_application_default_credentials).lower() == "true"


def _load_service_account_credentials(raw_credentials: Optional[Dict[str, Any]]):
    if not raw_credentials:
        return None
    try:
        from google.oauth2 import service_account
    except Exception:
        return None
    try:
        return service_account.Credentials.from_service_account_info(raw_credentials)
    except Exception:
        return None


def _try_initialize_firebase(settings: AppSettings) -> Tuple[bool, str, Any, Any]:
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except Exception:
        return False, "missing_dependency", None, None

    if str(settings.firestore_enabled).lower() != "true":
        return False, "not_configured", None, None

    creds_info = settings.firebase_credentials_dict()
    firebase_app = None
    firestore_client = None

    try:
        use_adc = str(settings.use_application_default_credentials).lower() == "true"
        if firebase_admin._apps:
            firebase_app = firebase_admin.get_app()
        elif creds_info:
            firebase_app = firebase_admin.initialize_app(credentials.Certificate(creds_info))
        elif settings.firebase_project_id and use_adc:
            firebase_app = firebase_admin.initialize_app()
        else:
            return False, "not_configured", None, None

        firestore_client = firestore.client(app=firebase_app)
        
        # Probe Firestore to verify the database exists and is accessible
        try:
            list(firestore_client.collection("_probe").limit(1).stream())
        except Exception as e:
            import logging
            logging.getLogger("hiresense_api").warning(
                f"Firestore database probe failed. Disabling Firestore storage: {e}"
            )
            return False, "not_configured", firebase_app, None

        return True, "ready", firebase_app, firestore_client
    except Exception:
        return False, "degraded", firebase_app, firestore_client


def _try_initialize_gcs(settings: AppSettings) -> Tuple[bool, str, Any]:
    try:
        from google.cloud import storage
    except Exception:
        return False, "missing_dependency", None

    creds_info = settings.gcs_credentials_dict()
    creds = _load_service_account_credentials(creds_info)

    try:
        if creds is not None:
            client = storage.Client(project=settings.gcs_project_id or settings.google_cloud_project, credentials=creds)
        elif str(settings.use_application_default_credentials).lower() == "true" and (
            settings.gcs_project_id or settings.google_cloud_project
        ):
            client = storage.Client(project=settings.gcs_project_id or settings.google_cloud_project)
        else:
            return False, "not_configured", None
        return True, "ready", client
    except Exception:
        return False, "degraded", None


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
    firebase_ready, firebase_status, firebase_app, firestore_client = _try_initialize_firebase(settings)
    gcs_ready, gcs_status, gcs_client = _try_initialize_gcs(settings)
    gemini_ready, gemini_status = _probe_gemini(settings)

    runtime = RuntimeState(
        settings=settings,
        firebase_ready=firebase_ready,
        firestore_ready=bool(firestore_client),
        gcs_ready=gcs_ready,
        gemini_ready=gemini_ready,
        faiss_ready=True,
        database_mode="firestore" if firestore_client else "not_configured",
        firebase_status=firebase_status,
        firestore_status="ready" if firestore_client else firebase_status,
        gcs_status=gcs_status,
        gemini_status=gemini_status,
        faiss_status="ok",
        firebase_app=firebase_app,
        firestore_client=firestore_client,
        gcs_client=gcs_client,
    )
    return runtime
