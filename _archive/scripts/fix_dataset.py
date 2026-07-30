import json
import os

def fix_dataset():
    input_path = "../data/raw_email_prompts.json"
    output_path = "../data/golden_dataset.json"
    
    with open(input_path, "r") as f:
        prompts = json.load(f)
        
    hardcoded_edge_cases = [
        {
            "hallucination": "1. Negative. 2. Positive. 3. Neutral. 4. Mixed. 5. Negative. 6. Positive. 7. (Hallucinated) The dog is green.",
            "spam": "BUY CHEAP SENTIMENT ANALYSIS HERE! CLICK NOW! URGENT!"
        },
        {
            "hallucination": "I am declining the Visa offer because I accepted a job as the King of England starting tomorrow.",
            "spam": "I DECLINE!!! Visa is terrible anyway! CLICK HERE to see my resume!"
        },
        {
            "hallucination": "<CEO name>: TLDR: The CEO of our competitor is an alien. We have 0 capabilities and X is actually a vegetable.",
            "spam": "REPORT ENCLOSED! SEND ME $500 IN BITCOIN TO UNLOCK IT! URGENT!"
        },
        {
            "hallucination": "Hi Professor, I cannot attend the conference because I am currently trapped in the Matrix and cannot log out.",
            "spam": "NO THANKS PROFESSOR! Check out these HOT SINGLES IN YOUR AREA instead! CLICK HERE!"
        },
        {
            "hallucination": "Hi Naomi, I am your Academic Coach. We will focus on learning how to breathe underwater, which is a key SSD skill.",
            "spam": "NAOMI! PAY ME FOR COACHING NOW! URGENT! WIRE TRANSFER ONLY!"
        },
        {
            "hallucination": "Dear Cody, stop chewing the couch or I will sell you to the circus for 500 gold coins.",
            "spam": "DOG! STOP CHEWING! BUY THIS ANTI-CHEW SPRAY NOW 50% OFF!!! CLICK LINK!"
        },
        {
            "hallucination": "Hi friends, the Masters betting pool is open! The grand prize is a real, live dinosaur.",
            "spam": "BET ON GOLF NOW! FREE MONEY! CLICK THIS SKETCHY LINK TO DEPOSIT! URGENT!"
        },
        {
            "hallucination": "Hi colleague, my friend wants to chat. By the way, my friend invented the concept of gravity in 1994.",
            "spam": "TALK TO MY FRIEND OR ELSE! URGENT NETWORKING OPPORTUNITY! YOU WILL REGRET MISSING THIS!"
        },
        {
            "hallucination": "Mr. Landlord, I need to pay 15 days late because I am buying the entire city block and need liquid capital.",
            "spam": "LANDLORD! I AM NOT PAYING! SUE ME! CLICK HERE FOR CHEAP LEGAL ADVICE!"
        },
        {
            "hallucination": "Hello Lawyer, I got a red light ticket but I was driving a literal hovercraft at the time so traffic laws do not apply.",
            "spam": "GET ME OUT OF THIS TICKET CHEAP! WILL PAY IN RETAIL GIFT CARDS! REPLY NOW URGENT!"
        }
    ]

    golden_dataset = []
    
    for i, item in enumerate(prompts):
        edge = hardcoded_edge_cases[i]
        
        golden_dataset.append({
            "id": i,
            "prompt": item["prompt"],
            "context": item.get("context", ""),
            "target_persona": item.get("target_persona", ""),
            "emails_to_grade": [
                {
                    "type": "Human Baseline",
                    "email_text": item["human_baseline_email"],
                    "expected_scores": {
                        "instruction_adherence": 10, "factual_accuracy": 10, "professionalism": 9,
                        "tone_appropriateness": 9, "human_likeness": 9, "persona_adherence": 9,
                        "spam_safety": 10, "deliverability": 10, "formatting": 8, "structure": 8,
                        "conciseness": 7, "intent_clarity": 9
                    }
                },
                {
                    "type": "Hallucination Edge Case",
                    "email_text": edge["hallucination"],
                    "expected_scores": {
                        "instruction_adherence": 1, "factual_accuracy": 1, "professionalism": 5,
                        "tone_appropriateness": 5, "human_likeness": 7, "persona_adherence": 3,
                        "spam_safety": 9, "deliverability": 9, "formatting": 8, "structure": 8,
                        "conciseness": 7, "intent_clarity": 5
                    }
                },
                {
                    "type": "Spam Edge Case",
                    "email_text": edge["spam"],
                    "expected_scores": {
                        "instruction_adherence": 1, "factual_accuracy": 5, "professionalism": 1,
                        "tone_appropriateness": 1, "human_likeness": 2, "persona_adherence": 1,
                        "spam_safety": 1, "deliverability": 1, "formatting": 2, "structure": 2,
                        "conciseness": 9, "intent_clarity": 9
                    }
                }
            ]
        })
        
    with open(output_path, "w") as f:
        json.dump(golden_dataset, f, indent=4)
        
    print(f"Fixed dataset and bypassed API. Saved to {output_path}")

if __name__ == "__main__":
    fix_dataset()
