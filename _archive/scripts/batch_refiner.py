import os
import json
import asyncio
import sqlite3
import re
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv(dotenv_path="../web/.env.local")

client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

RAW_FILE = "../data/raw_dataset.jsonl"
GOLDEN_FILE = "../data/golden_dataset.jsonl"
DB_FILE = "../data/inboxeval_cache.db"
CONCURRENCY_LIMIT = 3

# ---------------------------------------------------------
# DPBC (Dynamic Persona-Based Calibration) RAM Cache
# ---------------------------------------------------------
MEMORY_CACHE = {
    "completed_ids": set(),
    "persona_thresholds": {}
}

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS completed (email_id TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS persona_stats (
                    persona TEXT PRIMARY KEY,
                    total_score REAL,
                    count INTEGER
                 )''')
    
    # Load into memory cache (0ms latency lookup for the async loop)
    c.execute("SELECT email_id FROM completed")
    MEMORY_CACHE["completed_ids"] = set(row[0] for row in c.fetchall())
    
    c.execute("SELECT persona, total_score, count FROM persona_stats")
    for row in c.fetchall():
        persona, total, count = row
        MEMORY_CACHE["persona_thresholds"][persona] = total / count if count > 0 else 8.0
    conn.close()

def save_completed_id(email_id, persona, final_score):
    MEMORY_CACHE["completed_ids"].add(email_id)
    
    # Update running average in memory (exponential moving average for speed)
    if persona not in MEMORY_CACHE["persona_thresholds"]:
        MEMORY_CACHE["persona_thresholds"][persona] = final_score
    else:
        MEMORY_CACHE["persona_thresholds"][persona] = (MEMORY_CACHE["persona_thresholds"][persona] * 0.9) + (final_score * 0.1)

    # Async flush to SQLite (background safety)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO completed (email_id) VALUES (?)", (email_id,))
    c.execute('''INSERT INTO persona_stats (persona, total_score, count)
                 VALUES (?, ?, 1)
                 ON CONFLICT(persona) DO UPDATE SET
                 total_score = total_score + excluded.total_score,
                 count = count + 1''', (persona, final_score))
    conn.commit()
    conn.close()

# ---------------------------------------------------------
# Core AI Logic
# ---------------------------------------------------------
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

def extract_score(eval_text):
    match = re.search(r'\[SCORE\]:\s*([\d\.]+)', eval_text)
    if match:
        return float(match.group(1))
    return 0.0

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
        human_email = entry.get("emails_to_grade", [{}])[0].get("email_text", "")
        if not human_email: return
        
        # Determine Persona & Target Threshold (RAM Lookup - 0ms)
        persona = entry.get("taxonomy_category", "Generic")
        target_threshold = MEMORY_CACHE["persona_thresholds"].get(persona, 8.0)
        
        print(f"Refining ID: {email_id} | Persona: {persona} | Target Score: >= {target_threshold:.1f}")
        
        iteration = 0
        max_iterations = 3
        best_prompt = entry.get("prompt", "")
        best_score = 0
        current_prompt = best_prompt

        # The Closed-Loop PID Controller
        while iteration < max_iterations:
            synthetic_email = await generate_synthetic_email(current_prompt)
            eval_result = await semantic_debate_eval(human_email, synthetic_email)
            
            score = extract_score(eval_result)
            feedback = eval_result.split("[FEEDBACK]:")[-1].strip() if "[FEEDBACK]:" in eval_result else ""
            
            print(f"  [{email_id}] Iteration {iteration+1} | Score: {score}")
            
            if score >= target_threshold:
                best_prompt = current_prompt
                best_score = score
                print(f"  [{email_id}] PASSED DPBC Threshold!")
                break
                
            if score > best_score:
                best_score = score
                best_prompt = current_prompt
                
            # Feed delta back into input
            current_prompt = await refine_prompt(current_prompt, feedback)
            iteration += 1
            
        entry["prompt"] = best_prompt
        entry["dpbc_score"] = best_score
        entry["dpbc_threshold_used"] = target_threshold
        
        # O(1) Append to final Golden file
        with open(GOLDEN_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
            
        save_completed_id(email_id, persona, best_score)

async def main():
    if not os.path.exists(RAW_FILE):
        print("Raw dataset JSONL not found. Run mass_ingestion.py first.")
        return
        
    init_db() # Boot-up Caching
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    tasks = []
    
    print("Starting DPBC Semantic Refiner (Background Process)...")
    
    with open(RAW_FILE, "r") as f:
        for line in f:
            if not line.strip(): continue
            entry = json.loads(line)
            email_id = str(entry.get("id"))
            
            if email_id in MEMORY_CACHE["completed_ids"]: continue
            
            task = asyncio.create_task(process_entry(entry, semaphore))
            tasks.append(task)
            
            if len(tasks) >= 20:
                await asyncio.gather(*tasks)
                tasks = []
                
    if tasks:
        await asyncio.gather(*tasks)
        
    print("All available raw emails have been semantically refined via DPBC!")

if __name__ == "__main__":
    asyncio.run(main())
