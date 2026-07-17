import os
import json
import logging
from datetime import datetime

from ..schemas import SuperPrompt, HumanEmail

logger = logging.getLogger("Step12_GoldenRecordExport")

def export_golden_record(champion: SuperPrompt, email: HumanEmail, output_path: str = "data/golden_dataset.jsonl"):
    """
    Step 12: Golden Record Export.
    Serializes the perfect (HumanEmail, SuperPrompt) tuple and appends it to the dataset.
    """
    logger.info(f"Executing Golden Record Export for Email ID: {email.id}")
    
    # 1. Construct the Golden Tuple
    golden_record = {
        "email_id": email.id,
        "human_target_text": email.raw_text,
        "human_metadata": email.metadata,
        "optimal_super_prompt": champion.final_prompt_text,
        "final_error_delta": champion.elo_delta,
        "champion_id": champion.id,
        "export_timestamp": datetime.utcnow().isoformat()
    }
    
    # 2. Disk Serialization (JSONL) with Fallback
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(golden_record) + "\n")
            
        logger.info(f"Successfully exported Golden Record to {output_path}")
        
    except Exception as e:
        logger.error(f"Failed to write to primary dataset file {output_path}: {e}")
        
        # Fallback Mechanism to prevent data loss
        fallback_path = f"data/fallback_export_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.jsonl"
        try:
            with open(fallback_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(golden_record) + "\n")
            logger.warning(f"Successfully dumped Golden Record to fallback file: {fallback_path}")
        except Exception as fallback_e:
            logger.critical(f"Catastrophic failure: Could not write to fallback file either: {fallback_e}")
            
    # 3. Telemetry Log (Relational DB placeholder)
    logger.info(f"[DB_TELEMETRY] INSERT INTO rl_feedback_loop (email_id, prompt_id, delta) VALUES ('{email.id}', '{champion.id}', {champion.elo_delta})")
