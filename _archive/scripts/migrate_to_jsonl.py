import json
import os

def migrate():
    input_file = "../data/golden_dataset.json"
    output_file = "../data/raw_dataset.jsonl"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return
        
    print(f"Loading {input_file}...")
    with open(input_file, "r") as f:
        data = json.load(f)
        
    print(f"Found {len(data)} entries. Migrating to JSONL...")
    
    with open(output_file, "w") as out_f:
        for entry in data:
            out_f.write(json.dumps(entry) + "\n")
            
    print(f"Success! Migrated data to {output_file}")

if __name__ == "__main__":
    migrate()
