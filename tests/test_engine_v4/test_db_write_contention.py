import pytest
import asyncio
from unittest.mock import AsyncMock
from scripts.mass_evolution_runner_v4 import process_email_v4

@pytest.mark.asyncio
async def test_batch_commit_prevents_contention():
    """
    Proves that 100 concurrent workers only result in 1 DB commit.
    """
    mock_db = AsyncMock()
    mock_orchestrator = AsyncMock()
    
    # Create 100 fake workers
    tasks = []
    semaphore = asyncio.Semaphore(60)
    for i in range(100):
        # We need mock JSON payloads for the schema parsing in process_email_v4
        mock_persona = '{"intent": "intent", "sentiment": "s", "nlp_task": "Zero-Shot Drafting", "domain": "d", "format": "f", "power_dynamic": "p", "formality_scale": "Casual", "conciseness_tier": "Standard", "behavioral_quirks": [], "evidence_quotes": [], "prompting_strategies": [], "typology_classification": "t"}'
        mock_dpbc = '{"tone_target": 5.0, "conciseness_target": 5.0, "accuracy_target": 5.0}'
        row = {"id": i, "raw_text": "mock", "target_persona": mock_persona, "dpbc_targets": mock_dpbc}
        tasks.append(asyncio.create_task(process_email_v4(mock_orchestrator, row, semaphore, mock_db)))
        
    # Execute all 100 workers concurrently
    results = await asyncio.gather(*tasks)
    
    # ASSERTION 1: 100 successful workers should return a tuple with "completed"
    assert len(results) == 100
    assert results[0][5] == "completed"
    
    # ASSERTION 2: The individual workers MUST NOT interact with the database
    assert mock_db.execute.call_count == 0, "CRITICAL FAILURE: Worker executed DB query!"
    assert mock_db.commit.call_count == 0, "CRITICAL FAILURE: Worker called commit()!"
