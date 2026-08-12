import json
import random
try:
    from datasets import load_dataset
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "datasets"])
    from datasets import load_dataset

def fetch_email_prompts():
    print("Loading databricks-dolly-15k dataset...")
    # Dolly-15k is a high quality instruction-tuning dataset created by humans.
    dataset = load_dataset("databricks/databricks-dolly-15k", split="train")
    
    email_data = []
    
    # We filter for tasks that specifically ask to write or respond to an email
    for row in dataset:
        if "email" in row["instruction"].lower():
            email_data.append({
                "prompt": row["instruction"],
                "context": row["context"] if row["context"] else "",
                "human_baseline_email": row["response"]
            })
            
    # Shuffle and pick a diverse subset of 30 emails to act as our core test prompts
    random.seed(42)
    random.shuffle(email_data)
    selected_data = email_data[:30]
    
    output_path = "../data/raw_email_prompts.json"
    with open(output_path, "w") as f:
        json.dump(selected_data, f, indent=4)
        
    print(f"Successfully fetched {len(selected_data)} diverse email prompts.")
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    fetch_email_prompts()
