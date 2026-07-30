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
    "meta-llama/llama-4-scout-17b-16e-instruct"
]

JUDGE_MODEL = "llama-3.3-70b-versatile"  # High-intelligence model to simulate the human

ELO_K = 32

# The Constitutional AI Multi-Persona Emotive Matrix
CONSTITUTIONAL_MATRIX = [
    {
        "persona": "The Ruthless Executive",
        "principle": "You hate filler words, corporate fluff, and unnecessary pleasantries. You value emails that get straight to the point with maximum brevity and clarity."
    },
    {
        "persona": "The Empathetic HR Director",
        "principle": "You value emotional intelligence, soft tones, and psychological safety. You penalize emails that sound overly robotic, aggressive, or cold."
    },
    {
        "persona": "The Meticulous Legal Counsel",
        "principle": "You are anxious about compliance and factual accuracy. You value emails that are extremely precise, professional, and leave absolutely no room for misinterpretation."
    },
    {
        "persona": "The Chaotic Sales Rep",
        "principle": "You value high-energy, persuasive, and engaging language. You hate emails that are boring, overly formal, or lack a clear, exciting call-to-action."
    },
    {
        "persona": "The Overwhelmed Customer Support Lead",
        "principle": "You value extreme simplicity and step-by-step clarity. You penalize emails that use confusing jargon or make the reader think too hard to find the solution."
    }
]

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

def constitutional_critique_and_vote(prompt, text_a, text_b, emotion):
    # Step 1: The Critique (Chain of Thought)
    critique_prompt = f"""[SYSTEM PERSONA]
Persona: {emotion['persona']}
Guiding Principle: {emotion['principle']}

Original Email Prompt Context: {prompt}

--- MODEL A ---
{text_a}

--- MODEL B ---
{text_b}

[TASK 1: CRITIQUE]
Act strictly as your Persona. Read both emails. Write a brutal 2-sentence critique comparing how well Model A and Model B adhered to your specific Guiding Principle.

[TASK 2: VOTE]
Based ONLY on your critique and persona, declare the winner. End your response with exactly one of these strings on a new line:
[VOTE: A]
[VOTE: B]
[VOTE: Tie]"""

    try:
        response = client.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[{"role": "user", "content": critique_prompt}],
            temperature=0.3,
            max_tokens=200
        )
        full_response = response.choices[0].message.content.strip()
        
        # Parse the Vote
        vote = "Tie"
        if "[VOTE: A]" in full_response.upper(): vote = "A"
        elif "[VOTE: B]" in full_response.upper(): vote = "B"
        
        # Extract the Critique
        critique = full_response.split("[VOTE:")[0].strip()
        
        return vote, critique
    except Exception as e:
        print(f"Judge error: {e}")
        return "Tie", "Error generating critique"

def run_arena_bot(iterations=5):
    print("🤖 Booting Constitutional AI-Simulated Arena Bot...")
    
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
        
        scenario = random.choice(golden_data)
        prompt = scenario.get("prompt", "")
        if not prompt: continue
        
        models = random.sample(AVAILABLE_MODELS, 2)
        model_a, model_b = models[0], models[1]
        
        print(f"Summoning: {model_a} vs {model_b}")
        
        text_a = generate_email(prompt, model_a)
        text_b = generate_email(prompt, model_b)
        if not text_a or not text_b: continue
        
        # Inject the Constitutional Emotive Persona
        active_persona = random.choice(CONSTITUTIONAL_MATRIX)
        print(f"🧠 Simulated Human activated: {active_persona['persona']}")
        
        vote, critique = constitutional_critique_and_vote(prompt, text_a, text_b, active_persona)
        print(f"📝 Critique: {critique}")
        print(f"🗳️  Vote Cast: {vote}")
        
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
        
        with open(elo_path, "w") as f:
            json.dump(elo_data, f, indent=2)
            
        # Log RLHF Data with Constitutional Reasoning
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
                "simulated_by": JUDGE_MODEL,
                "persona": active_persona["persona"],
                "principle": active_persona["principle"],
                "critique": critique
            }
        }
        
        with open(rlhf_path, "a") as f:
            f.write(json.dumps(rlhf_record) + "\n")

if __name__ == "__main__":
    run_arena_bot(3)
