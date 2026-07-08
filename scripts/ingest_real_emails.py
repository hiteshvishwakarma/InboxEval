import os
import json
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")
api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=api_key)

# We use Qwen3-32B because of its massive 500k TPD limit
MODEL = "qwen/qwen3-32b" 

FAMOUS_EMAILS = [
    {
        "id": 11,
        "author": "Steve Jobs",
        "description": "Steve Jobs internal memo about the Top 100 Apple retreat",
        "text": """Team,
We need to hold our Top 100 meeting soon. I want this to be the best one yet.
Here is what we need to focus on:
1. 2011 Strategy - who are we? 
2. Post PC era - Apple is the first company to get here.
3. Mobile devices are the future.
We need to tie all our products together so we further lock customers into our ecosystem.
Steve"""
    },
    {
        "id": 12,
        "author": "Elon Musk",
        "description": "Elon Musk's leaked email on Return to Office at Tesla",
        "text": """Anyone who wishes to do remote work must be in the office for a minimum (and I mean *minimum*) of 40 hours per week or depart Tesla. This is less than we ask of factory workers.
If there are particularly exceptional contributors for whom this is impossible, I will review and approve those exceptions directly.
Moreover, the 'office' must be a main Tesla office, not a remote branch office unrelated to the job duties.
Thanks,
Elon"""
    },
    {
        "id": 13,
        "author": "Mark Zuckerberg",
        "description": "Mark Zuckerberg's leaked memo demanding resignation",
        "text": """We recently had a leak in the press about our new product strategy. This is a betrayal of our trust. 
I am asking whoever leaked this to resign immediately. If you do not resign, we will find out who you are anyway, and you will be fired. 
We are building a culture of trust and rapid innovation. We cannot have people secretly undermining the company.
Mark"""
    }
]

def backtranslate_email(email_text):
    prompt = f"""
You are an expert at reverse-engineering AI prompts.
Read the following real-world email:
---
{email_text}
---
Generate the 'Original Instruction' that a user would have typed into an AI assistant to generate this exact email.
Return ONLY a valid JSON object matching this schema:
{{
    "prompt": "<The instruction to generate the email>",
    "context": "<Any background facts or context needed to write it>",
    "target_persona": "<The persona of the sender>"
}}
"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error backtranslating: {e}")
        return None

def generate_edge_cases(email_text):
    # For these famous emails, the real email IS the perfect Human Baseline.
    # In a full run, we would also generate a Spam and Hallucination case.
    return [
        {
            "case_type": "Human Baseline",
            "email_text": email_text,
            "human_scores": {
                "instruction_adherence": 10,
                "factual_accuracy": 10,
                "professionalism": 9,
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
    print("Starting Ingestion of Famous Real Emails (Synthetic Backtranslation)...")
    
    try:
        with open("../data/golden_dataset.json", "r") as f:
            dataset = json.load(f)
    except Exception as e:
        print(f"Could not load existing dataset: {e}")
        dataset = []
        
    for item in FAMOUS_EMAILS:
        print(f"\nProcessing: {item['description']}...")
        back_data = backtranslate_email(item['text'])
        time.sleep(2.5) # Rate limit protection
        
        if back_data:
            evaluations = generate_edge_cases(item['text'])
            
            dataset_entry = {
                "id": item['id'],
                "prompt": back_data['prompt'],
                "context": back_data['context'],
                "target_persona": back_data['target_persona'],
                "evaluations": evaluations
            }
            
            # Prevent duplicates if run multiple times
            if not any(d.get("id") == item["id"] for d in dataset):
                dataset.append(dataset_entry)
                print(f"  -> Successfully backtranslated! Prompt: '{back_data['prompt'][:50]}...'")
            else:
                print(f"  -> ID {item['id']} already exists in dataset. Skipping.")
                
    with open("../data/golden_dataset.json", "w") as f:
        json.dump(dataset, f, indent=4)
        
    print("\nDone! Famous emails have been successfully injected into the Golden Dataset.")

if __name__ == "__main__":
    run()
