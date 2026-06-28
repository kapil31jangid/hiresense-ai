import os
import sys
import gzip
import shutil
import tempfile
from pathlib import Path
from google.cloud import storage
from app.common.runtime import load_settings

def compress_file(src_path: Path, dest_path: Path):
    print(f"Compressing {src_path} to {dest_path}...")
    with open(src_path, 'rb') as f_in:
        with gzip.open(dest_path, 'wb', compresslevel=6) as f_out:
            shutil.copyfileobj(f_in, f_out)
    print("Compression complete.")

def upload_blob(client: storage.Client, bucket_name: str, source_file: Path, destination_blob: str):
    print(f"Uploading {source_file} to gs://{bucket_name}/{destination_blob}...")
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob)
    
    # Optional performance tuning for large uploads
    # e.g., chunk size
    blob.chunk_size = 5 * 1024 * 1024  # 5 MB chunks
    
    blob.upload_from_filename(str(source_file))
    print(f"Uploaded successfully to {destination_blob}")

def main():
    settings = load_settings()
    
    # 1. Resolve source paths
    candidates_path_str = settings.challenge_candidates_path
    sample_path_str = settings.challenge_sample_candidates_path
    bucket_name = settings.firebase_storage_bucket or "hiresense-ai"
    if hasattr(settings, "challenge_gcs_bucket") and settings.challenge_gcs_bucket:
        bucket_name = settings.challenge_gcs_bucket
    
    # Let's override bucket name to hiresense-ai explicitly if it's not set
    if not bucket_name or bucket_name == "hiresense-ai-kapil.firebasestorage.app":
        bucket_name = "hiresense-ai"
        
    print(f"Target Bucket: {bucket_name}")
    
    if not candidates_path_str or not sample_path_str:
        print("ERROR: CHALLENGE_CANDIDATES_PATH or CHALLENGE_SAMPLE_CANDIDATES_PATH not configured in .env.")
        sys.exit(1)
        
    candidates_path = Path(candidates_path_str)
    sample_path = Path(sample_path_str)
    
    if not candidates_path.exists():
        print(f"ERROR: Local candidates file not found at: {candidates_path}")
        sys.exit(1)
        
    if not sample_path.exists():
        print(f"ERROR: Local sample candidates file not found at: {sample_path}")
        sys.exit(1)
        
    # 2. Gzip candidates.jsonl to temporary file
    temp_gz_dir = tempfile.gettempdir()
    gz_candidates_path = Path(temp_gz_dir) / "candidates.jsonl.gz"
    
    try:
        compress_file(candidates_path, gz_candidates_path)
        
        # 3. Initialize GCS Client
        print("Initializing Google Cloud Storage Client...")
        client = storage.Client(project=settings.gcs_project_id or settings.google_cloud_project or "hiresense-ai-kapil")
        
        # 4. Upload candidates.jsonl.gz
        upload_blob(
            client=client,
            bucket_name=bucket_name,
            source_file=gz_candidates_path,
            destination_blob="challenge-dataset/candidates.jsonl.gz"
        )
        
        # 5. Upload sample_candidates.json
        upload_blob(
            client=client,
            bucket_name=bucket_name,
            source_file=sample_path,
            destination_blob="challenge-dataset/sample_candidates.json"
        )
        
        print("\nSUCCESS: All files uploaded successfully to the cloud!")
        
    except Exception as e:
        print("\nEXCEPTION occurred during compression or upload:")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup
        if gz_candidates_path.exists():
            try:
                os.remove(gz_candidates_path)
                print("Cleaned up temporary local gz file.")
            except Exception:
                pass

if __name__ == "__main__":
    main()
