from src.engine.golden_dataset_generator.schemas import HumanEmail

def ingest_raw_email(raw_text: str, email_id: str) -> HumanEmail:
    """Step 01: Ingests raw verbatim email string into HumanEmail model."""
    clean_text = raw_text.strip()
    return HumanEmail(id=str(email_id), raw_text=clean_text)
