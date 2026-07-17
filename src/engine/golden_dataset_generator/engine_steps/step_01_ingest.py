import uuid
from typing import Dict, Any
from ..schemas import HumanEmail

def ingest_raw_email(raw_text: str, metadata: Dict[str, Any] = None) -> HumanEmail:
    """
    Step 1: Ingestion.
    Accepts raw email text (e.g., from a CSV or API), generates a unique ID, 
    and validates it through the HumanEmail Pydantic schema.
    """
    if not metadata:
        metadata = {}
        
    # In a full production environment, this might pull from an Enron CSV
    # or a connected IMAP inbox. For now, it wraps the provided text.
    return HumanEmail(
        id=f"email_{uuid.uuid4().hex[:8]}",
        raw_text=raw_text,
        metadata=metadata
    )
