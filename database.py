import sqlite3
import pandas as pd
from datetime import datetime
import uuid

DB_PATH = "chat_history.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            start_time TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_prompt TEXT,
            assistant_response TEXT,
            label INTEGER,
            reason TEXT,
            toxicity_details TEXT,
            timestamp TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
    ''')
    conn.commit()
    conn.close()

def create_session():
    session_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO sessions (session_id, start_time) VALUES (?, ?)",
              (session_id, datetime.now()))
    conn.commit()
    conn.close()
    return session_id

def save_message(session_id, user_prompt, assistant_response, label, reason, toxicity_details=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO messages 
        (session_id, user_prompt, assistant_response, label, reason, toxicity_details, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (session_id, user_prompt, assistant_response, label, reason, str(toxicity_details), datetime.now()))
    conn.commit()
    conn.close()

def export_all_messages():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM messages ORDER BY timestamp", conn)
    conn.close()
    return df