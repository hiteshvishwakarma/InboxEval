import json
import os
import random
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv(dotenv_path="../web/.env.local")

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

AVAILABLE_MODELS = [
    "qwen/qwen3-32b",
    "llama-3.1-8b-instant",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "gemma2-9b-it"
]

JUDGE_MODEL = "llama-3.3-70b-versatile"  # High-intelligence model to simulate the human

ELO_K = 32

def calculate_elo(rating_a, rating_b, score_a):
    expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    new_a = rating_a + ELO_K * (score_a - expected_a)
    new_b = rating_b + ELO_K * ((1 - score_a) - (1 - expected_a))
    return new_a, new_b

def generate_email(prompt, model_id):
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating with {model_id}: {e}")
        return None

def simulate_human_vote(prompt, text_a, text_b):
    judge_prompt = f"""You are an exhausted corporate manager. You don't have time for AI jargon or robotic corporate speak.
You need to pick the email that sounds the most NATURAL, HUMAN, and DIRECT.

Original Context/Prompt: {prompt}

--- MODEL A ---
{text_a}

--- MODEL B ---
{text_b}

Evaluate both. Which one feels more like a real human wrote it? 
You must output EXACTLY one of these three strings and nothing else:
"A" if Model A is better.
"B" if Model B is better.
"Tie" if they are equally good or bad."""

    try:
        response = client.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[{"role": "user", "content": judge_prompt}],
            temperature=0.1,
            max_tokens=10
        )
        vote = response.choices[0].message.content.strip().replace('"', '')
        if vote in ["A", "B", "Tie"]:
            return vote
        return "Tie" # Fallback
    except Exception as e:
        print(f"Judge error: {e}")
        return "Tie"

def run_arena_bot(iterations=5):
    print("🤖 Booting AI-Simulated Human Arena Bot...")
    
    dataset_path = "../data/golden_dataset.json"
    elo_path = "../data/arena_elo.json"
    rlhf_path = "../data/arena_training_dataset.jsonl"
    
    with open(dataset_path, "r") as f:
        golden_data = json.load(f)
        
    elo_data = {}
    if os.path.exists(elo_path):
        with open(elo_path, "r") as f:
            elo_data = json.load(f)
            
    for i in range(iterations):
        print(f"\n--- Match {i+1}/{iterations} ---")
        
        # 1. Pick a random proprietary prompt
        scenario = random.choice(golden_data)
        prompt = scenario.get("prompt", "")
        
        if not prompt: continue
        
        # 2. Pick 2 random models
        models = random.sample(AVAILABLE_MODELS, 2)
        model_a, model_b = models[0], models[1]
        
        print(f"Summoning: {model_a} vs {model_b}")
        
        # 3. Generate outputs
        text_a = generate_email(prompt, model_a)
        text_b = generate_email(prompt, model_b)
        
        if not text_a or not text_b: continue
        
        # 4. Simulate the Human Vote
        print(f"🧠 Simulated Human (Judge: {JUDGE_MODEL}) is reading...")
        time.sleep(1) # Simulate think time
        vote = simulate_human_vote(prompt, text_a, text_b)
        print(f"🗳️  Vote Cast: {vote}")
        
        # 5. Update Elo
        if model_a not in elo_data: elo_data[model_a] = {"elo": 1000, "matches": 0}
        if model_b not in elo_data: elo_data[model_b] = {"elo": 1000, "matches": 0}
        
        score_a = 0.5
        if vote == "A": score_a = 1.0
        elif vote == "B": score_a = 0.0
        
        old_a = elo_data[model_a]["elo"]
        old_b = elo_data[model_b]["elo"]
        
        new_a, new_b = calculate_elo(old_a, old_b, score_a)
        
        elo_data[model_a]["elo"] = new_a
        elo_data[model_a]["matches"] += 1
        elo_data[model_b]["elo"] = new_b
        elo_data[model_b]["matches"] += 1
        
        print(f"📈 Elo Update:")
        print(f"   {model_a}: {old_a:.1f} -> {new_a:.1f}")
        print(f"   {model_b}: {old_b:.1f} -> {new_b:.1f}")
        
        # Save Elo
        with open(elo_path, "w") as f:
            json.dump(elo_data, f, indent=2)
            
        # Save RLHF Data
        approx_tokens = int((len(text_a) + len(text_b)) / 4)
        rlhf_record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "prompt": prompt,
            "model_a": model_a,
            "text_a": text_a,
            "model_b": model_b,
            "text_b": text_b,
            "winner": vote,
            "telemetry": {
                "time_to_vote_ms": random.randint(4000, 12000), # Simulated human read time
                "approx_tokens": approx_tokens,
                "simulated_by": JUDGE_MODEL
            }
        }
        
        with open(rlhf_path, "a") as f:
            f.write(json.dumps(rlhf_record) + "\n")

if __name__ == "__main__":
    # Run 5 simulated battles
    run_arena_bot(5)
