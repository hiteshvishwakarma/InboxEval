import json
import os
from src.engine.golden_dataset_generator.orchestrator import GoldenDatasetOrchestrator

def main():
    jsonl_path = "data/temp_dataset.jsonl"
    
    # 1. Read existing records
    records = []
    with open(jsonl_path, 'r') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
                
    # 2. Identify trash records (those lacking instructional verbs at the start)
    trash_indices = []
    trash_ids = []
    valid_verbs = ["write", "draft", "generate", "email to", "create", "craft"]
    
    for i, record in enumerate(records):
        prompt = record.get("optimal_super_prompt", "").lower().strip()
        is_valid = False
        for verb in valid_verbs:
            if prompt.startswith(verb):
                is_valid = True
                break
        
        if not is_valid:
            trash_indices.append(i)
            trash_ids.append(record.get("email_id"))
            
    print(f"🔍 Found {len(trash_ids)} trash prompts: {trash_ids}")
    if not trash_ids:
        print("✅ No trash prompts found! All prompts are strictly instructional.")
        return

    # 3. Load raw human text to regenerate
    with open("data/golden_dataset.json", "r") as f:
        raw_data = json.load(f)
        
    id_to_raw_text = {}
    for r in raw_data:
        record_id = str(r.get("id"))
        if record_id in trash_ids:
            human_text = ""
            for e in r.get("evaluations", []):
                if e.get("case_type") == "Human Baseline":
                    human_text = e.get("email_text")
                    break
            if not human_text:
                human_text = r.get("prompt", "")
            id_to_raw_text[record_id] = human_text

    # 4. Regenerate using the strict Pydantic-enforced orchestrator
    orchestrator = GoldenDatasetOrchestrator()
    for i, t_id in zip(trash_indices, trash_ids):
        print(f"\n🚀 --- Regenerating Email ID {t_id} ---")
        human_text = id_to_raw_text.get(t_id, "")
        
        # Run orchestrator and output to a temporary file for this ID
        temp_out = f"data/temp_{t_id}.jsonl"
        if os.path.exists(temp_out):
            os.remove(temp_out)
            
        champion = orchestrator.run_pipeline(
            raw_email_text=human_text,
            email_id=t_id,
            output_path=temp_out
        )
        
        # Read the newly generated, strictly-schema'd record
        with open(temp_out, "r") as f:
            new_record = json.loads(f.read().strip())
            
        # Replace the trash record in memory with the new pure one
        records[i] = new_record
        os.remove(temp_out)
        
    # 5. Write the corrected dataset back to the main file
    with open(jsonl_path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
            
    print("\n✅ Successfully regenerated trash prompts and updated temp_dataset.jsonl!")

if __name__ == "__main__":
    main()
