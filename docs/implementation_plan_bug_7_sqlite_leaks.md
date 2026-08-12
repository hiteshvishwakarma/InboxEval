# Engine v4 Implementation Plan: Focus on Bug 7 (SQLite Leaks)

## Goal Description
Maintaining our strict, isolated focus, I audited `diversity_sampler.py` to target **Bug 7 (SQLite Leaks)**. 

**The Bug:** The `get_next_best_email` function explicitly opens a raw `sqlite3.connect()` connection and then attempts to manually call `conn.close()` at the very bottom of the function. 
The fatal flaw here is that if *any* exception occurs between opening and closing the database (for example, if the aggregation query fails, or the database throws a temporary lock timeout), the function instantly crashes upward. The `conn.close()` line is bypassed, and a "zombie" database connection is left open in the OS. As the engine runs over thousands of iterations, these zombie connections pile up, eventually exhausting the system's file descriptors and causing a total catastrophic failure (`Too many open files`).

## Proposed Changes

### [MODIFY] `src/engine_v4/golden_dataset_generator_v4/diversity_sampler.py`
We will mathematically guarantee that the connection is closed—even if a fatal exception occurs—by utilizing Python's `contextlib.closing` combined with the SQLite transaction context manager.

```diff
+ from contextlib import closing
  import sqlite3
  import json
  import logging

  class DiversitySampler:
      # ...
      def get_next_best_email(self) -> Optional[Dict[str, Any]]:
-         conn = sqlite3.connect(self.db_path)
-         conn.row_factory = sqlite3.Row
-         cursor = conn.cursor()
-         
-         distribution = self._get_current_distribution(cursor)
-         # ... (queries) ...
-         
-         if row:
-             cursor.execute("UPDATE raw_emails SET status = 'locked_v3' WHERE id = ?", (row['id'],))
-             conn.commit()
-             result = dict(row)
-         else:
-             result = None
-             
-         conn.close()
-         return result

+         with closing(sqlite3.connect(self.db_path)) as conn:
+             conn.row_factory = sqlite3.Row
+             
+             # The inner 'with conn' manages the transaction (auto-commit/rollback)
+             # The outer 'closing' guarantees conn.close() is fired upon exit
+             with conn:
+                 cursor = conn.cursor()
+                 distribution = self._get_current_distribution(cursor)
+                 # ... (queries) ...
+                 
+                 if row:
+                     cursor.execute("UPDATE raw_emails SET status = 'locked_v4' WHERE id = ?", (row['id'],))
+                     result = dict(row)
+                 else:
+                     result = None
+                     
+             return result
```

## Verification Plan (The Pytest)
We will write a Pytest to mathematically prove that an unexpected exception does not leave a zombie database connection.

### [NEW] `tests/test_engine_v4/test_sqlite_leaks.py`
```python
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
            sampler.get_next_best_email()
            
        # ASSERTION 2: Even though it crashed, the connection MUST have been closed mathematically
        assert mock_conn.close.called is True, "CRITICAL FAILURE: The database connection was leaked!"
```
