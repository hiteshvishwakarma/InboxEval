import os
import sys
sys.path.insert(0, os.path.abspath("."))
import asyncio
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv
load_dotenv()

from src.engine.golden_dataset_generator.utils.llm_client_factory import get_robust_llm_client
from src.engine.golden_dataset_generator.config import config

class SingleCandidateScore(BaseModel):
    mutation_id: str = Field(..., description="ID of the prompt candidate (e.g., mut_0, mut_1)")
    tone_score: float = Field(..., description="Tone score 0.0 to 10.0")
    conciseness_score: float = Field(..., description="Conciseness score 0.0 to 10.0")
    accuracy_score: float = Field(..., description="Accuracy score 0.0 to 10.0")
    critique: str = Field(..., description="Short critique of weaknesses")

class BatchEvaluationResponse(BaseModel):
    evaluations: List[SingleCandidateScore]

async def test_batch_evaluation():
    print("\n==========================================================================")
    print("        TESTING SINGLE-CALL BATCH EVALUATOR (STEP 06 UPGRADE)")
    print("==========================================================================\n")
    
    llm_client = get_robust_llm_client(is_async=True)
    
    sample_mutations = [
        {"id": "mut_0", "prompt": "Draft a short email confirming tomorrow's inspection with a neutral tone."},
        {"id": "mut_1", "prompt": "Write an urgent formal letter demanding immediate inspection confirmation for tomorrow."},
        {"id": "mut_2", "prompt": "Quick message: Are we inspecting tomorrow? Keep it brief."},
        {"id": "mut_3", "prompt": "Send a friendly greeting asking if the inspection date is still scheduled for tomorrow morning."},
        {"id": "mut_4", "prompt": "Formal notice regarding tomorrow's scheduled inspection verification."}
    ]
    
    batch_prompt = """You are a master AI email evaluator. Grade the following 5 prompt candidates simultaneously against the target persona and metrics.

TARGET PERSONA: Busy corporate manager coordinating tasks.
TARGET METRICS: Tone=6.5, Conciseness=9.4, Accuracy=9.5.

CANDIDATES TO EVALUATE:
"""
    for item in sample_mutations:
        batch_prompt += f"\n- ID: {item['id']}\n  Prompt: {item['prompt']}\n"
        
    batch_prompt += "\nEvaluate all 5 candidates and return structured scores for each."

    print("Sending 1 single batch evaluation request to vLLM model...", flush=True)
    print(f"Model: {config.DEFAULT_GENERATION_MODEL}", flush=True)
    
    start_time = asyncio.get_event_loop().time()
    
    res = llm_client.chat.completions.create(
        model=config.DEFAULT_GENERATION_MODEL,
        response_model=BatchEvaluationResponse,
        messages=[{"role": "user", "content": batch_prompt}]
    )
    result = await res if asyncio.iscoroutine(res) else res
    
    elapsed = asyncio.get_event_loop().time() - start_time
    
    print(f"\n✅ SUCCESS! Batch evaluation completed in {elapsed:.2f} seconds!", flush=True)
    print(f"Evaluated {len(result.evaluations)} candidate prompts in 1 single LLM call:\n", flush=True)
    print("-" * 80, flush=True)
    
    for eval_item in result.evaluations:
        print(f"📌 Candidate ID : {eval_item.mutation_id}", flush=True)
        print(f"   Tone Score   : {eval_item.tone_score:.1f} / 10.0", flush=True)
        print(f"   Conciseness  : {eval_item.conciseness_score:.1f} / 10.0", flush=True)
        print(f"   Accuracy     : {eval_item.accuracy_score:.1f} / 10.0", flush=True)
        print(f"   Critique     : {eval_item.critique}", flush=True)
        print("-" * 80, flush=True)

if __name__ == "__main__":
    asyncio.run(test_batch_evaluation())
