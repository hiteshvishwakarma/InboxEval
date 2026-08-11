import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '../../../../data/pipeline.db')

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Track raw Enron emails and their overall pipeline status
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT UNIQUE,
            raw_text TEXT,
            clean_text TEXT,
            word_count INTEGER,
            size_category TEXT,
            prompt TEXT,
            context TEXT,
            target_persona TEXT,
            status TEXT DEFAULT 'pending',
            current_step INTEGER DEFAULT 1,
            error_log TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # The final output table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS golden_dataset (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_email_id INTEGER,
            original_text TEXT,
            synthetic_text TEXT,
            target_persona TEXT,
            kda_winner_mutation_id TEXT,
            tone_score REAL,
            conciseness_score REAL,
            accuracy_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(raw_email_id) REFERENCES raw_emails(id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)

if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
