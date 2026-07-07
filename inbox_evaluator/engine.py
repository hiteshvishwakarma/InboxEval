import json
import os
import time
from static_evals import StaticEvaluator
from dynamic_evals import DynamicEvaluator

class Engine:
    """
    The orchestrator that runs the full evaluation suite against the Golden Dataset.
    """
    def __init__(self):
        self.static_eval = StaticEvaluator()
        self.dynamic_eval = DynamicEvaluator()
        
    def run_calibration(self, dataset_path: str, output_path: str = None):
        """
        Runs the Evaluator against the dataset and compares scores.
        """
        with open(dataset_path, "r") as f:
            dataset = json.load(f)
            
        print(f"Loaded Golden Dataset with {len(dataset)} prompts.")
        
        results = []
        
        # Run across all prompts in the dataset
        test_subset = dataset
        
        for item in test_subset:
            print(f"\nEvaluating Prompt ID: {item['id']}")
            print("-" * 40)
            
            prompt_res = {
                "id": item["id"],
                "prompt": item["prompt"],
                "evaluations": []
            }
            
            for email_case in item["emails_to_grade"]:
                print(f"Testing Case: {email_case['type']}")
                
                # 1. Run Static Evaluator
                static_scores = self.static_eval.evaluate(email_case["email_text"])
                
                # 2. Run Dynamic Evaluator
                print("  Running LLM-as-a-Judge (Gemini Pro)...")
                dynamic_scores = self.dynamic_eval.evaluate(
                    original_instruction=item["prompt"],
                    context=item["context"],
                    target_persona=item["target_persona"],
                    generated_email=email_case["email_text"]
                )
                
                # 3. Calculate Delta (Engine Score - Human Score)
                # Positive delta means AI graded too high. Negative means AI graded too low.
                expected = email_case["expected_scores"]
                deltas = {}
                
                if "error" not in dynamic_scores:
                    for param, human_score in expected.items():
                        ai_score = dynamic_scores.get(param, 0)
                        deltas[param] = ai_score - human_score
                        
                case_result = {
                    "type": email_case["type"],
                    "static_results": static_scores,
                    "human_expected": expected,
                    "ai_judge_scores": dynamic_scores,
                    "calibration_deltas": deltas
                }
                prompt_res["evaluations"].append(case_result)
                
                print("  Done.")
                time.sleep(2) # Rate limit protection
                
            results.append(prompt_res)
            
        if output_path:
            with open(output_path, "w") as f:
                json.dump(results, f, indent=4)
            print(f"\nCalibration results saved to {output_path}")
            
        return results
        
if __name__ == "__main__":
    engine = Engine()
    dataset_file = "../data/golden_dataset.json"
    output_file = "../data/calibration_results.json"
    
    if os.path.exists(dataset_file):
        print("Starting Evaluator Engine...")
        results = engine.run_calibration(dataset_file, output_file)
        
        # Print a quick summary of the deltas for the first email
        first_eval = results[0]["evaluations"][0]
        print(f"\n=== CALIBRATION SUMMARY FOR '{first_eval['type']}' ===")
        print("Parameter | Human | AI | Delta (AI - Human)")
        print("-" * 50)
        
        if "error" not in first_eval["ai_judge_scores"]:
            for param, delta in first_eval["calibration_deltas"].items():
                human = first_eval["human_expected"][param]
                ai = first_eval["ai_judge_scores"].get(param, 0)
                # Highlight large discrepancies (off by more than 2)
                flag = " 🚩" if abs(delta) > 2 else ""
                print(f"{param.ljust(22)} | {str(human).rjust(5)} | {str(ai).rjust(2)} | {str(delta).rjust(5)}{flag}")
            
            print(f"\nAI Reasoning: {first_eval['ai_judge_scores'].get('reasoning', '')}")
        else:
            print(first_eval["ai_judge_scores"])
            
    else:
        print(f"Dataset not found at {dataset_file}")
