# Engine v4 Implementation Plan: Focus on Bug 1 (Prefix Cache Buster)

## Goal Description
You were absolutely right to hold me accountable for Bug 1. I rushed the previous explanation, so I just performed a deep, meticulous audit of `step_05_batch_genesis.py`. 

**The Bug:** The developer wrote a prompt template titled `STATIC PREFIX`, but then mistakenly injected a massive amount of dynamic variables (`{required_verbs}`, `{persona.intent}`, `{persona.sentiment}`, `{persona.behavioral_quirks}`) directly into the top of the string.
Because the Target Persona changes for every single email, the physical string hash of the "Static Prefix" changes every single time. When this hits your GCP server, vLLM compares the prompt hash, sees that it doesn't match the cache, and is forced to re-compute the entire prefill phase from scratch, leading to a 0% Prefix Cache hit rate and massive latency.
**The Hidden Nuance:** Exactly like Bug 4, there is a bare `except Exception as e:` block at the bottom of the script that catches Pydantic ValidationErrors and returns an empty array. This silently kills the FSM instead of allowing Tenacity to retry!

## Proposed Changes

### [MODIFY] `src/engine_v4/golden_dataset_generator_v4/engine_steps/step_05_batch_genesis.py`
We will mathematically guarantee the cache hit rate by separating the prompt into a 100% static `system` string and a fully dynamic `user` string. We will also remove the silent exception trap.

```diff
-    # Static-First Prompt Layout: Instructions at index 0 for 100% vLLM Radix Cache Hits
-    static_first_prompt = f"""
-SYSTEM INSTRUCTIONS & CONSTRAINTS (STATIC PREFIX):
-You are a master prompt engineer. Generate 5 distinct Base Prompts for the given 5 strategies.
-CRITICAL CONSTRAINT: Each prompt's 'action_command' MUST begin with EXACTLY ONE of: {required_verbs}.
-ANTI-META LEAK: Never refer to 'the original email' or 'reference text'.
-FACTUAL INJECTION: Explicitly list all core entities, dates, and claims.
-
-PERSONA METRICS:
-- Intent: {persona.intent} | Sentiment: {persona.sentiment}
-- Power Dynamic: {persona.power_dynamic} | Formality: {persona.formality_scale}
-- Quirks: {', '.join(persona.behavioral_quirks)}
-
---- DYNAMIC INPUT DATA ---
-Strategies to implement: {persona.prompting_strategies}
-Target Email Text: {email.raw_text}
-"""
+    # 100% Static System Prompt for vLLM Prefix Caching
+    system_prompt = """
+SYSTEM INSTRUCTIONS & CONSTRAINTS (STATIC PREFIX):
+You are a master prompt engineer. Generate 5 distinct Base Prompts for the given strategies in the User Prompt.
+ANTI-META LEAK: Never refer to 'the original email' or 'reference text'.
+FACTUAL INJECTION: Explicitly list all core entities, dates, and claims.
+"""
+
+    user_prompt = f"""
+CRITICAL CONSTRAINT: Each prompt's 'action_command' MUST begin with EXACTLY ONE of: {required_verbs}.
+
+TARGET PERSONA METRICS:
+- Intent: {persona.intent} | Sentiment: {persona.sentiment}
+- Power Dynamic: {persona.power_dynamic} | Formality: {persona.formality_scale}
+- Quirks: {', '.join(persona.behavioral_quirks)}
+
+--- DYNAMIC INPUT DATA ---
+Strategies to implement: {persona.prompting_strategies}
+Target Email Text: {email.raw_text}
+"""

-    try:
-        if llm_client:
-            res = llm_client.chat.completions.create(
-                model=config.DEFAULT_GENERATION_MODEL,
-                response_model=BatchGenesisResponse,
-                messages=[{"role": "user", "content": static_first_prompt}]
-            )
-    except Exception as e:
-        logger.error(f"LLM failed in Engine v2 Batched Genesis for email {email.id}: {e}")
+    if llm_client:
+        res = llm_client.chat.completions.create(
+            model=config.DEFAULT_GENERATION_MODEL,
+            response_model=BatchGenesisResponse,
+            messages=[
+                {"role": "system", "content": system_prompt},
+                {"role": "user", "content": user_prompt}
+            ]
+        )
+        # ... (Dictionary extraction logic remains the same)
```
*(By completely removing the `except Exception:` block, any LLM hallucinations will safely crash upward into the Tenacity `@retry` decorator).*

## Verification Plan (The Pytest)
We will write a Pytest to mathematically prove that the System Prompt string hash remains strictly identical, even if the Engine processes two wildly different emails back-to-back.

### [NEW] `tests/test_engine_v4/test_prefix_cache_hash.py`
```python
import pytest
from unittest.mock import AsyncMock
from src.engine_v4.golden_dataset_generator_v4.engine_steps.step_05_batch_genesis import generate_batch_genesis_mutations_v4

@pytest.mark.asyncio
async def test_prefix_cache_is_static():
    mock_client = AsyncMock()
    
    # Execute Genesis on Email 1 (Angry Persona)
    await generate_batch_genesis_mutations_v4(email_angry, persona_angry, mock_client)
    
    # Execute Genesis on Email 2 (Professional Persona)
    await generate_batch_genesis_mutations_v4(email_prof, persona_prof, mock_client)
    
    # Extract the "system" prompt (index 0) from both API calls
    sys_prompt_1 = mock_client.chat.completions.create.call_args_list[0][1]['messages'][0]['content']
    sys_prompt_2 = mock_client.chat.completions.create.call_args_list[1][1]['messages'][0]['content']
    
    # ASSERTION: The hashes must be perfectly identical for the vLLM cache to hit
    assert sys_prompt_1 == sys_prompt_2, "CRITICAL FAILURE: System prompt mutated, prefix cache busted!"
```
