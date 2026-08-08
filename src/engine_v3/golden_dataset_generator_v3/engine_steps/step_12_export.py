import json
import logging
from src.engine.golden_dataset_generator.schemas import SuperPrompt, HumanEmail

logger = logging.getLogger("EngineV3_Step12_Export")

def export_golden_record_v3(champion: SuperPrompt, email: HumanEmail, output_path: str):
    """Step 12: Export Golden Record to JSON/Database format."""
    record = {
        "email_id": email.id,
        "original_text": email.raw_text,
        "golden_super_prompt": champion.final_prompt_text,
        "mutation_id": champion.id,
        "final_error_delta": champion.elo_delta
    }
    logger.info(f"Exporting Golden Record for email {email.id} to {output_path}")
