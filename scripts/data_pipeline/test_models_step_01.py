import os
import sys
import asyncio
import json
from openai import AsyncOpenAI
import instructor

async def test_model(model_name, email_text):
    client = instructor.from_openai(
        AsyncOpenAI(api_key="omniroute", base_url="http://localhost:20128/v1"), 
        mode=instructor.Mode.TOOLS
    )
    
    prompt = f"""You are an expert at reverse-engineering AI prompts.
Read the following real-world corporate email:
---
{email_text[:2000]}
---
Generate the 'Original Instruction' that a user would have typed into an AI assistant to generate this exact email.
Return ONLY a valid JSON object matching this schema:
{{
    "prompt": "<The instruction to generate the email>",
    "context": "<Any background facts or context needed to write it>",
    "target_persona": "<The persona of the sender>"
}}"""
    
    print(f"\n[Testing Model]: {model_name}")
    try:
        response = await client.chat.completions.create(
            response_model=None,
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        output = json.loads(response.choices[0].message.content)
        print(f"✅ Success! Output:")
        print(json.dumps(output, indent=2))
        return {"model": model_name, "status": "success", "output": output}
    except Exception as e:
        print(f"❌ Failed! Error: {str(e)}")
        return {"model": model_name, "status": "failed", "error": str(e)}

async def main():
    test_email = "Hi team, just a quick reminder that our Q3 planning meeting is tomorrow at 10 AM. Please review the attached deck beforehand so we can jump right into the roadmap discussion. Best, Sarah."
    
    # Candidate models based on the free tiers you added
    candidates = [
        "gemini/gemini-1.5-flash",
        "gemini/gemini-1.5-pro",
        "together/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "together/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "cohere/command-r-plus",
        "mistral/mistral-large-latest"
    ]
    
    results = []
    for model in candidates:
        res = await test_model(model, test_email)
        results.append(res)
        
    with open("data/step_01_model_test_results.json", "w") as f:
        json.dump(results, f, indent=4)
        
    print("\n🎯 Testing complete! Results saved to data/step_01_model_test_results.json")

if __name__ == "__main__":
    asyncio.run(main())
