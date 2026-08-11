# Engine v4 Architecture & Detailed Implementation Plan

## Goal Description
Following the Engine v3 Codebase Audit, we are creating a strictly isolated **Engine v4**. This plan details exactly how we will duplicate the architecture, un-merges all 8 bug fixes for absolute clarity, and introduces a massive **Test-Driven Development (TDD) Pytest Suite** to prevent future hallucination regression.

---

## 1. Core Architecture Duplication
To protect the active v3 pipeline, we will copy the source files to a new namespace.
#### [NEW] `src/engine_v4/golden_dataset_generator_v4/`
#### [NEW] `scripts/mass_evolution_runner_v4.py`
#### [NEW] `tests/test_engine_v4/`

*All copied files will have `v3`/`V3` references strictly renamed to `v4`/`V4`.*

---

## 2. The 8 Surgical Bug Fixes (Explicit Mapping)

### Bug 1: The Prefix Cache Buster (Speed Bottleneck)
*Location:* `step_05_batch_genesis.py` and `step_06_static_evaluator.py`
*The Issue:* The "Static" system prompts dynamically injected `dpbc_targets` and `persona` parameters. This physically changed the hash of the system prompt for every email, causing a 0% cache hit rate.
#### [MODIFY] `step_05` and `step_06`
```diff
- SYSTEM_PROMPT = f"Your Persona constraints are: {persona.intent}"
+ SYSTEM_PROMPT = "Apply the Persona constraints provided in the User Prompt."

- USER_PROMPT = f"Here is the email: {email.raw_text}"
+ USER_PROMPT = f"""Here is the email: {email.raw_text}
+
+ STRICT CONSTRAINTS:
+ Persona Intent: {persona.intent}
+ Quirks: {persona.behavioral_quirks}"""
```

### Bug 2: Zero Genetic Variation (Mathematical Flaw)
*Location:* `step_10_elitism.py`
*The Issue:* The script cloned the champion string 4 times instead of mathematically mutating it, instantly triggering fake "plateaus" in the FSM.
#### [MODIFY] `step_10_elitism.py`
```diff
-    for i in range(1, 5):
-        mutations.append(PromptMutation(prompt_text=champion.final_prompt_text))
+    for i in range(1, 5):
+        # Now making an actual LLM call to mutate the champion!
+        mutated_text = await llm_client.chat.completions.acreate(...)
+        mutations.append(PromptMutation(prompt_text=mutated_text))
```

### Bug 3: Crossover Persona Drop (Quality Flaw)
*Location:* `step_08_09_fused_crossover.py`
*The Issue:* Crossover forgot to feed tone and length constraints to the LLM.
#### [MODIFY] `step_08_09_fused_crossover.py`
```diff
- USER_PROMPT = f"Perform crossover. Task: {persona.nlp_task}"
+ USER_PROMPT = f"Perform crossover. Apply ALL constraints from this Persona JSON: {persona.model_dump_json()}"
```

### Bug 4: Silent Eval Fails (Hallucination Risk)
*Location:* `step_06_static_evaluator.py`
*The Issue:* The evaluator caught exceptions and silently returned mock 5.0 scores, hiding LLM hallucinations.
#### [MODIFY] `step_06_static_evaluator.py`
```diff
- except Exception as e:
-     return [EvaluatedEmail(..., tone_score=5.0, conciseness_score=5.0)]
+ # Removed bare except block to allow Tenacity to intercept ValidationErrors and automatically retry.
```

### Bug 5: Blocking Async I/O (Concurrency Bottleneck)
*Location:* `mass_evolution_runner_v4.py`
*The Issue:* Synchronous SQLite sampler queries blocked the entire asyncio loop.
#### [MODIFY] `mass_evolution_runner_v4.py`
```diff
- row = sampler.get_next_best_email()
+ row = await asyncio.to_thread(sampler.get_next_best_email)
```

### Bug 6: Write Contention (Crash Risk)
*Location:* `mass_evolution_runner_v4.py`
*The Issue:* 60 workers simultaneously spammed `await db.commit()`, causing SQLite locks.
#### [MODIFY] `mass_evolution_runner_v4.py`
```diff
  async def process_email_v4(...):
-     await db.commit() # Removed from individual workers
  async def main():
      await tqdm.gather(*tasks)
+     await db.commit() # Moved to the batch-level execution
```

### Bug 7: SQLite Leaks
*Location:* `diversity_sampler.py`
*The Issue:* Missing `try..finally` blocks in the sampler.
#### [MODIFY] `diversity_sampler.py`
```diff
- conn = sqlite3.connect(self.db_path)
+ with sqlite3.connect(self.db_path) as conn:
```

### Bug 8: Schema Redefinition
*Location:* `schemas.py`
*The Issue:* `PersonaProfileV3` was defined twice in the same file.
#### [MODIFY] `schemas.py`
```diff
- class PersonaProfileV4(BaseModel): ... # DELETED duplicate
```

---

## 3. Comprehensive Verification Plan (TDD Pytest Suite)
We will implement an exhaustive TDD suite. Per the new `AGENTS.md` rule, **these tests are immutable**. I am forbidden from changing them if my code fails them; I must rewrite the engine code until the tests pass.

### A. Performance Test (Bug 1 Fix)
**`test_prefix_cache_hash.py`**: Instantiates Step 5 with two entirely different mock emails/personas. Asserts `system_prompt` strings are strictly `==` to prove Prefix Cache hash retention.

### B. Business Logic & Quality Test (Bug 2 & 3 Fix)
**`test_elitism_mutation.py`**: Asserts `llm_client.chat.completions.acreate.call_count == 4` to prove the FSM is mathematically mutating instead of cloning.
**`test_crossover_schema.py`**: Asserts the user prompt payload contains the exact key `"tone_guidelines"` to prove constraints aren't dropped.

### C. Negative Scenario Test (Bug 4 Fix)
**`test_tenacity_fallback.py`**: Forces the mock LLM to return a raw SQL string instead of JSON. Asserts `pytest.raises(ValidationError)` to prove the engine crashes upward (triggering Tenacity) instead of silently proceeding with mock scores.

### D. Security & Concurrency Test (Bug 5, 6, 7 Fix)
**`test_db_write_contention.py`**: Mocks the DB client and asserts `db.commit.call_count == 1` at the end of a mocked batch of 100 workers (rather than 100 commits), proving SQLite lock immunity.

**Command to execute Verification:**
```bash
pytest tests/test_engine_v4/ -v
```
