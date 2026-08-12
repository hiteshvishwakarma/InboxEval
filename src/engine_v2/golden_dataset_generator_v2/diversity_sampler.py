import sqlite3
from typing import List, Tuple

def fetch_stratified_diversity_batch(db_path: str, batch_size: int = 60) -> List[Tuple]:
    """
    High-speed SQL query that fetches an equal slice across size categories 
    (micro, short, medium, long, massive), prioritizing underrepresented lengths 
    with zero pipeline or engine overhead.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    categories = ['medium', 'long', 'massive', 'short', 'micro']
    slots_per_cat = max(1, batch_size // len(categories))

    queries = []
    for cat in categories:
        queries.append(f"""
            SELECT * FROM (
                SELECT id, clean_text, raw_text, prompt, context, target_persona 
                FROM raw_emails 
                WHERE status = 'backtranslated' 
                  AND size_category = '{cat}' 
                  AND id NOT IN (SELECT raw_email_id FROM golden_dataset)
                ORDER BY RANDOM() 
                LIMIT {slots_per_cat}
            )
        """)

    full_sql = " UNION ALL ".join(queries)
    c.execute(full_sql)
    rows = c.fetchall()
    
    # Fill remaining capacity if any category was underfilled
    if len(rows) < batch_size:
        needed = batch_size - len(rows)
        seen_ids = {r[0] for r in rows}
        placeholders = ','.join('?' * len(seen_ids)) if seen_ids else '0'
        
        query_fill = f"""
            SELECT id, clean_text, raw_text, prompt, context, target_persona 
            FROM raw_emails 
            WHERE status = 'backtranslated' 
              AND id NOT IN ({placeholders})
              AND id NOT IN (SELECT raw_email_id FROM golden_dataset)
            ORDER BY RANDOM() 
            LIMIT ?
        """
        c.execute(query_fill, list(seen_ids) + [needed])
        fill_rows = c.fetchall()
        rows.extend(fill_rows)

    conn.close()
    return rows
