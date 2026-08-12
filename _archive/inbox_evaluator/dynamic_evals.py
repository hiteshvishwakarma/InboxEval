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

    def _infer_context_and_persona(self, instruction: str) -> tuple:
        """
        If the user does not provide context or persona, we infer it directly from the prompt.
        """
        infer_prompt = f"""
Analyze the following instruction for an email.
Instruction: "{instruction}"

Extract the implied 'Context' (the background scenario) and the implied 'Target Persona' (who is writing the email, e.g. 'A professional PM', 'A casual friend').
Return ONLY a valid JSON object matching this schema:
{{
    "inferred_context": "<string>",
    "inferred_persona": "<string>"
}}
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. Output only JSON."},
                    {"role": "user", "content": infer_prompt}
                ],
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            return data.get("inferred_context", "General Context"), data.get("inferred_persona", "General User")
        except:
            return "General context inferred from prompt.", "General User"

    def evaluate(self, original_instruction: str, generated_email: str, context: str = None, target_persona: str = None) -> Dict[str, Any]:
        """
        Calls Groq to evaluate the email against the specific prompt instructions.
        """
        if not context or not target_persona:
            inferred_context, inferred_persona = self._infer_context_and_persona(original_instruction)
            context = context or inferred_context
            target_persona = target_persona or inferred_persona

        judge_prompt = f"""
You are an expert AI evaluator. Your job is to grade the provided 'Generated Email' against the 'Original Instruction' and 'Context'.

Original Instruction: {original_instruction}
Context Provided to AI: {context}
Target Persona (The implied sender of the email): {target_persona}

Generated Email to Evaluate:
{generated_email}

Grade this email strictly based on our 12 parameters. Remember our Human Baseline Target: a 10 means perfect calibration to human expectations.

CRITICAL GRADING CALIBRATION RULES:
1. Human Likeness & Structure: Humans are often terse, informal, or use lists. Do not penalize an email for lacking conversational filler or a traditional greeting/sign-off if the context implies a brief response.
2. Professionalism & Tone: Do not expect formal, corporate language if the Target Persona is casual (e.g., a friend, or talking to a pet). Professionalism means matching the appropriate tone for the scenario.
3. Intent Clarity: Do not expect the intent to be explicitly spelled out (e.g., "The purpose of this email is..."). Recognize human subtext.
4. Formatting: Penalize clunky or overly-dense formatting. AI-generated blocks are often too perfect; humans use simple, breathable formatting.
5. Deliverability & Spam: Be extremely harsh on spam edge cases. Assume promotional triggers will immediately block the email.
6. Instruction Adherence: Be strict. If the email hallucinates details not in the context, penalize instruction adherence heavily.

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
        original_instruction="Remind John about the meeting. It's at 5 PM EST on Friday.",
        generated_email="Hey John, don't forget our meeting at 9 AM tomorrow!"
    )
    print(json.dumps(res, indent=4))
