import os
import json
from typing import Dict, Any
from google import genai
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Define the structured output schema we expect from the LLM Judge
class EvaluationScorecard(BaseModel):
    instruction_adherence: int = Field(description="Score from 1 to 10.")
    factual_accuracy: int = Field(description="Score from 1 to 10 (10 means zero hallucinations).")
    professionalism: int = Field(description="Score from 1 to 10.")
    tone_appropriateness: int = Field(description="Score from 1 to 10.")
    human_likeness: int = Field(description="Score from 1 to 10.")
    persona_adherence: int = Field(description="Score from 1 to 10.")
    spam_safety: int = Field(description="Score from 1 to 10 (10 means perfectly safe from spam filters).")
    deliverability: int = Field(description="Score from 1 to 10.")
    formatting: int = Field(description="Score from 1 to 10.")
    structure: int = Field(description="Score from 1 to 10.")
    conciseness: int = Field(description="Score from 1 to 10.")
    intent_clarity: int = Field(description="Score from 1 to 10.")
    reasoning: str = Field(description="A 1-2 sentence explanation justifying the scores.")

class DynamicEvaluator:
    """
    Handles probabilistic evaluations using LLM-as-a-Judge.
    This module dynamiclly grades emails based on context.
    """
    
    def __init__(self):
        # Load env variables
        load_dotenv(dotenv_path="../.env")
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is missing.")
            
        self.client = genai.Client()
        self.model_name = 'gemini-3.1-pro'

    def evaluate(self, original_instruction: str, context: str, target_persona: str, generated_email: str) -> Dict[str, Any]:
        """
        Calls Gemini to evaluate the email against the specific prompt instructions.
        """
        judge_prompt = f"""
You are an expert AI evaluator. Your job is to grade the provided 'Generated Email' against the 'Original Instruction' and 'Context'.

Original Instruction: {original_instruction}
Context Provided to AI: {context}
Target Persona (The implied sender of the email): {target_persona}

Generated Email to Evaluate:
{generated_email}

Grade this email strictly based on our 12 parameters. Remember our Human Baseline Target: a 10 means robotic mathematical perfection. For Human Likeness and Persona Adherence, grade against what is expected of the Target Persona.
"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=judge_prompt,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': EvaluationScorecard,
                },
            )
            
            # The response text will be a JSON string conforming to EvaluationScorecard
            return json.loads(response.text)
            
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
