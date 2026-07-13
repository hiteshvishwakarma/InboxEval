import os
import json
import asyncio
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv(dotenv_path="../web/.env.local")

client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

RAW_FILE = "../data/raw_dataset.jsonl"
GOLDEN_FILE = "../data/golden_dataset.jsonl"
CHECKPOINT_FILE = "../data/refiner_checkpoint.json"
CONCURRENCY_LIMIT = 3

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

async def generate_synthetic_email(prompt):
    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception:
        return ""

async def semantic_debate_eval(human_email, synthetic_email):
    eval_prompt = f"""You are an elite semantic analyzer.
Compare these two emails:
[ORIGINAL HUMAN EMAIL]
{human_email}
[SYNTHETIC AI EMAIL]
{synthetic_email}
Task: Find differences in Tone, Formality, Length, and Intent. 
Output your analysis in two parts:
1. [SCORE]: A number from 0 to 10 on how perfectly the Synthetic email captures the EXACT vibe of the Human email.
2. [FEEDBACK]: A 2-sentence instruction on how to change the prompt to make the next synthetic email closer to the original."""
    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": eval_prompt}],
            temperature=0.1,
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception:
        return "[SCORE]: 0\n[FEEDBACK]: Error"

async def refine_prompt(old_prompt, feedback):
    ref_prompt = f"""You are an expert prompt engineer, but act like a normal human manager. 
Old prompt: "{old_prompt}"
Feedback on failure: "{feedback}"
Rewrite the prompt to fix these issues. 
CRITICAL RULE: The new prompt MUST sound like a real human wrote it. Do not use AI-speak like 'Output strictly in JSON'. Use casual phrasing like 'just give me the list'.
Return ONLY the new prompt text."""
    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": ref_prompt}],
            temperature=0.7,
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception:
        return old_prompt

async def process_entry(entry, semaphore):
    async with semaphore:
        email_id = str(entry.get("id"))
        print(f"Refining ID: {email_id}...")
        
        human_email = entry.get("emails_to_grade", [{}])[0].get("email_text", "")
        if not human_email: return
        
        v1_prompt = entry.get("prompt", "")
        
        # 1. Generate V1
        v1_email = await generate_synthetic_email(v1_prompt)
        # 2. Semantic Debate
        v1_eval = await semantic_debate_eval(human_email, v1_email)
        feedback = v1_eval.split("[FEEDBACK]:")[-1].strip() if "[FEEDBACK]:" in v1_eval else ""
        
        # 3. Refine
        v2_prompt = await refine_prompt(v1_prompt, feedback)
        entry["prompt"] = v2_prompt # Update entry with the perfected prompt
        
        # O(1) Append to final Golden file
        with open(GOLDEN_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
            
        save_completed_id(email_id)
        print(f" -> Successfully Refined {email_id}.")

async def main():
    if not os.path.exists(RAW_FILE):
        print("Raw dataset JSONL not found. Run mass_ingestion.py first.")
        return
        
    completed_ids = get_completed_ids()
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    tasks = []
    
    print("Starting Semantic Refiner (Background Process)...")
    
    with open(RAW_FILE, "r") as f:
        for line in f:
            if not line.strip(): continue
            entry = json.loads(line)
            email_id = str(entry.get("id"))
            
            if email_id in completed_ids: continue
            
            task = asyncio.create_task(process_entry(entry, semaphore))
            tasks.append(task)
            
            if len(tasks) >= 20:
                await asyncio.gather(*tasks)
                tasks = []
                
    if tasks:
        await asyncio.gather(*tasks)
        
    print("All available raw emails have been semantically refined!")

if __name__ == "__main__":
    asyncio.run(main())
