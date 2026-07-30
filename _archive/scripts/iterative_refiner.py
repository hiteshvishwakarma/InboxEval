import json
import os
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv(dotenv_path="../web/.env.local")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

def generate_synthetic_email(prompt):
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating email: {e}")
        return ""

def semantic_debate_eval(human_email, synthetic_email):
    eval_prompt = f"""You are an elite semantic analyzer.
Compare these two emails:

[ORIGINAL HUMAN EMAIL]
{human_email}

[SYNTHETIC AI EMAIL]
{synthetic_email}

Task: Find the exact differences in Tone, Formality, Length, and Intent. 
Output your analysis in two parts:
1. [SCORE]: A number from 0 to 10 on how perfectly the Synthetic email captures the EXACT vibe of the Human email.
2. [FEEDBACK]: A 2-sentence instruction on how to change the prompt to make the next synthetic email closer to the original.
"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": eval_prompt}],
            temperature=0.1,
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        return "[SCORE]: 0\n[FEEDBACK]: Error"

def refine_prompt(old_prompt, feedback):
    refine_prompt = f"""You are an expert prompt engineer, but you must act like a normal human manager or employee sending a task to a colleague. 
Here is an old prompt used to generate an email:
"{old_prompt}"

Here is the feedback on why the generated email failed to match the target human vibe:
"{feedback}"

Rewrite the prompt to completely fix these issues. 
CRITICAL RULE: The new prompt MUST sound like a real human wrote it. 
- DO NOT use AI-speak like "Output exactly in this format" or "Do not include conversational text". 
- Instead, use human phrasing like "just give me the list, I don't need an essay" or "keep it super brief".
- It can be slightly informal or messy, just like a real human typing an email request.

Return ONLY the new prompt text. Do not include any other text.
"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": refine_prompt}],
            temperature=0.7, # Higher temp for more human variance
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        return old_prompt

def run_test():
    print("--- BATCH ITERATIVE PID LOOP TEST (IDs 0-4) ---")
    
    dataset_path = "../data/golden_dataset.json"
    if not os.path.exists(dataset_path):
        print("Dataset not found.")
        return
        
    with open(dataset_path, "r") as f:
        data = json.load(f)
        
    if not data: return
    
    for i in range(min(5, len(data))):
        print(f"\n======================================")
        print(f"PROCESSING EMAIL ID: {data[i].get('id', i)}")
        print(f"======================================")
        
        test_case = data[i]
        human_email = test_case.get("emails_to_grade", [{}])[0].get("email_text", "Could not find original.")
        v1_prompt = test_case.get("prompt", "")
        
        print(f"\n[ORIGINAL HUMAN EMAIL]\n{human_email[:200]}...")
        print(f"\n[V1 PROMPT (From reverse engineering)]\n{v1_prompt[:200]}...")
        
        v1_email = generate_synthetic_email(v1_prompt)
        v1_eval = semantic_debate_eval(human_email, v1_email)
        
        score_v1 = v1_eval.split("[SCORE]:")[-1].split("\\n")[0][:5].strip() if "[SCORE]:" in v1_eval else "0"
        print(f"\n[V1 SCORE]: {score_v1}")
        
        feedback = v1_eval.split("[FEEDBACK]:")[-1].strip() if "[FEEDBACK]:" in v1_eval else ""
        
        v2_prompt = refine_prompt(v1_prompt, feedback)
        print(f"\n[V2 PROMPT (Humanized Refinement)]\n{v2_prompt}")
        
        v2_email = generate_synthetic_email(v2_prompt)
        v2_eval = semantic_debate_eval(human_email, v2_email)
        
        score_v2 = v2_eval.split("[SCORE]:")[-1].split("\\n")[0][:5].strip() if "[SCORE]:" in v2_eval else "0"
        print(f"\n[V2 SCORE]: {score_v2}")
        
        time.sleep(2) # Prevent Groq rate limiting

if __name__ == "__main__":
    run_test()
