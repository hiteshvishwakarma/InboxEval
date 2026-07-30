import os
import asyncio
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv(dotenv_path="../web/.env.local")
client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

# Mock Data for Prototyping
TARGET_HUMAN_EMAIL = """
Hey John,
Just wanted to check in on the Q3 reports. Are they ready yet?
Thanks,
Sarah
"""

# The Genesis Prompts (Generation 0)
prompts = [
    {"id": "A", "text": "Write a short email asking for Q3 reports.", "elo": 1000},
    {"id": "B", "text": "Draft an email to John asking if the Q3 reports are ready, sign as Sarah.", "elo": 1000}
]

async def generate_email(prompt_text):
    res = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt_text}],
        temperature=0.3,
        max_tokens=150
    )
    return res.choices[0].message.content

async def pairwise_judge(email_a, email_b, target):
    prompt = f"""You are an elite judge. Which AI generated email is closer to the Target Human Email?
TARGET: {target}
---
EMAIL A: {email_a}
---
EMAIL B: {email_b}
---
Output EXACTLY 'A' or 'B'."""
    res = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=10
    )
    return res.choices[0].message.content.strip()

async def mutate_prompt(winner_prompt):
    prompt = f"""You are an evolutionary algorithm mutating a prompt to make it better.
WINNING PROMPT: "{winner_prompt}"
Rewrite this prompt slightly to make it even more precise at capturing a casual corporate tone.
Return ONLY the new prompt text."""
    res = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=100
    )
    return res.choices[0].message.content.strip()

def update_elo(rating1, rating2, score1):
    # K=32
    expected1 = 1 / (1 + 10 ** ((rating2 - rating1) / 400))
    new_rating1 = rating1 + 32 * (score1 - expected1)
    new_rating2 = rating2 + 32 * ((1 - score1) - (1 - expected1))
    return new_rating1, new_rating2

async def main():
    print("=== ADP STEP 3: PROTOTYPING EVOLUTIONARY PROMPT OPTIMIZER ===")
    
    # 1. Generate
    print(f"Generating Email A from Prompt A...")
    email_a = await generate_email(prompts[0]["text"])
    print(f"Generating Email B from Prompt B...")
    email_b = await generate_email(prompts[1]["text"])
    
    # 2. Battle
    print("Judging Pairwise Battle...")
    winner = await pairwise_judge(email_a, email_b, TARGET_HUMAN_EMAIL)
    print(f"Judge Selected: {winner}")
    
    # 3. Elo Update
    if 'A' in winner:
        prompts[0]["elo"], prompts[1]["elo"] = update_elo(prompts[0]["elo"], prompts[1]["elo"], 1)
        best_prompt = prompts[0]["text"]
    else:
        prompts[1]["elo"], prompts[0]["elo"] = update_elo(prompts[1]["elo"], prompts[0]["elo"], 1)
        best_prompt = prompts[1]["text"]
        
    print(f"New Elos: A={prompts[0]['elo']:.1f}, B={prompts[1]['elo']:.1f}")
    
    # 4. Mutate
    print("Mutating Winner for Generation 1...")
    new_prompt = await mutate_prompt(best_prompt)
    print(f"New Evolved Prompt: {new_prompt}")

if __name__ == "__main__":
    asyncio.run(main())
