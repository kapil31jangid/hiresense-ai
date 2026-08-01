import os
import sys
import gzip
import shutil
import tempfile
import math
from pathlib import Path
from supabase import create_client, Client
from app.common.runtime import load_settings

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

def split_file(file_path: Path, chunk_size: int = 40 * 1024 * 1024) -> list[Path]:
    print(f"Splitting {file_path} into {chunk_size/1024/1024:.0f} MB chunks...")
    chunks = []
    file_size = os.path.getsize(file_path)
    num_chunks = math.ceil(file_size / chunk_size)
    
    with open(file_path, 'rb') as f:
        for i in range(num_chunks):
            temp_dir = tempfile.gettempdir()
            chunk_path = Path(temp_dir) / f"{file_path.name}.part{i}"
            with open(chunk_path, 'wb') as chunk_file:
                chunk_file.write(f.read(chunk_size))
            chunks.append(chunk_path)
            print(f"Created chunk {chunk_path.name}")
            
    return chunks

def upload_blob(client: Client, bucket_name: str, source_file: Path, destination_blob: str):
    print(f"Uploading {source_file} to supabase://{bucket_name}/{destination_blob}...")
    
    with open(source_file, 'rb') as f:
        try:
            res = client.storage.from_(bucket_name).upload(
                path=destination_blob,
                file=f,
                file_options={"upsert": "true"}
            )
            print(f"Uploaded successfully to {destination_blob}")
        except Exception as e:
            print(f"Error uploading {destination_blob}: {e}")
            raise e

def main():
    settings = load_settings()
    
    if not settings.supabase_url or not settings.supabase_service_role_key:
        print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not configured in .env.")
        sys.exit(1)
        
    bucket_name = "challenge-dataset"
    print(f"Target Bucket: {bucket_name}")
    
    candidates_path_str = settings.challenge_candidates_path
    sample_path_str = settings.challenge_sample_candidates_path
    
    if not candidates_path_str or not sample_path_str:
        print("ERROR: CHALLENGE_CANDIDATES_PATH or CHALLENGE_SAMPLE_CANDIDATES_PATH not configured in .env.")
        sys.exit(1)
        
    candidates_path = Path(candidates_path_str)
    if not candidates_path.is_absolute():
        candidates_path = REPOSITORY_ROOT / candidates_path
        
    sample_path = Path(sample_path_str)
    if not sample_path.is_absolute():
        sample_path = REPOSITORY_ROOT / sample_path
    
    if not candidates_path.exists():
        print(f"ERROR: Local candidates file not found at: {candidates_path}")
        sys.exit(1)
        
    if not sample_path.exists():
        print(f"ERROR: Local sample candidates file not found at: {sample_path}")
        sys.exit(1)
        
    chunks = []
    
    try:
        chunks = split_file(candidates_path)
        
        print("Initializing Supabase Client...")
        client: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)
        
        # Upload each chunk
        for chunk in chunks:
            upload_blob(
                client=client,
                bucket_name=bucket_name,
                source_file=chunk,
                destination_blob=chunk.name
            )
            
        # Write metadata file so downloader knows how many chunks to expect
        temp_dir = tempfile.gettempdir()
        metadata_path = Path(temp_dir) / "candidates.jsonl.gz.meta"
        with open(metadata_path, 'w') as meta_file:
            meta_file.write(str(len(chunks)))
            
        upload_blob(
            client=client,
            bucket_name=bucket_name,
            source_file=metadata_path,
            destination_blob="candidates.jsonl.gz.meta"
        )
        
        # Upload sample candidates
        upload_blob(
            client=client,
            bucket_name=bucket_name,
            source_file=sample_path,
            destination_blob="sample_candidates.json"
        )
        
        print("\nSUCCESS: All files and chunks uploaded successfully to Supabase!")
        
    except Exception as e:
        print("\nEXCEPTION occurred during upload:")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        for chunk in chunks:
            if chunk.exists():
                try:
                    os.remove(chunk)
                except Exception:
                    pass
        temp_dir = tempfile.gettempdir()
        metadata_path = Path(temp_dir) / "candidates.jsonl.gz.meta"
        if metadata_path.exists():
            try:
                os.remove(metadata_path)
            except Exception:
                pass

if __name__ == "__main__":
    main()
