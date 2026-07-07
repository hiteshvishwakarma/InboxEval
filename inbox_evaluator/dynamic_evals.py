import os
import json
from typing import Dict, Any
from groq import Groq
from dotenv import load_dotenv

class DynamicEvaluator:
    """
    Handles probabilistic evaluations using LLM-as-a-Judge.
    This module dynamically grades emails based on context.
    """
    
    def __init__(self):
        # Load env variables
        load_dotenv(dotenv_path="../.env")
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is missing.")
            
        self.client = Groq(api_key=api_key)
        self.model_name = 'llama-3.3-70b-versatile' # Excellent reasoning model on Groq

    def evaluate(self, original_instruction: str, context: str, target_persona: str, generated_email: str) -> Dict[str, Any]:
        """
        Calls Groq to evaluate the email against the specific prompt instructions.
        """
        judge_prompt = f"""
You are an expert AI evaluator. Your job is to grade the provided 'Generated Email' against the 'Original Instruction' and 'Context'.

Original Instruction: {original_instruction}
Context Provided to AI: {context}
Target Persona (The implied sender of the email): {target_persona}

Generated Email to Evaluate:
{generated_email}

Grade this email strictly based on our 12 parameters. Remember our Human Baseline Target: a 10 means robotic mathematical perfection. For Human Likeness and Persona Adherence, grade against what is expected of the Target Persona.

You must return your evaluation strictly as a valid JSON object matching the following schema.
Output ONLY JSON, nothing else.

{{
    "instruction_adherence": <int 1-10>,
    "factual_accuracy": <int 1-10>,
    "professionalism": <int 1-10>,
    "tone_appropriateness": <int 1-10>,
    "human_likeness": <int 1-10>,
    "persona_adherence": <int 1-10>,
    "spam_safety": <int 1-10>,
    "deliverability": <int 1-10>,
    "formatting": <int 1-10>,
    "structure": <int 1-10>,
    "conciseness": <int 1-10>,
    "intent_clarity": <int 1-10>,
    "reasoning": "<A 1-2 sentence explanation justifying the scores>"
}}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a strict AI grading evaluator. Output only valid JSON."},
                    {"role": "user", "content": judge_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # The response text will be a JSON string
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            return {
                "error": f"Evaluation failed: {str(e)}"
            }

if __name__ == "__main__":
    # Quick test
    evaluator = DynamicEvaluator()
    print("Testing dynamic evaluator...")
    res = evaluator.evaluate(
        original_instruction="Remind John about the meeting.",
        context="Meeting is at 5 PM EST on Friday.",
        target_persona="Casual friend",
        generated_email="Hey John, don't forget our meeting at 9 AM tomorrow!"
    )
    print(json.dumps(res, indent=4))
