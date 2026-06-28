import os
import gzip
import shutil
from pathlib import Path
from google.cloud import storage
from app.common.runtime import load_settings

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CACHE_DIR = REPOSITORY_ROOT / "backend" / "data" / "challenge"

def get_gcs_client(settings):
    # Initialize storage client using Application Default Credentials
    # or fallback to local user/SDK login.
    project_id = settings.gcs_project_id or settings.google_cloud_project or "hiresense-ai-kapil"
    creds_info = settings.gcs_credentials_dict()
    if creds_info:
        from app.common.runtime import _load_service_account_credentials
        creds = _load_service_account_credentials(creds_info)
        return storage.Client(project=project_id, credentials=creds)
    
    # Standard ADC client
    return storage.Client(project=project_id)

def download_and_decompress(use_sample: bool = False) -> Path:
    settings = load_settings()
    
    # 1. Resolve configured local path, or fall back to default cache path
    configured_path = settings.challenge_sample_candidates_path if use_sample else settings.challenge_candidates_path
    if configured_path:
        target_path = Path(configured_path)
        if not target_path.is_absolute():
            target_path = REPOSITORY_ROOT / target_path
    else:
        filename = "sample_candidates.json" if use_sample else "candidates.jsonl.gz"
        target_path = DEFAULT_CACHE_DIR / filename

    # Ensure parent directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # If file exists, return it immediately
    if target_path.exists():
        return target_path

    # 2. Setup GCS details
    bucket_name = "hiresense-ai"
    if hasattr(settings, "challenge_gcs_bucket") and settings.challenge_gcs_bucket:
        bucket_name = settings.challenge_gcs_bucket
    elif settings.firebase_storage_bucket:
        bucket_name = settings.firebase_storage_bucket
        
    if bucket_name == "hiresense-ai-kapil.firebasestorage.app":
        bucket_name = "hiresense-ai"

    # Define blobs
    if use_sample:
        blob_name = "challenge-dataset/sample_candidates.json"
    else:
        blob_name = "challenge-dataset/candidates.jsonl.gz"

    print(f"Dataset file missing locally at {target_path}")
    print(f"Attempting to download {blob_name} from GCS bucket: {bucket_name}...")

    try:
        client = get_gcs_client(settings)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        if not blob.exists():
            raise FileNotFoundError(f"Blob gs://{bucket_name}/{blob_name} does not exist.")

        # Download blob directly to target_path
        blob.download_to_filename(str(target_path))
        print(f"Downloaded to {target_path}")

        print(f"Successfully retrieved dataset: {target_path}")
        return target_path

    except Exception as e:
        # Clean up target_path if it exists and was partially downloaded
        if target_path.exists():
            try:
                os.remove(target_path)
            except Exception:
                pass
        
        err_msg = (
            f"Failed to automatically download dataset from GCS (bucket: {bucket_name}, blob: {blob_name}): {e}.\n"
            f"Please ensure you are authenticated to Google Cloud (e.g. run 'gcloud auth application-default login') "
            f"and have access to the project."
        )
        raise FileNotFoundError(err_msg) from e
