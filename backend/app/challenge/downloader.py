import os
import gzip
import shutil
import tempfile
from pathlib import Path
from supabase import create_client, Client
from app.common.runtime import load_settings

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CACHE_DIR = REPOSITORY_ROOT / "backend" / "data" / "challenge"

def download_and_decompress(use_sample: bool = False) -> Path:
    settings = load_settings()
    
    # 1. Resolve configured local path
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

    bucket_name = "challenge-dataset"

    print(f"Dataset file missing locally at {target_path}")
    
    try:
        if not settings.supabase_url or not settings.supabase_anon_key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be configured to download from Supabase Storage.")
            
        client: Client = create_client(settings.supabase_url, settings.supabase_anon_key)
        
        if use_sample:
            blob_name = "sample_candidates.json"
            print(f"Attempting to download {blob_name} from Supabase bucket: {bucket_name}...")
            with open(target_path, 'wb') as f:
                res = client.storage.from_(bucket_name).download(blob_name)
                f.write(res)
        else:
            # For the main dataset, we must download the chunks and stitch them.
            print(f"Attempting to download candidates.jsonl.gz chunks from Supabase bucket: {bucket_name}...")
            
            # 1. Download metadata file to get chunk count
            meta_res = client.storage.from_(bucket_name).download("candidates.jsonl.gz.meta")
            num_chunks = int(meta_res.decode('utf-8').strip())
            print(f"Found {num_chunks} chunks to download.")
            
            # 2. Download each chunk and append to the final file
            with open(target_path, 'wb') as outfile:
                for i in range(num_chunks):
                    chunk_name = f"candidates.jsonl.gz.part{i}"
                    print(f"Downloading {chunk_name}...")
                    chunk_data = client.storage.from_(bucket_name).download(chunk_name)
                    outfile.write(chunk_data)
                    
        print(f"Downloaded to {target_path}")
        print(f"Successfully retrieved dataset: {target_path}")
        return target_path

    except Exception as e:
        if target_path.exists():
            try:
                os.remove(target_path)
            except Exception:
                pass
        
        err_msg = (
            f"Failed to automatically download dataset from Supabase (bucket: {bucket_name}): {e}.\n"
            f"Please ensure you have configured your SUPABASE_URL and SUPABASE_ANON_KEY."
        )
        raise FileNotFoundError(err_msg) from e
