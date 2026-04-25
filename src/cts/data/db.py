import sqlite3
import json
import uuid
from pathlib import Path

DB_PATH = Path("artifacts/replay_buffer.db")

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS experience_replay (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                step INTEGER,
                state_json TEXT,
                action_type TEXT,
                action_magnitude REAL,
                reward REAL,
                next_state_json TEXT,
                is_human_action BOOLEAN,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def log_transition(session_id: str, step: int, state: dict, action: dict, reward: float, next_state: dict, is_human: bool):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO experience_replay (id, session_id, step, state_json, action_type, action_magnitude, reward, next_state_json, is_human_action)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                session_id,
                step,
                json.dumps(state),
                action.get("type", "noop"),
                action.get("magnitude", 0.0),
                reward,
                json.dumps(next_state),
                is_human
            ))
            conn.commit()
    except Exception as e:
        print(f"Failed to log transition to DB: {e}")
