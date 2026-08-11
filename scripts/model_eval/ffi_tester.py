import os
import sys
import asyncio
import json
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, ValidationError

# Load NVIDIA_API_KEY from .env
load_dotenv()

# The strict Pydantic Schema that models MUST adhere to perfectly
class EmailPromptOutput(BaseModel):
    prompt: str = Field(..., description="The synthetic prompt that would generate the email.")
    context: str = Field(..., description="The underlying context/variables of the email.")
    target_persona: str = Field(..., description="The persona of the human who wrote the email.")

# A notoriously difficult, messy corporate email to stress-test the models
STRESS_TEST_EMAIL = """
FWD: Re: Q3 Margins - URGENT
Dan, this is completely unacceptable. We discussed the AWS spend capping at $40k/mo. 
The latest invoice shows $82k. Are you kidding me? If the compute costs are spiraling because 
of the new inference pipeline, you needed to flag this to Finance WEEKS ago. 
I need a post-mortem on my desk by EOD, and you need to get the DevOps team to kill any zombie clusters IMMEDIATELY. 
- Sarah
"""

MODELS_TO_TEST = [
    "openai/gpt-oss-120b",
    "nvidia/nemotron-3-ultra-550b-a55b",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "nvidia/llama-3.3-nemotron-super-49b-v1"
]

async def test_model_ffi(client: AsyncOpenAI, model_name: str, test_rounds: int = 3) -> int:
    """Blasts the model 'test_rounds' times and validates strict JSON fidelity."""
    print(f"\n🧪 Testing {model_name}...")
    score = 0
    
    for i in range(test_rounds):
        try:
            response = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a data extraction AI. Output strictly valid JSON matching the schema: {prompt, context, target_persona}. Do not include markdown formatting or conversational text."},
                    {"role": "user", "content": f"Extract the data from this email:\n\n{STRESS_TEST_EMAIL}"}
                ],
                temperature=0.3,
                max_tokens=500,
                timeout=15.0
            )
            
            raw_output = response.choices[0].message.content.strip()
            
            # Clean potential markdown (some models still try to add ```json)
            if raw_output.startswith("```json"):
                raw_output = raw_output[7:-3].strip()
            elif raw_output.startswith("```"):
                raw_output = raw_output[3:-3].strip()

            # The Ultimate Test: Will Pydantic accept it?
            parsed = EmailPromptOutput.model_validate_json(raw_output)
            print(f"  ✅ Round {i+1}: PERFECT JSON")
            score += 1
            
        except ValidationError as e:
            print(f"  ❌ Round {i+1}: Schema Violation (Missing keys or wrong types)")
        except json.JSONDecodeError:
            print(f"  ❌ Round {i+1}: Fatal JSON Decode Error (Trailing commas or conversational text)")
        except Exception as e:
            print(f"  ⚠️ Round {i+1}: API Error: {str(e)}")
            
    return score

async def main():
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        print("ERROR: NVIDIA_API_KEY not found in .env!")
        sys.exit(1)
        
    client = AsyncOpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )
    
    print("==================================================")
    print("🏆 FORMAT FIDELITY INDEX (FFI) BENCHMARKER 🏆")
    print("==================================================")
    
    leaderboard = {}
    
    for model in MODELS_TO_TEST:
        ffi_score = await test_model_ffi(client, model)
        leaderboard[model] = ffi_score
        
    print("\n\n==================================================")
    print("🏁 FINAL FFI LEADERBOARD 🏁")
    print("==================================================")
    for model, score in sorted(leaderboard.items(), key=lambda x: x[1], reverse=True):
        if score == 3:
            print(f"🟢 {model.ljust(40)} | FFI: {score}/3 (APPROVED)")
        else:
            print(f"🔴 {model.ljust(40)} | FFI: {score}/3 (REJECTED - JSON Hallucination)")

if __name__ == "__main__":
    asyncio.run(main())
