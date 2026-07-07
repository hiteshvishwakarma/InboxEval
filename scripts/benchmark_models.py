import os
import json
import time
import sys
from groq import Groq
from dotenv import load_dotenv

# Add parent dir to path so we can import our evaluator
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from inbox_evaluator.dynamic_evals import DynamicEvaluator

load_dotenv(dotenv_path="../.env")
api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=api_key)

# We will benchmark these 3 models against each other
MODELS_TO_BENCHMARK = [
    "llama-3.1-8b-instant",
    "qwen/qwen3-32b",
    "meta-llama/llama-4-scout-17b-16e-instruct"
]

def generate_email(model_name: str, instruction: str) -> str:
    prompt = f"Write an email based on the following instruction:\n\n{instruction}\n\nOutput ONLY the email text. Do not include any conversational filler before or after the email."
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a highly capable AI email assistant. Output only the email itself."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating with {model_name}: {e}")
        return ""

def run_benchmark():
    print("Loading Golden Dataset Prompts...")
    with open("../data/golden_dataset.json", "r") as f:
        dataset = json.load(f)
        
    evaluator = DynamicEvaluator()
    
    # To bypass the 100k TPD limit on Llama 3.3 70B, we will temporarily 
    # upgrade the Evaluator Judge to Qwen3 32B which has a massive 500k TPD limit!
    evaluator.model_name = "qwen/qwen3-32b" 
    print(f"Using {evaluator.model_name} as the AI Judge (500k TPD limit)...")
    
    results = {}
    for model in MODELS_TO_BENCHMARK:
        results[model] = []
        
    for i, item in enumerate(dataset):
        instruction = item["prompt"]
        print(f"\n[{i+1}/{len(dataset)}] Benchmarking Prompt: {instruction[:50]}...")
        
        for model in MODELS_TO_BENCHMARK:
            print(f"  -> Generating with {model}...")
            generated_email = generate_email(model, instruction)
            time.sleep(2.5) # strict rate limit protection (30 RPM = 1 request every 2s)
            
            if not generated_email:
                continue
                
            print(f"  -> Grading {model}...")
            # We do NOT pass context or persona, letting the Judge auto-infer!
            scorecard = evaluator.evaluate(
                original_instruction=instruction,
                generated_email=generated_email
            )
            time.sleep(2.5) # strict rate limit protection
            
            results[model].append({
                "prompt_id": item["id"],
                "generated_email": generated_email,
                "scorecard": scorecard
            })
            
    # Calculate Leaderboard
    print("\n\n=== INBOXEVAL LEADERBOARD ===")
    
    leaderboard = []
    for model in MODELS_TO_BENCHMARK:
        if not results[model]:
            continue
            
        total_score = 0
        valid_evals = 0
        
        for eval_res in results[model]:
            scores = eval_res.get("scorecard", {})
            if "error" in scores:
                continue
            
            # Sum up all 12 parameters to get an average score for this email out of 10
            try:
                numeric_scores = [v for k, v in scores.items() if isinstance(v, (int, float))]
                if len(numeric_scores) > 0:
                    avg = sum(numeric_scores) / len(numeric_scores)
                    total_score += avg
                    valid_evals += 1
            except:
                pass
                
        if valid_evals > 0:
            final_avg = total_score / valid_evals
            leaderboard.append((model, final_avg))
            
    # Sort descending
    leaderboard.sort(key=lambda x: x[1], reverse=True)
    
    for rank, (model, score) in enumerate(leaderboard):
        print(f"#{rank+1} | {model.ljust(45)} | Score: {score:.2f}/10")
        
    # Save detailed results
    with open("../data/leaderboard_results.json", "w") as f:
        json.dump(results, f, indent=4)
    print("\nDetailed results saved to data/leaderboard_results.json")

if __name__ == "__main__":
    run_benchmark()
