import os
import asyncio
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv(dotenv_path="../web/.env.local")
client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

RAW_EMAIL = """
To Whom It May Concern,
I have been waiting for my refund for THREE WEEKS. This is completely unacceptable and frankly, it's theft. If I do not see the money in my account by tomorrow, I am filing a chargeback and canceling my subscription permanently.
Fix this immediately.
- Mark
"""

async def evidence_based_classifier(email_text):
    prompt = f"""You are an elite linguistic classifier. Analyze this email and output a JSON profile.
EMAIL: {email_text}

Extract the following:
1. "domain": The professional domain (e.g., B2C Customer Support, Corporate M&A, Internal HR).
2. "sentiment": The emotional state (e.g., Angry, Anxious, Professional, Neutral).
3. "evidence": A direct quote or linguistic trait from the email that PROVES the sentiment.
4. "persona_tag": A combined string (e.g., "b2c_support_angry")

Output ONLY raw valid JSON."""
    
    res = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=200,
        response_format={"type": "json_object"}
    )
    return res.choices[0].message.content

async def main():
    print("=== ADP STEP 3: PROTOTYPING EVIDENCE-BASED PERSONA CLASSIFIER ===")
    print("Analyzing Raw Email...")
    
    classification_json = await evidence_based_classifier(RAW_EMAIL)
    print("\n[EVIDENCE-BASED PERSONA PROFILE]:")
    print(classification_json)

if __name__ == "__main__":
    asyncio.run(main())
