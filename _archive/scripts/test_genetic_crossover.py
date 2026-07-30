import os
import asyncio
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv(dotenv_path="../web/.env.local")
client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

# Mock Data for Prototyping
TARGET_HUMAN_EMAIL = """
Hi Team,
Just a quick reminder that tomorrow's standup is moved to 10:30 AM EST. Please come prepared with your blockers.
Best,
Alex
"""

# The Genesis Prompts
# Prompt A has great intent/details, but is too robotic.
# Prompt B has great tone (casual), but misses the specific time zone and blockers requirement.
prompt_A = "Write a highly detailed and professional corporate email to the team stating that the standup meeting for tomorrow has been rescheduled to exactly 10:30 AM EST, and mandate that all participants bring their blockers."
prompt_B = "Draft a quick, casual heads up to the team saying tomorrow's meeting is pushed to 10:30. Sign it as Alex."

async def generate_email(prompt_text):
    res = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt_text}],
        temperature=0.3,
        max_tokens=150
    )
    return res.choices[0].message.content

async def parameter_judge(email_a, email_b, target):
    prompt = f"""You are an elite judge. Compare Email A and Email B against the Target Human Email.
TARGET: {target}
---
EMAIL A: {email_a}
---
EMAIL B: {email_b}
---
Evaluate on 3 Parameters: Overall Winner, Best Tone, Best Details.
Output EXACTLY in this format:
OVERALL: [A or B]
TONE: [A or B]
DETAILS: [A or B]"""
    res = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=50
    )
    return res.choices[0].message.content.strip()

async def genetic_crossover(prompt_a, prompt_b, scorecard):
    prompt = f"""You are a genetic algorithm performing Crossover on two prompts.
PROMPT A: "{prompt_a}"
PROMPT B: "{prompt_b}"

The Judge's Scorecard:
{scorecard}

Task: Combine the best parts of both prompts based on the scorecard. If Prompt A won "Details", extract its detailed constraints. If Prompt B won "Tone", extract its style constraints.
Return ONLY the new 'Super Prompt' text that inherits the winning traits of both."""
    res = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=150
    )
    return res.choices[0].message.content.strip()

async def main():
    print("=== ADP STEP 3: PROTOTYPING GENETIC CROSSOVER & KDA ELO ===")
    
    print(f"Generating Email A (Detail Heavy, Bad Tone)...")
    email_a = await generate_email(prompt_A)
    print(f"Generating Email B (Good Tone, Missing Details)...")
    email_b = await generate_email(prompt_B)
    
    print("Judging Parameter-Specific Battle (KDA)...")
    scorecard = await parameter_judge(email_a, email_b, TARGET_HUMAN_EMAIL)
    print(f"\n--- SCORECARD ---\n{scorecard}\n-----------------")
    
    print("Executing Genetic Crossover...")
    super_prompt = await genetic_crossover(prompt_A, prompt_B, scorecard)
    print(f"\n[NEW SUPER PROMPT]:\n{super_prompt}")

if __name__ == "__main__":
    asyncio.run(main())
