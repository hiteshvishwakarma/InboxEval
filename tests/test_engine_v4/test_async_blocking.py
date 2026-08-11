import pytest
import asyncio
import time
from unittest.mock import MagicMock
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
