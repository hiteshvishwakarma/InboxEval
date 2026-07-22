import os
import json
import time
import logging
from tqdm import tqdm
from src.engine.golden_dataset_generator.orchestrator import GoldenDatasetOrchestrator

logging.basicConfig(level=logging.WARNING) # Set to WARNING to keep the progress bar clean
logger = logging.getLogger("MassEvolutionRunner")

JSON_INPUT_PATH = "data/golden_dataset.json"
JSONL_OUTPUT_PATH = "data/golden_dataset.jsonl"

def get_processed_ids():
    """Reads the JSONL file to find out which IDs have already been processed."""
    processed_ids = set()
    if os.path.exists(JSONL_OUTPUT_PATH):
        with open(JSONL_OUTPUT_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                        processed_ids.add(str(record.get("email_id")))
                    except json.JSONDecodeError:
                        continue
    return processed_ids

def main():
    print(f"--- InboxEval Mass Evolution Runner ---")
    
    # 1. Load the raw JSON data
    if not os.path.exists(JSON_INPUT_PATH):
        print(f"Error: Could not find {JSON_INPUT_PATH}")
        return
        
    with open(JSON_INPUT_PATH, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
        
    print(f"Loaded {len(raw_data)} total records from {JSON_INPUT_PATH}.")
    
    # 2. Get stateful checkpoint
    processed_ids = get_processed_ids()
    print(f"Found {len(processed_ids)} already processed records in {JSONL_OUTPUT_PATH}.")
    
    # 3. Filter out records that are already done
    pending_records = [r for r in raw_data if str(r.get("id")) not in processed_ids]
    print(f"Remaining records to evolve: {len(pending_records)}")
    
    if not pending_records:
        print("All records have been processed! Exiting.")
        return

    # 4. Initialize the Engine
    orchestrator = GoldenDatasetOrchestrator()
    
    # 5. Run the Engine over pending records with a Progress Bar
    for record in tqdm(pending_records, desc="Evolving Golden Dataset", unit="email"):
        record_id = str(record.get("id"))
        
        # Extract the human baseline text.
        human_text = ""
        emails_to_grade = record.get("evaluations", [])
        for e in emails_to_grade:
            if e.get("case_type") == "Human Baseline":
                human_text = e.get("email_text")
                break
                
        if not human_text:
            human_text = record.get("prompt", "")
            
        try:
            # The engine runs all 12 steps and auto-appends to the JSONL via Step 12.
            champion = orchestrator.run_pipeline(human_text, email_id=record_id)
            
            # Brief pause to cool down local GPUs or prevent API rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Failed to evolve record {record_id}: {e}")
            # Do not crash the whole script on one bad record. Continue to the next.
            continue

    print("\n--- Mass Evolution Complete ---")

if __name__ == "__main__":
    main()
