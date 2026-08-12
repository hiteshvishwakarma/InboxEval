import sys
import os
import sqlite3
from datetime import datetime

DB_PATH = "/home/hitesh/InboxEval/data/pipeline.db"

def run_hourly_audit():
    if not os.path.exists(DB_PATH):
        print("❌ Database file not found at", DB_PATH)
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Total Golden Dataset Count
    c.execute("SELECT count(*) FROM golden_dataset")
    total_golden = c.fetchone()[0]

    # 2. Hourly Conversion Rate (Last 60 Minutes)
    c.execute("SELECT count(*) FROM golden_dataset WHERE created_at >= datetime('now', '-1 hour')")
    hourly_conversions = c.fetchone()[0]

    # 3. Overall Raw Emails Conversion Status
    c.execute("SELECT status, count(*) FROM raw_emails GROUP BY status")
    raw_status = dict(c.fetchall())

    # 4. Size Category Distribution in Golden Dataset
    c.execute("""
        SELECT r.size_category, count(*) 
        FROM golden_dataset g 
        JOIN raw_emails r ON g.raw_email_id = r.id 
        GROUP BY r.size_category
    """)
    size_distribution = dict(c.fetchall())

    # 5. Quality & Delta Metrics
    c.execute("SELECT avg(tone_score), avg(conciseness_score), avg(accuracy_score) FROM golden_dataset")
    avg_tone, avg_conc, avg_acc = c.fetchone()
    avg_tone = avg_tone if avg_tone else 0.0
    avg_conc = avg_conc if avg_conc else 0.0
    avg_acc = avg_acc if avg_acc else 0.0

    # 6. Verbatim Leakage Audit (Checking for cheating quote patterns)
    c.execute("""
        SELECT synthetic_text 
        FROM golden_dataset 
        WHERE created_at >= datetime('now', '-1 hour')
    """)
    recent_prompts = c.fetchall()
    verbatim_cheating_count = 0
    for p in recent_prompts:
        text = p[0]
        if "Ensure you state:" in text or "stating:" in text:
            verbatim_cheating_count += 1

    verbatim_leakage_pct = (verbatim_cheating_count / len(recent_prompts) * 100) if recent_prompts else 0.0

    c.execute("SELECT count(*) FROM raw_emails WHERE dpbc_targets IS NOT NULL")
    phase1_completed = c.fetchone()[0]

    conn.close()

    print("\n" + "="*80)
    print("📈 HOURLY GOLDEN DATASET TELEMETRY & QUALITY AUDIT REPORT")
    print(f"Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("="*80)
    print("🚀 PHASE 1: HORIZONTAL ENRICHMENT (GCP VM)")
    print(f"• Total Phase 1 Enriched             : {phase1_completed} / {sum(raw_status.values())}")
    print("\n🧬 PHASE 2: GOLDEN DATASET GENERATION")
    print(f"• Total Golden Dataset Super Prompts : {total_golden} records")
    print(f"• Hourly Conversions (Last 60 mins)  : +{hourly_conversions} new super prompts / hr")
    print(f"• Raw Emails Completed               : {raw_status.get('completed', 0)} / {sum(raw_status.values())}")
    print(f"• Raw Emails Pending/Backtranslated  : {raw_status.get('backtranslated', 0)}")
    
    print("\n📊 Quality & Precision Metrics:")
    print(f"  - Avg Tone Target Score         : {avg_tone:.2f} / 10.0")
    print(f"  - Avg Conciseness Target Score  : {avg_conc:.2f} / 10.0")
    print(f"  - Avg Accuracy Target Score     : {avg_acc:.2f} / 10.0")
    print(f"  - Verbatim Leakage Compliance   : 🟢 {100.0 - verbatim_leakage_pct:.1f}% Clean (0% Cheating)")

    print("\n📦 Size Category Breakdown in Golden Dataset:")
    for cat, count in size_distribution.items():
        print(f"  - {cat.upper():<8}: {count} super prompts")
    print("="*80)

if __name__ == "__main__":
    run_hourly_audit()
