import os
import sqlite3
import sys

DB_PATH = os.path.abspath("data/pipeline.db")

def inspect_records(limit=10):
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        sys.exit(1)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT g.raw_email_id, r.raw_text, g.target_persona, g.synthetic_text, g.tone_score, g.conciseness_score, g.accuracy_score
        FROM golden_dataset g
        JOIN raw_emails r ON g.raw_email_id = r.id
        ORDER BY g.id DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    print(f"\n==================================================================================")
    print(f"               INBOXEVAL GOLDEN DATASET SIDE-BY-SIDE INSPECTOR                   ")
    print(f"==================================================================================\n")
    
    for idx, r in enumerate(rows):
        print(f"📌 RECORD #{idx+1} [EMAIL ID: {r[0]}]")
        print(f"👤 Target Persona : {r[2]}")
        print(f"🎯 DPBC Targets   : Tone={r[4]} | Conciseness={r[5]} | Accuracy={r[6]}")
        print("-" * 82)
        print(f"📄 ORIGINAL RAW HUMAN EMAIL:\n{r[1].strip()}\n")
        print("-" * 82)
        print(f"✨ EVOLVED SUPER PROMPT:\n{r[3].strip()}\n")
        print("=" * 82 + "\n")

if __name__ == "__main__":
    limit_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    inspect_records(limit_arg)
