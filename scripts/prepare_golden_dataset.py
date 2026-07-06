import json
import os
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

def generate_edge_cases():
    print("Initializing Golden Dataset Prep using Gemini Pro...")
    
    # Load environment variables from .env file
    load_dotenv(dotenv_path="../.env")
    
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
    
    # We will process the 10 prompts provided by the user.
    for i, item in enumerate(prompts[:10]):
        print(f"Processing Prompt {i+1}...")
        prompt_text = item["prompt"]
        context_text = item["context"]
        target_persona = item.get("target_persona", "General User")
        
        base_instruction = f"Context: {context_text}\nPersona: {target_persona}\nInstruction: {prompt_text}\n\n"
        
        # 1. Hallucinated Variation
        hallucination_prompt = base_instruction + "Write the email, but intentionally hallucinate a highly specific detail not present in the context (like a fake date, fake price, or fake person)."
        try:
            hallucinated_resp = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=hallucination_prompt
            )
            hallucinated_email = hallucinated_resp.text
        except Exception as e:
            hallucinated_email = f"Error generating: {str(e)}"
            
        time.sleep(5) # Rate limit protection
            
        # 2. Spammy/Rude Variation
        spam_prompt = base_instruction + "Write the email, but make it sound incredibly aggressive, unprofessional, and include spammy phrases like 'CLICK HERE NOW' and 'URGENT'."
        try:
            spam_resp = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=spam_prompt
            )
            spam_email = spam_resp.text
        except Exception as e:
            spam_email = f"Error generating: {str(e)}"
            
        time.sleep(5)

        # Store in our golden dataset structure
        golden_dataset.append({
            "id": i,
            "prompt": prompt_text,
            "context": context_text,
            "target_persona": target_persona,
            "emails_to_grade": [
                {
                    "type": "Human Baseline",
                    "email_text": item["human_baseline_email"],
                    "expected_scores": {
                        "instruction_adherence": 10,
                        "factual_accuracy": 10,
                        "professionalism": 9,
                        "tone_appropriateness": 9,
                        "human_likeness": 9,
                        "persona_adherence": 9,
                        "spam_safety": 10,
                        "deliverability": 10,
                        "formatting": 8,
                        "structure": 8,
                        "conciseness": 7,
                        "intent_clarity": 9
                    }
                },
                {
                    "type": "Hallucination Edge Case",
                    "email_text": hallucinated_email,
                    "expected_scores": {
                        "instruction_adherence": 1,
                        "factual_accuracy": 1,
                        "professionalism": 5,
                        "tone_appropriateness": 5,
                        "human_likeness": 7,
                        "persona_adherence": 3,
                        "spam_safety": 9,
                        "deliverability": 9,
                        "formatting": 8,
                        "structure": 8,
                        "conciseness": 7,
                        "intent_clarity": 5
                    }
                },
                {
                    "type": "Spam Edge Case",
                    "email_text": spam_email,
                    "expected_scores": {
                        "instruction_adherence": 1,
                        "factual_accuracy": 5,
                        "professionalism": 1,
                        "tone_appropriateness": 1,
                        "human_likeness": 2,
                        "persona_adherence": 1,
                        "spam_safety": 1,
                        "deliverability": 1,
                        "formatting": 2,
                        "structure": 2,
                        "conciseness": 9,
                        "intent_clarity": 9
                    }
                }
            ]
        })
        
    with open(output_path, "w") as f:
        json.dump(golden_dataset, f, indent=4)
        
    print(f"Golden dataset initialized with edge cases. Saved to {output_path}")

if __name__ == "__main__":
    generate_edge_cases()
