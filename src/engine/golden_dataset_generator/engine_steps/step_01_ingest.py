import uuid
from typing import Dict, Any
from ..schemas import HumanEmail

def ingest_raw_email(raw_text: str, email_id: str = None, metadata: Dict[str, Any] = None) -> HumanEmail:
    """
    Step 1: Ingestion.
    Accepts raw email text (e.g., from a CSV or API), generates a unique ID (if none provided), 
    and validates it through the HumanEmail Pydantic schema.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Cannot ingest empty email text.")
        
    sanitized_text = raw_text.strip()
    actual_id = email_id if email_id else f"email_{uuid.uuid4().hex[:8]}"
    actual_metadata = metadata if metadata else {}
        
    return HumanEmail(
        id=actual_id,
        raw_text=sanitized_text,
        metadata=actual_metadata
    )
