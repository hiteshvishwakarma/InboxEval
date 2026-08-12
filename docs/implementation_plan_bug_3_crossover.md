# Engine v4 Implementation Plan: Focus on Bug 3 (Crossover Persona Drop)

## Goal Description
By focusing strictly on **Bug 3**, I was able to deeply analyze `step_08_09_fused_crossover.py`. The subagent was absolutely correct, and the bug is actually two-fold.

**The Bug:** The Fused Crossover step is supposed to synthesize a new `SuperPrompt` by combining the best DNA from Generation 1. To write this prompt correctly, the LLM *must* know what the target Persona is. However, the current code only passes `persona.nlp_task` (to determine the action verb) and completely ignores `persona.intent`, `persona.tone_guidelines`, etc. The crossover LLM is literally flying blind.
**The Hidden Nuance (Prefix Cache):** Just like in Bug 1, the developer put `{required_verbs}` directly into the `SYSTEM INSTRUCTIONS (STATIC PREFIX)` block. Because the required verbs change per email, the Prefix Cache is broken for the Crossover step too!

## Proposed Changes

### [MODIFY] `src/engine_v4/golden_dataset_generator_v4/engine_steps/step_08_09_fused_crossover.py`
We will rewrite the `fused_prompt` to push all dynamic variables to the bottom (fixing Prefix caching) and explicitly inject the full Persona JSON (fixing the Persona Drop).

```diff
-    # Static-First Fused Prompt Layout with Strict Anti-Verbatim Guard
-    fused_prompt = f"""
-SYSTEM INSTRUCTIONS (STATIC PREFIX):
-You are acting as the Head Linguistic Judge AND Genetic Crossover Engine.
-TASK PART 1: Critique why the winning synthetic output failed to achieve 0.0 Delta.
-TASK PART 2: Synthesize a brand new SuperPrompt merging donor DNA and fixing Part 1 critique.
-
-CRITICAL CONSTRAINTS:
-1. Action command MUST start with EXACTLY ONE of: {required_verbs}.
-2. ANTI-VERBATIM COPYING GUARD: You are STRICTLY FORBIDDEN from copy-pasting or quoting verbatim sentences from the target email inside single/double quotes (NEVER write phrases like "Ensure you state: '...'"). Abstract the user's situation, key entities/dates, intent, and tone naturally into realistic human instructional phrasing.
-3. ANTI-META LEAK: Never refer to 'the original email' or 'reference text'.
-
-DONOR DNA:
-1. Base Architecture Winner: "{eval_dict[kda.overall_winner_mutation_id].prompt_text}"
-2. Best Tone Winner: "{eval_dict[kda.best_tone_mutation_id].prompt_text}"
-3. Best Conciseness Winner: "{eval_dict[kda.best_conciseness_mutation_id].prompt_text}"
-4. Best Factual Accuracy Winner: "{eval_dict[kda.best_accuracy_mutation_id].prompt_text}"
-
---- DYNAMIC INPUT DATA ---
-Original Email: {human_email.raw_text}
-Winning Synthetic Output: {base_winner.synthetic_text}
-Current Winner Error Delta: {base_winner.overall_delta:.2f}
-"""
+    # 100% Static System Prompt for vLLM Prefix Caching
+    system_prompt = """
+SYSTEM INSTRUCTIONS (STATIC PREFIX):
+You are acting as the Head Linguistic Judge AND Genetic Crossover Engine.
+TASK PART 1: Critique why the winning synthetic output failed to achieve 0.0 Delta.
+TASK PART 2: Synthesize a brand new SuperPrompt merging donor DNA and fixing Part 1 critique.
+
+ANTI-VERBATIM COPYING GUARD: You are STRICTLY FORBIDDEN from copy-pasting or quoting verbatim sentences from the target email inside single/double quotes (NEVER write phrases like "Ensure you state: '...'"). Abstract the user's situation, key entities/dates, intent, and tone naturally into realistic human instructional phrasing.
+ANTI-META LEAK: Never refer to 'the original email' or 'reference text'.
+"""
+
+    # All Dynamic Data and Strict Constraints injected here
+    user_prompt = f"""
+CRITICAL ACTION CONSTRAINT:
+The action command MUST start with EXACTLY ONE of these verbs: {required_verbs}.
+
+TARGET PERSONA CONSTRAINTS:
+{persona.model_dump_json(indent=2)}
+
+DONOR DNA:
+1. Base Architecture Winner: "{eval_dict[kda.overall_winner_mutation_id].prompt_text}"
+2. Best Tone Winner: "{eval_dict[kda.best_tone_mutation_id].prompt_text}"
+3. Best Conciseness Winner: "{eval_dict[kda.best_conciseness_mutation_id].prompt_text}"
+4. Best Factual Accuracy Winner: "{eval_dict[kda.best_accuracy_mutation_id].prompt_text}"
+
+--- DYNAMIC INPUT DATA ---
+Original Email: {human_email.raw_text}
+Winning Synthetic Output: {base_winner.synthetic_text}
+Current Winner Error Delta: {base_winner.overall_delta:.2f}
+"""
```

*(Note: The `llm_client.chat.completions.create` call will also be updated to accept `messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]`)*

## Verification Plan (The Pytest)
We will write a test that mathematically proves that the exact JSON representation of the Persona exists within the final string sent to the LLM, and that the System Prompt is strictly static.

### [NEW] `tests/test_engine_v4/test_crossover_schema.py`
```python
import pytest
from unittest.mock import AsyncMock
from src.engine_v4.golden_dataset_generator_v4.engine_steps.step_08_09_fused_crossover import generate_fused_critique_and_crossover_v4

@pytest.mark.asyncio
async def test_crossover_injects_persona_json():
    mock_client = AsyncMock()
    # Mock LLM Response
    mock_client.chat.completions.acreate.return_value = ...
    
    # Run crossover
    await generate_fused_critique_and_crossover_v4(mock_kda, mock_persona, mock_email, mock_client)
    
    # Extract the user prompt sent to the LLM
    user_prompt = mock_client.chat.completions.acreate.call_args[1]['messages'][1]['content']
    
    # ASSERTION 1: The prompt MUST contain the persona's specific intent string
    assert mock_persona.intent in user_prompt, "CRITICAL FAILURE: Persona intent dropped from Crossover!"
    
    # ASSERTION 2: The prompt MUST contain the JSON representation of the tone guidelines
    assert "tone_guidelines" in user_prompt, "CRITICAL FAILURE: Persona JSON was not fully serialized into the prompt!"
```
