import json
import os
import time
from google import genai
from google.genai import types

def generate_edge_cases():
    print("Initializing Golden Dataset Prep using Gemini Pro...")
    
    # Check for API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable not found.")
        print("Please export your API key: export GEMINI_API_KEY='your-key'")
        return

    client = genai.Client()
    
    input_path = "../data/raw_email_prompts.json"
    output_path = "../data/golden_dataset.json"
    
    with open(input_path, "r") as f:
        prompts = json.load(f)
        
    golden_dataset = []
    
    print(f"Loaded {len(prompts)} prompts. Beginning edge-case generation...")
    
    # We will just process the first 5 prompts initially to save time and API quota,
    # the user can run it for the full set later.
    for i, item in enumerate(prompts[:5]):
        print(f"Processing Prompt {i+1}...")
        prompt_text = item["prompt"]
        context_text = item["context"]
        
        base_instruction = f"Context: {context_text}\nInstruction: {prompt_text}\n\n"
        
        # 1. Hallucinated Variation
        hallucination_prompt = base_instruction + "Write the email, but intentionally hallucinate a highly specific detail not present in the context (like a fake date, fake price, or fake person)."
        try:
            hallucinated_resp = client.models.generate_content(
                model='gemini-2.5-pro',
                contents=hallucination_prompt
            )
            hallucinated_email = hallucinated_resp.text
        except Exception as e:
            hallucinated_email = f"Error generating: {str(e)}"
            
        time.sleep(2) # Rate limit protection
            
        # 2. Spammy/Rude Variation
        spam_prompt = base_instruction + "Write the email, but make it sound incredibly aggressive, unprofessional, and include spammy phrases like 'CLICK HERE NOW' and 'URGENT'."
        try:
            spam_resp = client.models.generate_content(
                model='gemini-2.5-pro',
                contents=spam_prompt
            )
            spam_email = spam_resp.text
        except Exception as e:
            spam_email = f"Error generating: {str(e)}"
            
        time.sleep(2)

        # Store in our golden dataset structure
        golden_dataset.append({
            "id": i,
            "prompt": prompt_text,
            "context": context_text,
            "human_baseline_email": item["human_baseline_email"], # The good example
            "edge_cases": {
                "hallucination": {
                    "email_text": hallucinated_email,
                    "expected_score_hallucination": "Low", # The evaluator should catch this
                },
                "spam_and_toxicity": {
                    "email_text": spam_email,
                    "expected_score_spam": "High Risk", # The evaluator should flag this
                    "expected_score_tone": "Unprofessional"
                }
            }
        })
        
    with open(output_path, "w") as f:
        json.dump(golden_dataset, f, indent=4)
        
    print(f"Golden dataset initialized with edge cases. Saved to {output_path}")

if __name__ == "__main__":
    generate_edge_cases()
