import uuid
from typing import Dict, Any
from ..schemas import HumanEmail

def ingest_raw_email(raw_text: str, metadata: Dict[str, Any] = None) -> HumanEmail:
    """
    Step 1: Ingestion.
    Accepts raw email text (e.g., from a CSV or API), generates a unique ID, 
    and validates it through the HumanEmail Pydantic schema.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Cannot ingest empty email text.")
        
    sanitized_text = raw_text.strip()
    
    if metadata is None:
        metadata = {}
    elif isinstance(metadata, str):
        import json
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            raise ValueError("Metadata string provided is not valid JSON.")
        
    return HumanEmail(
        id=f"email_{uuid.uuid4().hex[:8]}",
        raw_text=sanitized_text,
        metadata=metadata
    )
