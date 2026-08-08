import sqlite3
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("DiversitySamplerV3")

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
        
    def get_next_best_email(self) -> Optional[Dict[str, Any]]:
        """
        1. Gets current distribution.
        2. Identifies the most underrepresented size category.
        3. Queries `raw_emails` for an enriched email that matches this gap.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        distribution = self._get_current_distribution(cursor)
        
        # We know we want a balanced distribution.
        # Find the category with the lowest count (defaults to 0 if missing)
        categories = ["LONG", "MEDIUM", "MICRO"]
        counts = {cat: distribution.get(cat, 0) for cat in categories}
        
        least_represented_category = min(counts, key=counts.get)
        logger.info(f"Current GoldenDataset Distribution: {counts}")
        logger.info(f"Targeting least represented category: {least_represented_category}")
        
        # Query the database for the next available enriched email matching this category
        cursor.execute("""
            SELECT id, raw_text, target_persona, dpbc_targets 
            FROM raw_emails 
            WHERE status = 'backtranslated' 
              AND dpbc_targets IS NOT NULL 
              AND size_category = ?
            LIMIT 1
        """, (least_represented_category,))
        
        row = cursor.fetchone()
        
        # Fallback: if we run out of that specific category, just grab ANY enriched email
        if not row:
            logger.warning(f"No more {least_represented_category} emails left! Falling back to random enriched email.")
            cursor.execute("""
                SELECT id, raw_text, target_persona, dpbc_targets 
                FROM raw_emails 
                WHERE status = 'backtranslated' 
                  AND dpbc_targets IS NOT NULL 
                LIMIT 1
            """)
            row = cursor.fetchone()
            
        conn.close()
        
        if row:
            return dict(row)
        return None
