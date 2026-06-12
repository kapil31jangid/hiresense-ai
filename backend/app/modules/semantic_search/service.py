from typing import List
from app.common.schemas import SemanticSearchRequest, SemanticSearchItem
from app.common.errors import HireSenseException
from app.modules.job.service import _jobs_db
from app.modules.candidate.service import _candidates_db

class SemanticSearchService:
    @staticmethod
    def search_candidates(data: SemanticSearchRequest) -> List[SemanticSearchItem]:
        # Validate job_id
        if data.job_id not in _jobs_db:
            raise HireSenseException(
                status_code=404,
                code="JOB_NOT_FOUND",
                message=f"Job with ID {data.job_id} was not found."
            )
            
        items = []
        # Return mock semantic search items based on candidates in the DB
        for idx, cand_id in enumerate(_candidates_db.keys()):
            # Mock semantic score
            score = round(0.95 - (idx * 0.05), 2)
            items.append(SemanticSearchItem(
                candidate_id=cand_id,
                semantic_score=max(0.5, score),
                embedding_version="candidate_v1"
            ))
            
        return items[:data.top_k]
