import os
import json
import time
import re
from groq import Groq
from dotenv import load_dotenv

try:
    from datasets import load_dataset
except ImportError:
    print("Please install the datasets library: pip install datasets")
    exit(1)

load_dotenv(dotenv_path="../.env")
api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=api_key)

# We use Qwen3-32B because of its massive 500k TPD limit
MODEL = "qwen/qwen3-32b" 
DATASET_FILE = "../data/golden_dataset.json"
CHECKPOINT_FILE = "../data/completed_ids.json"

def get_completed_ids():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_completed_id(email_id):
    completed = get_completed_ids()
    completed.add(email_id)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(list(completed), f)

def load_golden_dataset():
    if os.path.exists(DATASET_FILE):
        with open(DATASET_FILE, "r") as f:
            return json.load(f)
    return []

def save_golden_dataset(dataset):
    with open(DATASET_FILE, "w") as f:
        json.dump(dataset, f, indent=4)

def backtranslate_email_with_backoff(email_text, max_retries=1000):
    prompt = f"""
You are an expert at reverse-engineering AI prompts.
Read the following real-world corporate email:
---
{email_text[:2000]}
---
Generate the 'Original Instruction' that a user would have typed into an AI assistant to generate this exact email.
Return ONLY a valid JSON object matching this schema:
{{
    "prompt": "<The instruction to generate the email>",
    "context": "<Any background facts or context needed to write it>",
    "target_persona": "<The persona of the sender>"
}}
"""
    retries = 0
    while retries < max_retries:
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            error_msg = str(e)
            print(f"  [!] API Error: {error_msg}")
            
            # Check for Rate Limit (429)
            if "429" in error_msg or "rate_limit_exceeded" in error_msg.lower():
                # Parse wait time: "Please try again in 10m9.12s" or "8.5s"
                wait_time = 60 # Default 1 min
                match = re.search(r"try again in (?:(\d+)m)?(\d+(?:\.\d+)?)s", error_msg)
                if match:
                    mins = int(match.group(1)) if match.group(1) else 0
                    secs = float(match.group(2))
                    wait_time = (mins * 60) + secs + 5 # Add 5s buffer
                else:
                    wait_time = min(300, (2 ** retries) * 10) # Exponential backoff
                    
                print(f"  [Zzz] Rate limited! Sleeping for {wait_time:.2f} seconds...")
                time.sleep(wait_time)
                retries += 1
            else:
                print("  [!] Unhandled error, sleeping for 10 seconds...")
                time.sleep(10)
                retries += 1
                
    return None

def generate_human_baseline(email_text):
    return [
        {
            "case_type": "Human Baseline",
            "email_text": email_text,
            "human_scores": {
                "instruction_adherence": 10,
                "factual_accuracy": 10,
                "professionalism": 8, # Enron emails can be informal!
                "tone_appropriateness": 10,
                "human_likeness": 10,
                "persona_adherence": 10,
                "spam_safety": 10,
                "deliverability": 10,
                "formatting": 10,
                "structure": 10,
                "conciseness": 10,
                "intent_clarity": 10
            }
        }
    ]

def run():
    print("Loading HuggingFace Enron Dataset (aeslc)...")
    dataset_hf = load_dataset("aeslc", split="train")
    
    completed_ids = get_completed_ids()
    golden_dataset = load_golden_dataset()
    
    # We process infinitely until the dataset is completely exhausted
    MAX_EMAILS = float('inf')
    processed_count = 0
    
    print(f"Starting batch process for {MAX_EMAILS} emails. Resuming from checkpoint...")
    
    for i, item in enumerate(dataset_hf):
        if processed_count >= MAX_EMAILS:
            print(f"Reached batch limit of {MAX_EMAILS}. Stopping.")
            break
            
        email_id = f"enron_{i}"
        
        if email_id in completed_ids:
            continue
            
        email_body = item['email_body'].strip()
        
        # Filter: Skip emails that are too short (<20 words) or too long (>500 words)
        word_count = len(email_body.split())
        if word_count < 20 or word_count > 500:
            continue
            
        print(f"\n[{processed_count+1}/{MAX_EMAILS}] Processing Enron Email {email_id} ({word_count} words)...")
        
        back_data = backtranslate_email_with_backoff(email_body)
        
        if back_data:
            evaluations = generate_human_baseline(email_body)
            numeric_id = 1000 + i # Offset to avoid colliding with manual IDs
            
            dataset_entry = {
                "id": numeric_id,
                "prompt": back_data.get('prompt', ''),
                "context": back_data.get('context', ''),
                "target_persona": back_data.get('target_persona', ''),
                "source": "enron_aeslc",
                "evaluations": evaluations
            }
            
            golden_dataset.append(dataset_entry)
            
            # Stateful Checkpointing
            save_golden_dataset(golden_dataset)
            save_completed_id(email_id)
            
            print(f"  -> Success! Checkpointed {email_id}.")
            processed_count += 1
            
            time.sleep(2.5) # Standard rate limit protection
            
    print("\nMass ingestion batch complete!")

if __name__ == "__main__":
    run()
