import sqlite3
import json
import logging
from contextlib import closing
from typing import Dict, Any, Optional, List

logger = logging.getLogger("DiversitySamplerV4")

class DiversitySampler:
    """
    Acts as the intelligent feedback loop for Engine v3.
    Analyzes the categorical distribution of the current GoldenDataset
    and mathematically samples the least represented raw email from Phase 1.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def _get_current_distribution(self, cursor) -> Dict[str, int]:
        """
        Analyzes all generated GoldenDataset records and calculates frequencies for size_category.
        (Since Phase 1 has heavily skewed toward MICRO, we must balance it).
        """
        cursor.execute("""
            SELECT r.size_category, count(*) 
            FROM golden_dataset g 
            JOIN raw_emails r ON g.raw_email_id = r.id 
            GROUP BY r.size_category
        """)
        results = dict(cursor.fetchall())
        return results
        
    def get_next_batch(self, batch_size: int) -> List[Dict[str, Any]]:
        with closing(sqlite3.connect(self.db_path, timeout=60.0)) as conn:
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
            except sqlite3.OperationalError:
                pass  # DB might be locked by another connection, WAL is likely already active
            conn.row_factory = sqlite3.Row
            
            with conn:
                cursor = conn.cursor()
                distribution = self._get_current_distribution(cursor)
                
                categories = ["short", "medium", "long", "massive", "micro"]
                counts = {cat: distribution.get(cat, 0) for cat in categories}
                
                least_represented_category = min(counts, key=counts.get)
                logger.info(f"Targeting least represented category: {least_represented_category} for batch size {batch_size}")
                
                cursor.execute("""
                    SELECT id, raw_text, target_persona, dpbc_targets 
                    FROM raw_emails 
                    WHERE status = 'backtranslated' 
                      AND dpbc_targets IS NOT NULL 
                      AND size_category = ?
                    LIMIT ?
                """, (least_represented_category, batch_size))
                
                rows = cursor.fetchall()
                
                # If we didn't get enough, fallback to any category
                if len(rows) < batch_size:
                    deficit = batch_size - len(rows)
                    cursor.execute("""
                        SELECT id, raw_text, target_persona, dpbc_targets 
                        FROM raw_emails 
                        WHERE status = 'backtranslated' 
                          AND dpbc_targets IS NOT NULL 
                          AND size_category != ?
                        LIMIT ?
                    """, (least_represented_category, deficit))
                    rows.extend(cursor.fetchall())
                    
                results = []
                for row in rows:
                    cursor.execute("UPDATE raw_emails SET status = 'locked_v4' WHERE id = ?", (row['id'],))
                    results.append(dict(row))
                    
            return results
