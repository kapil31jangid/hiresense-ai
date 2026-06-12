from typing import Any, Dict, Optional
from fastapi import HTTPException

class HireSenseException(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

def format_error_response(request_id: str, code: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "request_id": request_id,
        "error": {
            "code": code,
            "message": message,
            "details": details or {}
        }
    }
