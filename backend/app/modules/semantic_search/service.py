import hashlib
import numpy as np
import faiss
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone

from app.common.schemas import (
    SemanticSearchRequest, SemanticSearchItem,
    SemanticJobSearchRequest, SemanticJobSearchItem,
)
from app.common.errors import HireSenseException
from app.common.repositories import FirestoreBackedStore
from app.common.runtime import build_runtime_state
from app.modules.job.service import _jobs_db
from app.modules.candidate.service import _candidates_db

_model = None

def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

# In-memory vector metadata database (stores canonical embedding records)
_embeddings_db: Dict[str, Dict[str, Any]] = FirestoreBackedStore("embeddings", {})
_index_metadata_db: Dict[str, Dict[str, Any]] = FirestoreBackedStore("semantic_indexes", {})

# In-memory dense vector storage
_candidate_vectors: Dict[str, np.ndarray] = {}
_job_vectors: Dict[str, np.ndarray] = {}

# FAISS index objects
_candidate_index: Optional[faiss.IndexFlatIP] = None
_job_index: Optional[faiss.IndexFlatIP] = None

# Row index mappings: index i -> entity_id
_candidate_vector_keys: List[str] = []
_job_vector_keys: List[str] = []

# Timestamps of last rebuilds
_candidate_last_rebuilt_at: Optional[str] = None
_job_last_rebuilt_at: Optional[str] = None


def _get_runtime():
    return build_runtime_state()


def _index_snapshot_name(entity_type: str) -> str:
    return f"semantic_indexes/{entity_type.lower()}_index.faiss"


def _serialize_index(index: Any) -> Optional[bytes]:
    try:
        serialized = faiss.serialize_index(index)
        if isinstance(serialized, bytes):
            return serialized
        if hasattr(serialized, "tobytes"):
            return serialized.tobytes()
        return bytes(serialized)
    except Exception:
        return None


def _deserialize_index(payload: bytes):
    try:
        if hasattr(faiss, "deserialize_index"):
            arr = np.frombuffer(payload, dtype=np.uint8)
            return faiss.deserialize_index(arr)
    except Exception:
        return None
    return None


def _persist_index_snapshot(entity_type: str, index: Any, vector_count: int, rebuilt_at: str) -> None:
    runtime = _get_runtime()
    snapshot_name = _index_snapshot_name(entity_type)
    payload = _serialize_index(index)
    if payload is None:
        return

    metadata = {
        "entity_type": entity_type,
        "snapshot_name": snapshot_name,
        "vector_count": vector_count,
        "rebuilt_at": rebuilt_at,
        "status": "READY",
    }
    _index_metadata_db[entity_type] = metadata

    if not runtime.gcs_ready or runtime.gcs_client is None:
        return

    bucket_name = runtime.settings.gcs_bucket_name or runtime.settings.google_cloud_project
    if not bucket_name:
        return

    try:
        bucket = runtime.gcs_client.bucket(bucket_name)
        blob = bucket.blob(snapshot_name)
        blob.upload_from_string(payload, content_type="application/octet-stream")
        blob.metadata = metadata
        blob.patch()
    except Exception:
        return


def _load_index_snapshot(entity_type: str):
    runtime = _get_runtime()
    snapshot_name = _index_snapshot_name(entity_type)

    if runtime.gcs_ready and runtime.gcs_client is not None:
        bucket_name = runtime.settings.gcs_bucket_name or runtime.settings.google_cloud_project
        if bucket_name:
            try:
                bucket = runtime.gcs_client.bucket(bucket_name)
                blob = bucket.blob(snapshot_name)
                if blob.exists():
                    payload = blob.download_as_bytes()
                    index = _deserialize_index(payload)
                    if index is not None:
                        return index
            except Exception:
                pass
    return None


class SemanticSearchService:
    @staticmethod
    def search_candidates(data: SemanticSearchRequest) -> List[SemanticSearchItem]:
        global _candidate_index, _candidate_vector_keys
        # 1. Validate job_id
        if data.job_id not in _jobs_db:
            raise HireSenseException(
                status_code=404,
                code="JOB_NOT_FOUND",
                message=f"Job with ID {data.job_id} was not found."
            )

        # 2. Check if candidate index is ready and has vectors; self-heal if candidates exist but index is empty
        if _candidate_index is None or len(_candidate_vector_keys) == 0:
            loaded = _load_index_snapshot("CANDIDATE")
            if loaded is not None:
                _candidate_index = loaded
                _candidate_vector_keys = [
                    emb["entity_id"]
                    for emb in _embeddings_db.values()
                    if emb["entity_type"] == "CANDIDATE" and emb.get("status") == "READY"
                ]

            if len(_candidates_db) > 0:
                SemanticSearchService.refresh_embeddings("CANDIDATE")
                SemanticSearchService.rebuild_indexes("CANDIDATE")

            if _candidate_index is None or len(_candidate_vector_keys) == 0:
                raise HireSenseException(
                    status_code=503,
                    code="INDEX_NOT_READY",
                    message="Candidate semantic index is not ready or contains no vectors. Please rebuild or refresh."
                )

        # 3. Get query text from job
        job = _jobs_db[data.job_id]
        title = job.get("title", "")
        req_skills = job.get("required_skills", [])
        pref_skills = job.get("preferred_skills", [])
        source_text = " ".join([title, " ".join(req_skills), " ".join(pref_skills)]).strip()

        # 4. Generate query embedding
        model = get_model()
        query_vector = model.encode([source_text])[0]
        query_vector = query_vector / np.linalg.norm(query_vector)

        # 5. Search the FAISS candidate index
        query_matrix = np.array([query_vector]).astype('float32')
        k = min(data.top_k, len(_candidate_vector_keys))
        distances, indices = _candidate_index.search(query_matrix, k)

        items = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1 or idx >= len(_candidate_vector_keys):
                continue
            cand_id = _candidate_vector_keys[idx]
            
            emb_id = f"emb_cand_{cand_id}"
            emb_meta = _embeddings_db.get(emb_id, {})
            version = emb_meta.get("embedding_version", "candidate_v1")
            
            score = round(max(0.0, min(1.0, float(dist))), 2)
            items.append(SemanticSearchItem(
                candidate_id=cand_id,
                semantic_score=score,
                embedding_version=version
            ))

        items.sort(key=lambda x: x.semantic_score, reverse=True)
        return items

    @staticmethod
    def search_jobs(data: SemanticJobSearchRequest) -> List[SemanticJobSearchItem]:
        global _job_index, _job_vector_keys
        # 1. Validate candidate_id
        if data.candidate_id not in _candidates_db:
            raise HireSenseException(
                status_code=404,
                code="CANDIDATE_NOT_FOUND",
                message=f"Candidate with ID {data.candidate_id} was not found."
            )

        # 2. Check if job index is ready and has vectors; self-heal if jobs exist but index is empty
        if _job_index is None or len(_job_vector_keys) == 0:
            loaded = _load_index_snapshot("JOB")
            if loaded is not None:
                _job_index = loaded
                _job_vector_keys = [
                    emb["entity_id"]
                    for emb in _embeddings_db.values()
                    if emb["entity_type"] == "JOB" and emb.get("status") == "READY"
                ]

            if len(_jobs_db) > 0:
                SemanticSearchService.refresh_embeddings("JOB")
                SemanticSearchService.rebuild_indexes("JOB")

            if _job_index is None or len(_job_vector_keys) == 0:
                raise HireSenseException(
                    status_code=503,
                    code="INDEX_NOT_READY",
                    message="Job semantic index is not ready or contains no vectors. Please rebuild or refresh."
                )

        # 3. Get query text from candidate
        cand = _candidates_db[data.candidate_id]
        full_name = cand.get("full_name", "")
        skills = cand.get("normalized_skills", [])
        signals = cand.get("redrob_signals", [])
        source_text = " ".join([full_name, " ".join(skills), " ".join(signals)]).strip()

        # 4. Generate query embedding
        model = get_model()
        query_vector = model.encode([source_text])[0]
        query_vector = query_vector / np.linalg.norm(query_vector)

        # 5. Search the FAISS job index
        query_matrix = np.array([query_vector]).astype('float32')
        k = min(data.top_k, len(_job_vector_keys))
        distances, indices = _job_index.search(query_matrix, k)

        items = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1 or idx >= len(_job_vector_keys):
                continue
            j_id = _job_vector_keys[idx]
            
            emb_id = f"emb_job_{j_id}"
            emb_meta = _embeddings_db.get(emb_id, {})
            version = emb_meta.get("embedding_version", "job_requirements_v1")
            
            score = round(max(0.0, min(1.0, float(dist))), 2)
            items.append(SemanticJobSearchItem(
                job_id=j_id,
                semantic_score=score,
                embedding_version=version
            ))

        items.sort(key=lambda x: x.semantic_score, reverse=True)
        return items

    @staticmethod
    def refresh_embeddings(
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None
    ) -> int:
        from app.challenge import dataset_store as challenge_dataset
        from app.modules.ranking.service import _rankings_db

        if entity_type and entity_type not in ("CANDIDATE", "JOB"):
            raise HireSenseException(400, "INVALID_REQUEST", f"Invalid entity_type: {entity_type}")
            
        if entity_id:
            if not entity_type:
                raise HireSenseException(400, "INVALID_REQUEST", "entity_type is required when entity_id is specified.")
            if entity_type == "CANDIDATE":
                if entity_id not in _candidates_db and not (challenge_dataset.is_enabled() and challenge_dataset.has_candidate(entity_id)):
                    raise HireSenseException(404, "CANDIDATE_NOT_FOUND", f"Candidate with ID {entity_id} was not found.")
            elif entity_type == "JOB":
                if entity_id not in _jobs_db and not (entity_id == "JOB_CHALLENGE_001"):
                    raise HireSenseException(404, "JOB_NOT_FOUND", f"Job with ID {entity_id} was not found.")

        jobs_to_check = []
        candidates_to_check = []
        
        if entity_type == "JOB":
            if entity_id:
                jobs_to_check = [entity_id]
            else:
                jobs_to_check = list(_jobs_db.keys())
                if challenge_dataset.is_enabled():
                    jobs_to_check.append("JOB_CHALLENGE_001")
        elif entity_type == "CANDIDATE":
            if entity_id:
                candidates_to_check = [entity_id]
            else:
                candidates_to_check = list(_candidates_db.keys())
                if challenge_dataset.is_enabled():
                    for r in _rankings_db.values():
                        for c in r.get("candidates", []):
                            c_id = c["candidate_id"]
                            if c_id not in candidates_to_check:
                                candidates_to_check.append(c_id)
        else:
            jobs_to_check = list(_jobs_db.keys())
            candidates_to_check = list(_candidates_db.keys())
            if challenge_dataset.is_enabled():
                jobs_to_check.append("JOB_CHALLENGE_001")
                for r in _rankings_db.values():
                    for c in r.get("candidates", []):
                        c_id = c["candidate_id"]
                        if c_id not in candidates_to_check:
                            candidates_to_check.append(c_id)

        refreshed_count = 0
        model = get_model()
        now_str = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

        # Process jobs
        for j_id in jobs_to_check:
            if challenge_dataset.is_enabled() and j_id == "JOB_CHALLENGE_001":
                from app.challenge.job_store import get_challenge_job
                job = get_challenge_job()
            else:
                job = _jobs_db[j_id]
            title = job.get("title", "")
            req_skills = job.get("required_skills", [])
            pref_skills = job.get("preferred_skills", [])
            source_text = " ".join([title, " ".join(req_skills), " ".join(pref_skills)]).strip()
            source_hash = hashlib.md5(source_text.encode('utf-8')).hexdigest()
            
            emb_id = f"emb_job_{j_id}"
            existing = _embeddings_db.get(emb_id)
            
            if j_id == "JOB_CHALLENGE_001":
                source_db_status = "READY" if (existing and existing.get("status") == "READY") else "STALE"
            else:
                source_db_status = job.get("embedding_metadata", {}).get("status")
            is_stale = existing is None or existing.get("source_hash") != source_hash or existing.get("status") == "STALE" or source_db_status == "STALE" or j_id not in _job_vectors
            if is_stale:
                try:
                    vector = model.encode([source_text])[0]
                    vector = vector / np.linalg.norm(vector)
                    _job_vectors[j_id] = vector
                    
                    _embeddings_db[emb_id] = {
                        "embedding_id": emb_id,
                        "entity_type": "JOB",
                        "entity_id": j_id,
                        "embedding_version": "job_requirements_v1",
                        "status": "READY",
                        "source_hash": source_hash,
                        "created_at": existing.get("created_at", now_str) if existing else now_str,
                        "updated_at": now_str,
                    }
                    
                    # Synchronize status back to source database
                    if "embedding_metadata" not in job or not isinstance(job["embedding_metadata"], dict):
                        job["embedding_metadata"] = {}
                    job["embedding_metadata"]["status"] = "READY"
                    job["embedding_metadata"]["updated_at"] = now_str
                    job["embedding_metadata"]["source_text"] = source_text
                    
                    from app.modules.alerts.service import AlertService
                    AlertService.clear_alert(f"EMBEDDING_FAILED:JOB:{j_id}", "Embedding refresh completed successfully.")
                    
                    refreshed_count += 1
                except Exception as e:
                    _embeddings_db[emb_id] = {
                        "embedding_id": emb_id,
                        "entity_type": "JOB",
                        "entity_id": j_id,
                        "embedding_version": "job_requirements_v1",
                        "status": "FAILED",
                        "source_hash": source_hash,
                        "created_at": existing.get("created_at", now_str) if existing else now_str,
                        "updated_at": now_str,
                        "error_message": str(e)
                    }
                    from app.modules.alerts.service import AlertService
                    from app.common.schemas import AlertSeverity
                    AlertService.trigger_alert(
                        alert_type="EMBEDDING_FAILED",
                        condition_key=f"EMBEDDING_FAILED:JOB:{j_id}",
                        source_entity_id=j_id,
                        title=f"Embedding refresh failed for job {j_id}",
                        message=f"Vector generation failed during job indexing: {str(e)}",
                        severity=AlertSeverity.HIGH,
                        job_id=j_id
                    )
                    raise HireSenseException(
                        status_code=503,
                        code="EMBEDDING_FAILED",
                        message=f"Embedding generation failed for Job {j_id}: {str(e)}"
                    )

        # Process candidates
        for c_id in candidates_to_check:
            if challenge_dataset.is_enabled() and c_id not in _candidates_db:
                cand = challenge_dataset.get_candidate(c_id)
            else:
                cand = _candidates_db[c_id]
            full_name = cand.get("full_name", "")
            skills = cand.get("normalized_skills", [])
            signals = cand.get("redrob_signals", [])
            source_text = " ".join([full_name, " ".join(skills), " ".join(signals)]).strip()
            source_hash = hashlib.md5(source_text.encode('utf-8')).hexdigest()
            
            emb_id = f"emb_cand_{c_id}"
            existing = _embeddings_db.get(emb_id)
            
            if cand.get("source_type") == "CHALLENGE_DATASET":
                source_db_status = "READY" if (existing and existing.get("status") == "READY") else "STALE"
            else:
                source_db_status = cand.get("embedding_metadata", {}).get("status")
            is_stale = existing is None or existing.get("source_hash") != source_hash or existing.get("status") == "STALE" or source_db_status == "STALE" or c_id not in _candidate_vectors
            if is_stale:
                try:
                    vector = model.encode([source_text])[0]
                    vector = vector / np.linalg.norm(vector)
                    _candidate_vectors[c_id] = vector
                    
                    _embeddings_db[emb_id] = {
                        "embedding_id": emb_id,
                        "entity_type": "CANDIDATE",
                        "entity_id": c_id,
                        "embedding_version": "candidate_profile_v1",
                        "status": "READY",
                        "source_hash": source_hash,
                        "created_at": existing.get("created_at", now_str) if existing else now_str,
                        "updated_at": now_str,
                    }
                    
                    # Synchronize status back to source database
                    if "embedding_metadata" not in cand or not isinstance(cand["embedding_metadata"], dict):
                        cand["embedding_metadata"] = {}
                    cand["embedding_metadata"]["status"] = "READY"
                    cand["embedding_metadata"]["updated_at"] = now_str
                    cand["embedding_metadata"]["source_text"] = source_text
                    
                    from app.modules.alerts.service import AlertService
                    AlertService.clear_alert(f"EMBEDDING_FAILED:CANDIDATE:{c_id}", "Embedding refresh completed successfully.")
                    
                    refreshed_count += 1
                except Exception as e:
                    _embeddings_db[emb_id] = {
                        "embedding_id": emb_id,
                        "entity_type": "CANDIDATE",
                        "entity_id": c_id,
                        "embedding_version": "candidate_profile_v1",
                        "status": "FAILED",
                        "source_hash": source_hash,
                        "created_at": existing.get("created_at", now_str) if existing else now_str,
                        "updated_at": now_str,
                        "error_message": str(e)
                    }
                    from app.modules.alerts.service import AlertService
                    from app.common.schemas import AlertSeverity
                    AlertService.trigger_alert(
                        alert_type="EMBEDDING_FAILED",
                        condition_key=f"EMBEDDING_FAILED:CANDIDATE:{c_id}",
                        source_entity_id=c_id,
                        title=f"Embedding refresh failed for candidate {c_id}",
                        message=f"Vector generation failed during candidate indexing: {str(e)}",
                        severity=AlertSeverity.HIGH,
                        candidate_id=c_id
                    )
                    raise HireSenseException(
                        status_code=503,
                        code="EMBEDDING_FAILED",
                        message=f"Embedding generation failed for Candidate {c_id}: {str(e)}"
                    )

        # Auto rebuild indexes if any vector updated
        if refreshed_count > 0:
            if len(jobs_to_check) > 0:
                SemanticSearchService.rebuild_indexes("JOB")
            if len(candidates_to_check) > 0:
                SemanticSearchService.rebuild_indexes("CANDIDATE")

        return refreshed_count

    @staticmethod
    def rebuild_indexes(entity_type: Optional[str] = None) -> List[str]:
        if entity_type and entity_type not in ("CANDIDATE", "JOB", "ALL"):
            raise HireSenseException(400, "INVALID_REQUEST", f"Invalid entity_type: {entity_type}")

        rebuilt = []
        now_str = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

        # Rebuild candidate index
        if entity_type in ("CANDIDATE", "ALL") or not entity_type:
            global _candidate_index, _candidate_vector_keys, _candidate_last_rebuilt_at
            
            ready_cands = [
                emb for emb in _embeddings_db.values()
                if emb["entity_type"] == "CANDIDATE" and emb["status"] == "READY"
            ]
            
            dimension = 384
            index = faiss.IndexFlatIP(dimension)
            vector_keys = []
            vectors_list = []
            
            for emb in ready_cands:
                c_id = emb["entity_id"]
                if c_id in _candidate_vectors:
                    vector_keys.append(c_id)
                    vectors_list.append(_candidate_vectors[c_id])
            
            if vectors_list:
                vectors_matrix = np.array(vectors_list).astype('float32')
                index.add(vectors_matrix)
                
            _candidate_index = index
            _candidate_vector_keys = vector_keys
            _candidate_last_rebuilt_at = now_str
            _persist_index_snapshot("CANDIDATE", index, len(vector_keys), now_str)
            rebuilt.append("CANDIDATE")

        # Rebuild job index
        if entity_type in ("JOB", "ALL") or not entity_type:
            global _job_index, _job_vector_keys, _job_last_rebuilt_at
            
            ready_jobs = [
                emb for emb in _embeddings_db.values()
                if emb["entity_type"] == "JOB" and emb["status"] == "READY"
            ]
            
            dimension = 384
            index = faiss.IndexFlatIP(dimension)
            vector_keys = []
            vectors_list = []
            
            for emb in ready_jobs:
                j_id = emb["entity_id"]
                if j_id in _job_vectors:
                    vector_keys.append(j_id)
                    vectors_list.append(_job_vectors[j_id])
            
            if vectors_list:
                vectors_matrix = np.array(vectors_list).astype('float32')
                index.add(vectors_matrix)
                
            _job_index = index
            _job_vector_keys = vector_keys
            _job_last_rebuilt_at = now_str
            _persist_index_snapshot("JOB", index, len(vector_keys), now_str)
            rebuilt.append("JOB")

        return rebuilt

    @staticmethod
    def get_indexes_status() -> Dict[str, Any]:
        cand_status = "NOT_READY"
        if _candidate_index is not None and _candidate_last_rebuilt_at is not None:
            # Stale if explicit status="STALE" exists or if there are candidates in DB not ready in embeddings
            stale_exists = any(
                cand.get("embedding_metadata", {}).get("status") == "STALE"
                for cand in _candidates_db.values()
            ) or any(
                f"emb_cand_{c_id}" not in _embeddings_db or _embeddings_db[f"emb_cand_{c_id}"]["status"] != "READY"
                for c_id in _candidates_db.keys()
            )
            cand_status = "STALE" if stale_exists else "READY"
            
        job_status = "NOT_READY"
        if _job_index is not None and _job_last_rebuilt_at is not None:
            stale_exists = any(
                job.get("embedding_metadata", {}).get("status") == "STALE"
                for job in _jobs_db.values()
            ) or any(
                f"emb_job_{j_id}" not in _embeddings_db or _embeddings_db[f"emb_job_{j_id}"]["status"] != "READY"
                for j_id in _jobs_db.keys()
            )
            job_status = "STALE" if stale_exists else "READY"

        return {
            "candidate": {
                "status": cand_status,
                "vector_count": len(_candidate_vector_keys),
                "embedding_version": "candidate_profile_v1",
                "last_rebuilt_at": _candidate_last_rebuilt_at,
                "snapshot_name": _index_snapshot_name("CANDIDATE"),
            },
            "job": {
                "status": job_status,
                "vector_count": len(_job_vector_keys),
                "embedding_version": "job_requirements_v1",
                "last_rebuilt_at": _job_last_rebuilt_at,
                "snapshot_name": _index_snapshot_name("JOB"),
            }
        }
