# Engine v4 Implementation Plan: Focus on Bug 4 (Silent Eval Fails)

## Goal Description
By focusing strictly on **Bug 4**, I analyzed `step_06_static_evaluator.py`. The subagent was spot on.

**The Bug:** When the LLM evaluates the candidates, it is supposed to return a strict JSON schema. If the LLM hallucinates (e.g., outputs conversational text instead of JSON), Pydantic correctly throws a `ValidationError`. However, the current code traps this error using a bare `except Exception:` block, and silently injects fake scores (5.0, 5.0, 5.0) into the FSM. This completely neutralizes our Tenacity `@retry` logic and corrupts the dataset with unvalidated outputs.
**The Hidden Nuance (Prefix Cache):** Exactly like Bug 1 and 3, the developer injected dynamic DPBC thresholds (`{dpbc.tone_target}`) directly into the `STATIC PREFIX`. Because these thresholds change for every single email, it breaks the vLLM prefix cache hash. We must move them to the bottom.

## Proposed Changes

### [MODIFY] `src/engine_v4/golden_dataset_generator_v4/engine_steps/step_06_static_evaluator.py`
We will rewrite the Prompt to fix the Prefix Cache, and we will delete the silent fallback block to enforce strict Tenacity retries.

```diff
-    # Static-First Prompt Layout: Rubrics at index 0 for 100% vLLM Cache Hits
-    static_first_prompt = f"""
-SYSTEM INSTRUCTIONS & KDA DUAL-SCORING RUBRICS (STATIC PREFIX):
-You are the Head Judge. For each Candidate Prompt below:
-1. Generate the synthetic email output.
-2. Score on 3 absolute dimensions (0.0 to 10.0):
-   - Tone (Formality & Sentiment alignment)
-   - Conciseness (Length & Structure suitability)
-   - Factual Accuracy (Inclusion of essential entities/claims)
-
-TARGET DPBC THRESHOLDS:
-- Tone Target: {dpbc.tone_target:.1f}
-- Conciseness Target: {dpbc.conciseness_target:.1f}
-- Factual Accuracy Target: {dpbc.accuracy_target:.1f}
-
---- DYNAMIC INPUT DATA ---
-Original Target Human Email:
-{email.raw_text}
-
---- CANDIDATES TO EVALUATE ---
-{candidates_formatted}
-"""
+    # 100% Static System Prompt for vLLM Prefix Caching
+    system_prompt = """
+SYSTEM INSTRUCTIONS & KDA DUAL-SCORING RUBRICS (STATIC PREFIX):
+You are the Head Judge. For each Candidate Prompt provided in the User Prompt:
+1. Generate the synthetic email output.
+2. Score on 3 absolute dimensions (0.0 to 10.0):
+   - Tone (Formality & Sentiment alignment)
+   - Conciseness (Length & Structure suitability)
+   - Factual Accuracy (Inclusion of essential entities/claims)
+"""
+
+    user_prompt = f"""
+TARGET DPBC THRESHOLDS:
+- Tone Target: {dpbc.tone_target:.1f}
+- Conciseness Target: {dpbc.conciseness_target:.1f}
+- Factual Accuracy Target: {dpbc.accuracy_target:.1f}
+
+--- DYNAMIC INPUT DATA ---
+Original Target Human Email:
+{email.raw_text}
+
+--- CANDIDATES TO EVALUATE ---
+{candidates_formatted}
+"""

-    try:
-        if llm_client:
-            res = llm_client.chat.completions.create(...)
-        else:
-            # Mock logic
-    except Exception as e:
-        logger.error(f"LLM evaluation failed in Engine v2 for email {email.id}: {e}")
-        # Fallback
-        for m in mutations:
-            evaluations.append(EvaluatedEmail(tone_score=5.0, conciseness_score=5.0, accuracy_score=5.0...))
+    if llm_client:
+        res = llm_client.chat.completions.create(
+            model=config.DEFAULT_GENERATION_MODEL,
+            response_model=BatchEvaluationResponse,
+            messages=[
+                {"role": "system", "content": system_prompt},
+                {"role": "user", "content": user_prompt}
+            ]
+        )
+        response_data = await res if asyncio.iscoroutine(res) else res
+        # ... (Dictionary mapping logic remains the same)
+    else:
+        # Mock logic remains for local testing without LLM
```
*(By completely removing the `except Exception:` block, any Pydantic schema hallucinations will safely crash upward, instantly triggering the Tenacity `@retry` decorator wrapped around our `llm_client`).*

## Verification Plan (The Pytest)
We will write a test that forces a hallucination and proves that it crashes rather than corrupting the dataset.

### [NEW] `tests/test_engine_v4/test_evaluator.py`
```python
import pytest
from pydantic import ValidationError
from unittest.mock import AsyncMock
from src.engine_v4.golden_dataset_generator_v4.engine_steps.step_06_static_evaluator import evaluate_mutations_v4
from src.engine.golden_dataset_generator.schemas import HumanEmail, DPBCThresholds, PromptMutation

@pytest.mark.asyncio
async def test_evaluator_strict_failure_no_fallback():
    mock_client = AsyncMock()
    
    # Force the mock LLM to raise a ValidationError (simulating a hallucinated JSON schema)
    mock_client.chat.completions.create.side_effect = ValidationError.from_exception_data("Mock Error", line_errors=[])
    
    mock_mutations = [PromptMutation(id="1", prompt_text="test", typology_persona="test", generation_num=1)]
    mock_email = HumanEmail(id="1", raw_text="Hello")
    mock_dpbc = DPBCThresholds(tone_target=5.0, conciseness_target=5.0, accuracy_target=5.0)
    
    # ASSERTION: The function MUST raise the error. If it returns a list of mock 5.0 scores, this test fails.
    with pytest.raises(ValidationError):
        await evaluate_mutations_v4(mock_mutations, mock_email, mock_dpbc, mock_client)
```
