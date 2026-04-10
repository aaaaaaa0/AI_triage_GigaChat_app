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
            chat_name TEXT NOT NULL,
            start_time TIMESTAMP,
            is_deleted INTEGER DEFAULT 0
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
            FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

def create_session(chat_name: str = None) -> str:
    session_id = str(uuid.uuid4())
    if chat_name is None:
        chat_name = f"Чат {datetime.now().strftime('%d.%m %H:%M')}"
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO sessions (session_id, chat_name, start_time) VALUES (?, ?, ?)",
              (session_id, chat_name, datetime.now()))
    conn.commit()
    conn.close()
    return session_id

def delete_session(session_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

def rename_session(session_id: str, new_name: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE sessions SET chat_name = ? WHERE session_id = ?", (new_name, session_id))
    conn.commit()
    conn.close()

def get_all_sessions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT session_id, chat_name, start_time FROM sessions WHERE is_deleted = 0 ORDER BY start_time DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def get_messages(session_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT user_prompt, assistant_response, label, reason, toxicity_details, timestamp
        FROM messages
        WHERE session_id = ?
        ORDER BY timestamp
    ''', (session_id,))
    rows = c.fetchall()
    conn.close()
    return rows

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

def export_session_messages(session_id: str):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query('''
        SELECT user_prompt, assistant_response, label, reason, toxicity_details, timestamp
        FROM messages
        WHERE session_id = ?
        ORDER BY timestamp
    ''', conn, params=(session_id,))
    conn.close()
    return df