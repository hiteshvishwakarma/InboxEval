import os
import json
import asyncio
from groq import AsyncGroq
from dotenv import load_dotenv

try:
    from datasets import load_dataset
except ImportError:
    print("Please install the datasets library: pip install datasets")
    exit(1)

load_dotenv(dotenv_path="../.env")

client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "qwen-2.5-32b" # Updated to standard Groq model ID format if applicable, else fallback to llama3
# Note: Groq uses "llama-3.3-70b-versatile" or "llama-3.1-8b-instant"
MODEL = "llama-3.3-70b-versatile"

DATASET_FILE = "../data/raw_dataset.jsonl"
CHECKPOINT_FILE = "../data/completed_ids.json"
CONCURRENCY_LIMIT = 5 # Prevent hitting rate limits instantly

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

async def backtranslate_email(email_text, retries=3):
    prompt = f"""You are an expert at reverse-engineering AI prompts.
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
}}"""
    
    for attempt in range(retries):
        try:
            response = await client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate_limit" in error_msg.lower():
                wait_time = 15 * (attempt + 1)
                print(f"[!] Rate limited. Sleeping {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                print(f"[!] Error: {error_msg}")
                await asyncio.sleep(5)
    return None

async def process_email(i, item, semaphore):
    async with semaphore:
        email_id = f"enron_{i}"
        
        # In this highly optimized pipeline, we just grab the human email
        email_body = item['email_body'].strip()
        word_count = len(email_body.split())
        
        if word_count < 20 or word_count > 500:
            return False
            
        print(f"Processing {email_id}...")
        back_data = await backtranslate_email(email_body)
        
        if back_data:
            numeric_id = 1000 + i
            dataset_entry = {
                "id": numeric_id,
                "prompt": back_data.get('prompt', ''),
                "context": back_data.get('context', ''),
                "target_persona": back_data.get('target_persona', ''),
                "source": "enron_aeslc",
                "emails_to_grade": [
                    {
                        "type": "Human Baseline",
                        "email_text": email_body
                    }
                ]
            }
            
            # $O(1)$ Append to JSONL
            with open(DATASET_FILE, "a") as f:
                f.write(json.dumps(dataset_entry) + "\n")
                
            save_completed_id(email_id)
            print(f" -> Checkpointed {email_id}.")
            return True
        return False

async def main():
    print("Loading HuggingFace Enron Dataset (aeslc)...")
    dataset_hf = load_dataset("aeslc", split="train")
    
    completed_ids = get_completed_ids()
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    tasks = []
    MAX_EMAILS = 500000 
    processed_count = 0
    
    print("Starting high-speed asynchronous ingestion...")
    
    for i, item in enumerate(dataset_hf):
        if processed_count >= MAX_EMAILS: break
        
        email_id = f"enron_{i}"
        if email_id in completed_ids: continue
        
        task = asyncio.create_task(process_email(i, item, semaphore))
        tasks.append(task)
        processed_count += 1
        
        # To prevent creating 500k tasks in memory all at once, chunk them:
        if len(tasks) >= 50:
            await asyncio.gather(*tasks)
            tasks = []
            
    if tasks:
        await asyncio.gather(*tasks)
        
    print("Mass ingestion batch complete!")

if __name__ == "__main__":
    asyncio.run(main())
