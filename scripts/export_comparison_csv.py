import os
import csv
import sqlite3

DB_PATH = os.path.abspath("data/pipeline.db")
OUTPUT_CSV_LOCAL = os.path.abspath("data/golden_records_sample_comparison.csv")
OUTPUT_CSV_DOCS = os.path.abspath("docs/golden_records_sample_comparison.csv")

def clean_display_text(text, fallback_raw=""):
    """If text is empty or just dashes, use fallback raw text."""
    if not text or len(text.strip('- \n\t')) < 5:
        text = fallback_raw
    # Clean up forwarded headers if present
    if "Forwarded by" in text:
        parts = text.split("Subject:")
        if len(parts) > 1:
            text = parts[-1].strip()
    return text.strip()

def export_csv():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Join golden_dataset with raw_emails to always get full raw_text as fallback
    query = """
        SELECT g.id, g.raw_email_id, g.original_text, r.raw_text, g.target_persona, g.synthetic_text, g.tone_score, g.conciseness_score, g.accuracy_score, g.created_at
        FROM golden_dataset g
        LEFT JOIN raw_emails r ON g.raw_email_id = r.id
        ORDER BY g.id ASC
        LIMIT 10
    """
    cursor.execute(query)
    early_rows = cursor.fetchall()

    query_latest = """
        SELECT g.id, g.raw_email_id, g.original_text, r.raw_text, g.target_persona, g.synthetic_text, g.tone_score, g.conciseness_score, g.accuracy_score, g.created_at
        FROM golden_dataset g
        LEFT JOIN raw_emails r ON g.raw_email_id = r.id
        ORDER BY g.id DESC
        LIMIT 10
    """
    cursor.execute(query_latest)
    latest_rows = cursor.fetchall()

    conn.close()

    fieldnames = [
        "batch_type", "golden_record_pk", "raw_email_id", "target_persona", 
        "original_email_text", "evolved_super_prompt", 
        "tone_score", "conciseness_score", "accuracy_score", "created_at"
    ]

    rows_to_write = []
    
    for r in early_rows:
        orig_text = clean_display_text(r[2], r[3])
        rows_to_write.append({
            "batch_type": "Early Baseline (10-Gen Fixed)",
            "golden_record_pk": r[0],
            "raw_email_id": r[1],
            "target_persona": r[4],
            "original_email_text": orig_text,
            "evolved_super_prompt": r[5].strip() if r[5] else "",
            "tone_score": r[6],
            "conciseness_score": r[7],
            "accuracy_score": r[8],
            "created_at": r[9]
        })

    for r in reversed(latest_rows):
        orig_text = clean_display_text(r[2], r[3])
        rows_to_write.append({
            "batch_type": "Optimized Turbo (Batch + Adaptive Stop)",
            "golden_record_pk": r[0],
            "raw_email_id": r[1],
            "target_persona": r[4],
            "original_email_text": orig_text,
            "evolved_super_prompt": r[5].strip() if r[5] else "",
            "tone_score": r[6],
            "conciseness_score": r[7],
            "accuracy_score": r[8],
            "created_at": r[9]
        })

    os.makedirs(os.path.dirname(OUTPUT_CSV_LOCAL), exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_CSV_DOCS), exist_ok=True)

    for path in [OUTPUT_CSV_LOCAL, OUTPUT_CSV_DOCS]:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_to_write)

    print(f"✅ Clean CSV successfully generated at:\n  - {OUTPUT_CSV_LOCAL}\n  - {OUTPUT_CSV_DOCS}")

if __name__ == "__main__":
    export_csv()
