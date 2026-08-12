import os
import sys
import re
import sqlite3
from tqdm import tqdm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.engine.golden_dataset_generator.db.pipeline_db import init_db, get_connection

try:
    from datasets import load_dataset
except ImportError:
    print("Installing 'datasets' library for HuggingFace...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "datasets"])
    from datasets import load_dataset

def clean_enron_email(raw_text):
    """Strips forwards, and legal boilerplate to isolate the core human text."""
    if not raw_text:
        return None
        
    body = raw_text
    
    # Strip forwarded/replied chains
    chain_markers = [
        r"-----Original Message-----",
        r"----- Forwarded by",
        r"From: .*\nSent: .*\nTo: .*\nSubject:"
    ]
    for marker in chain_markers:
        body = re.split(marker, body, flags=re.IGNORECASE)[0]
        
    # Strip signature/legal boilerplate (common in Enron)
    body = re.sub(r"This e-mail is the property of Enron.*", "", body, flags=re.IGNORECASE | re.DOTALL)
    body = re.sub(r"This email and any attachments are confidential.*", "", body, flags=re.IGNORECASE | re.DOTALL)
    
    # Clean whitespace
    body = re.sub(r'\s+', ' ', body).strip()
    return body

def get_email_category(clean_text):
    """Calculates word count and assigns a size category. Still excludes pure spam."""
    if not clean_text:
        return None, None
        
    word_count = len(clean_text.split())
    
    # Exclude auto-replies or extreme spam
    bad_phrases = ["out of the office", "out of office", "delivery failure", "undeliverable"]
    if any(phrase in clean_text.lower() for phrase in bad_phrases):
        return None, None
        
    if word_count < 20: category = "micro"
    elif word_count <= 150: category = "short"
    elif word_count <= 500: category = "medium"
    elif word_count <= 1500: category = "long"
    else: category = "massive"
    
    return word_count, category

def main():
    print("🚀 Initializing Step 00: Dataset Ingestion & Sanitization")
    init_db()
    
    print("⬇️ Downloading the full Enron Corpus (~500,000 emails) from HuggingFace...")
    dataset = load_dataset("corbt/enron-emails", split="train")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    print("🧹 Cleaning, Categorizing, and Injecting into SQLite DB...")
    inserted_count = 0
    batch_data = []
    
    for i, item in enumerate(tqdm(dataset)):
        raw_text = item.get("body", "")
        clean_text = clean_enron_email(raw_text)
        
        word_count, category = get_email_category(clean_text)
        if category:
            source_id = f"enron_full_{i}"
            batch_data.append((source_id, raw_text, clean_text, word_count, category, 'pending'))
            
        if len(batch_data) >= 5000:
            cursor.executemany(
                "INSERT OR IGNORE INTO raw_emails (source_id, raw_text, clean_text, word_count, size_category, status) VALUES (?, ?, ?, ?, ?, ?)",
                batch_data
            )
            conn.commit()
            inserted_count += len(batch_data)
            batch_data = []
            
    # Insert remaining
    if batch_data:
        cursor.executemany(
            "INSERT OR IGNORE INTO raw_emails (source_id, raw_text, clean_text, word_count, size_category, status) VALUES (?, ?, ?, ?, ?, ?)",
            batch_data
        )
        conn.commit()
        inserted_count += len(batch_data)
        
    conn.close()
    print(f"✅ Ingestion Complete! Successfully loaded {inserted_count} ultra-clean Gold Candidates into SQLite.")

if __name__ == "__main__":
    main()
