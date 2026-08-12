import sys
import os
import time
import sqlite3

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "pipeline.db"))

def test_stratified_diversity_query(batch_size=60):
    print("="*80)
    print("🧪 TESTING ZERO-OVERHEAD STRATIFIED DIVERSITY SQL QUERY")
    print("="*80)

    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    t0 = time.time()

    categories = ['medium', 'long', 'massive', 'short', 'micro']
    slots_per_cat = batch_size // len(categories)

    queries = []
    for cat in categories:
        queries.append(f"""
            SELECT * FROM (
                SELECT id, size_category, word_count, clean_text, target_persona 
                FROM raw_emails 
                WHERE size_category = '{cat}' 
                  AND id NOT IN (SELECT raw_email_id FROM golden_dataset)
                ORDER BY RANDOM() 
                LIMIT {slots_per_cat}
            )
        """)

    full_sql = " UNION ALL ".join(queries)
    c.execute(full_sql)
    rows = c.fetchall()
    query_latency = (time.time() - t0) * 1000.0  # ms

    conn.close()

    print(f"\n⚡ SQL Query Execution Latency : {query_latency:.2f} ms (Zero Engine Overhead!)")
    print(f"📦 Total Emails Fetched in Batch  : {len(rows)} emails")

    size_counts = {}
    for r in rows:
        cat = r[1]
        size_counts[cat] = size_counts.get(cat, 0) + 1

    print("\n📊 Batch Diversity Breakdown across Size Categories:")
    for cat in categories:
        count = size_counts.get(cat, 0)
        pct = (count / len(rows) * 100) if rows else 0
        print(f"  • {cat.upper():<8}: {count:<2d} emails ({pct:.1f}%)")

    print("\n📝 Sample Fetched Batch Items:")
    for idx, r in enumerate(rows[:5]):
        print(f"  [{idx+1}] ID: {r[0]} | Cat: {r[1].upper()} | Words: {r[2]} | Snippet: \"{r[3][:60]}...\"")

if __name__ == "__main__":
    test_stratified_diversity_query()
