import random
import time

def print_step(step_num, title):
    print(f"\n[{'='*10} STEP {step_num}: {title} {'='*10}]")

class PipelineAPrototype:
    def __init__(self):
        self.generation = 0
        self.historical_db = {
            "Angry_Customer_Support": {"tone": 6.5, "conciseness": 7.0, "accuracy": 9.0}
        }
        self.reigning_champion = None
        self.early_stop_counter = 0
        self.last_elo = 0

    def step_1_ingestion(self):
        print_step(1, "Raw Ingestion")
        email = "Where the hell is my refund? It's been 3 weeks. Fix this now."
        print(f"Ingested E_human: '{email}'")
        return email

    def step_2_3_vectorization_dpbc(self, email):
        print_step("2 & 3", "Persona Extraction & DPBC Vector Lookup")
        persona = "Angry_Customer_Support"
        print(f"Extracted Persona: {persona}")
        dpbc_thresholds = self.historical_db[persona]
        print(f"KNN Vector Lookup DPBC Thresholds: {dpbc_thresholds}")
        return dpbc_thresholds

    def step_4_5_genesis(self):
        print_step("4 & 5", "Base Prompt & Persona-Augmented Mutations (Prompt Jitter)")
        matrix = ["The Minimalist", "The Over-Explainer", "The Executive", "The Structuralist", "The Non-Native"]
        prompts = []
        for i, p in enumerate(matrix):
            prompts.append({"id": f"P{i+1}", "style": p, "text": f"[{p}] write refund email angry"})
            print(f"Generated Mutation {i+1} via '{p}' Persona")
        return prompts

    def step_6_7_isolated_eval_kda(self, prompts, dpbc):
        print_step("6 & 7", "Isolated Eval, N-Way Ranking & KDA Matrix")
        evaluations = []
        for p in prompts:
            # Mocking the LLM Judge evaluating synthetic emails
            tone = random.uniform(5.0, 9.0)
            conc = random.uniform(5.0, 9.0)
            acc = random.uniform(5.0, 9.0)
            overall = (tone + conc + acc) / 3
            evaluations.append({
                "id": p["id"],
                "style": p["style"],
                "tone": round(tone, 1),
                "conciseness": round(conc, 1),
                "accuracy": round(acc, 1),
                "overall": round(overall, 1)
            })
        
        # Sort by overall to rank 1-5
        evaluations.sort(key=lambda x: x["overall"], reverse=True)
        print("--- OVERALL RANKING ---")
        for i, e in enumerate(evaluations):
            print(f"Rank {i+1}: {e['id']} ({e['style']}) - Overall: {e['overall']} [Tone: {e['tone']}, Conc: {e['conciseness']}, Acc: {e['accuracy']}]")
        
        # KDA Matrix Extraction (Polygenic)
        best_tone = max(evaluations, key=lambda x: x["tone"])
        best_conc = max(evaluations, key=lambda x: x["conciseness"])
        best_acc = max(evaluations, key=lambda x: x["accuracy"])
        
        print("\n--- KDA MATRIX (PARAMETER WINNERS) ---")
        print(f"Best Tone: {best_tone['id']} ({best_tone['tone']})")
        print(f"Best Conciseness: {best_conc['id']} ({best_conc['conciseness']})")
        print(f"Best Accuracy: {best_acc['id']} ({best_acc['accuracy']})")
        
        return evaluations, best_tone, best_conc, best_acc

    def step_8_9_feedback_polygenic(self, evaluations, best_tone, best_conc, best_acc):
        print_step("8 & 9", "Feedback Loop & Polygenic Crossover")
        overall_winner = evaluations[0]
        print(f"Feedback: {overall_winner['id']} won overall, but failed to hit DPBC Tone threshold. Extracting Tone instructions from {best_tone['id']}...")
        
        super_prompt = {
            "id": f"Super_P_Gen_{self.generation+1}",
            "base": overall_winner["style"],
            "polygenic_traits": f"Tone from {best_tone['id']}, Conciseness from {best_conc['id']}"
        }
        print(f"Bred Super Prompt: {super_prompt}")
        return super_prompt, overall_winner["overall"]

    def step_10_11_elitism_early_stop(self, super_prompt, overall_score, dpbc):
        print_step("10 & 11", "Elitism & Plateau Detection")
        if self.reigning_champion is None or overall_score > self.last_elo:
            self.reigning_champion = super_prompt
            print(f"New Reigning Champion Crowned! Elo: {overall_score}")
            self.early_stop_counter = 0
        else:
            print(f"Super Prompt failed to beat Champion. Elitism kicks in: Champion retained.")
            self.early_stop_counter += 1
            
        self.last_elo = max(self.last_elo, overall_score)
        
        # Check DPBC victory
        if self.last_elo >= 8.5:
            print(f">>> SUCCESS: DPBC Thresholds Crossed! (Score: {self.last_elo})")
            return True
            
        if self.early_stop_counter >= 2:
            print(f">>> EARLY STOP TRIGGERED: Linear plateau detected over 2 generations. Halting to save resources.")
            return True
            
        return False

    def run(self):
        print("INITIALIZING PIPELINE A PROTOTYPE...")
        time.sleep(1)
        email = self.step_1_ingestion()
        dpbc = self.step_2_3_vectorization_dpbc(email)
        
        while self.generation < 5: # Failsafe
            print(f"\n{'*'*20} STARTING GENERATION {self.generation} {'*'*20}")
            prompts = self.step_4_5_genesis()
            evals, best_tone, best_conc, best_acc = self.step_6_7_isolated_eval_kda(prompts, dpbc)
            super_prompt, score = self.step_8_9_feedback_polygenic(evals, best_tone, best_conc, best_acc)
            
            done = self.step_10_11_elitism_early_stop(super_prompt, score, dpbc)
            if done:
                break
                
            self.generation += 1

        print_step(12, "Commit to Golden Dataset")
        print(f"Saved E_human and Reigning Champion {self.reigning_champion['id']} to golden_dataset.jsonl")

if __name__ == "__main__":
    p = PipelineAPrototype()
    p.run()
