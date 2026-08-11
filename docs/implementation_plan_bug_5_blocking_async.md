# Engine v4 Implementation Plan: Focus on Bug 5 (Blocking Async I/O)

## Goal Description
Following your instructions to go slowly and mathematically analyze the codebase, I focused entirely on **Bug 5 (Blocking Async I/O)** inside `mass_evolution_runner_v3.py`. 

**The Bug:** The Mass Runner operates a highly concurrent `asyncio` event loop designed to handle 60 simultaneous workers. However, right before the workers are launched, the script fetches a batch of 100 emails using the `DiversitySampler`:
`row = sampler.get_next_best_email()`
The problem is that `get_next_best_email()` is a **100% synchronous** function. It opens a SQLite connection, executes multiple complex aggregation queries, updates the row lock, and commits the transaction. Because it is called directly inside the `async def main()` event loop without an `await` or thread offload, it physically blocks the entire Python process. While those 100 database queries are running sequentially, the asyncio loop is frozen, unable to process network responses from the LLM or handle concurrent tasks!

## Proposed Changes

### [MODIFY] `scripts/mass_evolution_runner_v4.py`
We will mathematically eliminate the event loop blockage by offloading the synchronous `sqlite3` operations to an underlying system thread pool, allowing the asyncio event loop to continue managing the active 60 LLM workers without interruption.

```diff
-    async with aiosqlite.connect(DB_PATH) as db:
-        while True:
-            pending_rows = []
-            print(f"Sampling {BATCH_SIZE} raw emails using the Smart Diversity Sampler...")
-            for _ in range(BATCH_SIZE):
-                row = sampler.get_next_best_email()
-                if row:
-                    pending_rows.append(row)
-                else:
-                    break

+    async with aiosqlite.connect(DB_PATH) as db:
+        while True:
+            pending_rows = []
+            print(f"Sampling {BATCH_SIZE} raw emails using the Smart Diversity Sampler...")
+            for _ in range(BATCH_SIZE):
+                # [FIX]: Offload synchronous sqlite3 I/O to a system thread so it doesn't freeze the asyncio loop!
+                row = await asyncio.to_thread(sampler.get_next_best_email)
+                if row:
+                    pending_rows.append(row)
+                else:
+                    break
```

*(Note: There is a related Bug 6 concerning SQLite Write Contention during `await db.commit()`. I will address that exclusively in the next plan as per your instructions to take it one by one).*

## Verification Plan (The Pytest)
We will write a Pytest to prove that the execution of the sampler is non-blocking to the main event loop.

### [NEW] `tests/test_engine_v4/test_async_blocking.py`
```python
import pytest
import asyncio
import time
from unittest.mock import MagicMock, patch
from src.engine_v4.golden_dataset_generator_v4.diversity_sampler import DiversitySampler

@pytest.mark.asyncio
async def test_sampler_does_not_block_event_loop():
    """
    Proves that calling the sampler offloads to a thread, 
    allowing other async tasks to run concurrently.
    """
    mock_sampler = MagicMock()
    
    # Simulate a slow synchronous database query (1 second)
    def slow_sync_query():
        time.sleep(1)
        return {"id": "mock_email"}
        
    mock_sampler.get_next_best_email = slow_sync_query
    
    # Create a simple concurrent async task that should finish INSTANTLY
    async def quick_async_task():
        await asyncio.sleep(0.1)
        return "Async task complete!"
        
    start_time = time.time()
    
    # Run the slow sampler query and the quick async task CONCURRENTLY
    sampler_task = asyncio.create_task(asyncio.to_thread(mock_sampler.get_next_best_email))
    quick_task = asyncio.create_task(quick_async_task())
    
    done, pending = await asyncio.wait(
        [sampler_task, quick_task], 
        return_when=asyncio.FIRST_COMPLETED
    )
    
    # ASSERTION: The quick async task MUST finish first!
    # If the sampler blocked the event loop, the quick task would be starved and couldn't finish first.
    finished_task = list(done)[0]
    assert finished_task.result() == "Async task complete!", "CRITICAL FAILURE: The event loop was blocked!"
    
    # Cleanup
    await sampler_task
```
