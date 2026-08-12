import pytest
from unittest.mock import MagicMock, patch
from src.engine_v4.golden_dataset_generator_v4.diversity_sampler import DiversitySampler

def test_sampler_closes_connection_on_exception():
    """
    Proves that the sqlite connection is strictly closed even if the internal queries crash.
    """
    sampler = DiversitySampler("dummy.db")
    
    mock_conn = MagicMock()
    
    with patch('sqlite3.connect', return_value=mock_conn):
        # Force the internal distribution query to simulate a fatal DB crash
        sampler._get_current_distribution = MagicMock(side_effect=Exception("Fatal DB Crash!"))
        
        # ASSERTION 1: The exception must successfully propagate upward
        with pytest.raises(Exception, match="Fatal DB Crash!"):
            sampler.get_next_batch(10)
            
        # ASSERTION 2: Even though it crashed, the connection MUST have been closed mathematically
        assert mock_conn.close.called is True, "CRITICAL FAILURE: The database connection was leaked!"
