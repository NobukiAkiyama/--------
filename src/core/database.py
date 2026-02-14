import sqlite3
from typing import List, Dict, Any, Optional
import json
import time

class DatabaseManager:
    """
    Manages SQLite connection and schema migrations.
    """
    def __init__(self, db_path: str = "brain.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn

    def init_db(self):
        """
        Initialize database schema.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Personas
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS personas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT, -- router, analysis, communication, coding
                system_prompt TEXT NOT NULL,
                metadata_json TEXT, -- Character Card JSON
                active BOOLEAN DEFAULT 0
            )
            """)

            # 2. Users
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                display_name TEXT,
                intimacy_score INTEGER DEFAULT 0,
                trust_level TEXT DEFAULT 'stranger',
                interaction_count INTEGER DEFAULT 0,
                notes TEXT  -- JSON string or specialized text
            )
            """)

            # 3. Memories (Transactional & Emotional)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                timestamp REAL,
                content TEXT,
                embedding_vector BLOB, -- Vector data
                emotion_tags TEXT, -- JSON list
                sentiment_score REAL,
                memory_type TEXT,
                stability REAL DEFAULT 1.0, 
                base_importance REAL DEFAULT 0.5,
                last_accessed_at REAL,
                recall_count INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """)

            # 4. Actions Log
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS actions_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                action_type TEXT,
                detail TEXT, -- JSON
                reason TEXT
            )
            """)

            # 5. Pending Events (Event Queue)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                source_type TEXT, -- 'reply', 'dm', 'system'
                payload TEXT, -- JSON content of the event
                priority_score INTEGER DEFAULT 0,
                processed BOOLEAN DEFAULT 0
            )
            """)
            
            # 7. System Config (Feature Flags & Settings)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT,
                category TEXT DEFAULT 'general',
                updated_at REAL
            )
            """)

            # 8. Config Audit Log
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS config_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                key TEXT,
                old_value TEXT,
                new_value TEXT,
                reason TEXT,
                changed_by TEXT DEFAULT 'user'
            )
            """)
            
            conn.commit()
            print("[DB] Database initialized.")

    # --- Helper methods ---
    def add_to_outbox(self, platform: str, target_id: str, content: str, message_type: str = 'dm'):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO message_outbox (timestamp, platform, target_id, content, message_type, sent) 
                   VALUES (?, ?, ?, ?, ?, 0)""",
                (time.time(), platform, target_id, content, message_type)
            )
            conn.commit()

    def get_pending_outbox(self, platform: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM message_outbox WHERE platform = ? AND sent = 0",
                (platform,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def mark_outbox_sent(self, message_id: int):
        with self.get_connection() as conn:
            conn.execute("UPDATE message_outbox SET sent = 1 WHERE id = ?", (message_id,))
            conn.commit()

    # --- Helper methods will act as the Data Access Layer ---
    def add_user(self, username: str, display_name: str = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO users (username, display_name) VALUES (?, ?)",
                (username, display_name or username)
            )
            conn.commit()
            
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def log_action(self, action_type: str, detail: Dict[str, Any], reason: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO actions_log (timestamp, action_type, detail, reason) VALUES (?, ?, ?, ?)",
                (time.time(), action_type, json.dumps(detail), reason)
            )
            conn.commit()

    def log_master_action(self, activity_type: str, detail: str, sentiment: str = "neutral"):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO master_actions (timestamp, activity_type, detail, sentiment) VALUES (?, ?, ?, ?)",
                (time.time(), activity_type, detail, sentiment)
            )
            conn.commit()

    def add_pending_event(self, source_type: str, payload: Dict[str, Any], priority: int = 0):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO pending_events (timestamp, source_type, payload, priority_score, processed) 
                   VALUES (?, ?, ?, ?, 0)""",
                (time.time(), source_type, json.dumps(payload, ensure_ascii=False), priority)
            )
            conn.commit()

    def _encode_vector(self, vector: List[float]) -> bytes:
        if not vector:
            return b''
        return struct.pack(f'{len(vector)}f', *vector)

    def save_memory(self, content: str, user_id: Optional[int] = None, 
                    sentiment: float = 0.0, emotions: List[str] = None, 
                    memory_type: str = "chat", llm_client: Optional[Any] = None):
        """
        Saves a memory with embedding and biological metadata.
        """
        from src.llm.client import LLMClient
        llm = llm_client or LLMClient()
        
        # 1. Generate Embedding
        vector = llm.get_embedding(content)
        vector_blob = self._encode_vector(vector)
        
        # 2. Base Importance (Simplified: higher for extreme sentiment)
        base_importance = 0.5 + (abs(sentiment) * 0.5)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO memories (
                    user_id, timestamp, content, embedding_vector, 
                    emotion_tags, sentiment_score, memory_type,
                    stability, base_importance, last_accessed_at, recall_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                user_id, time.time(), content, vector_blob,
                json.dumps(emotions or []), sentiment, memory_type,
                base_importance, base_importance, time.time()
            ))
            conn.commit()
            return cursor.lastrowid

    def get_active_persona(self, role: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if role:
                cursor.execute("SELECT * FROM personas WHERE active = 1 AND role = ? ORDER BY id DESC LIMIT 1", (role,))
            else:
                cursor.execute("SELECT * FROM personas WHERE active = 1 ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def register_character_card(self, card_data: Dict[str, Any], role: str = "router", active: bool = False):
        """
        Registers or updates a Character Card in the personas table.
        """
        name = card_data.get("identity", {}).get("name") or card_data.get("name")
        system_prompt = card_data.get("behavior", {}).get("system_prompt") or card_data.get("system_prompt")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM personas WHERE name = ?", (name,))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute("""
                    UPDATE personas 
                    SET system_prompt = ?, metadata_json = ?, role = ?, active = ? 
                    WHERE id = ?
                """, (system_prompt, json.dumps(card_data, ensure_ascii=False), role, int(active), existing[0]))
            else:
                cursor.execute("""
                    INSERT INTO personas (name, role, system_prompt, metadata_json, active)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, role, system_prompt, json.dumps(card_data, ensure_ascii=False), int(active)))
            conn.commit()

    def get_config(self, key: str, default: Any = None) -> Any:
        """Retrieves a configuration value from the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_config WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row[0])
                except:
                    return row[0]
            return default

    def set_config(self, key: str, value: Any, reason: str = "No reason provided", changed_by: str = "user"):
        """Sets a configuration value and records the change in the audit log."""
        str_value = json.dumps(value) if not isinstance(value, (str, int, float, bool)) else str(value)
        now = time.time()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Get old value for audit
            cursor.execute("SELECT value FROM system_config WHERE key = ?", (key,))
            old_row = cursor.fetchone()
            old_value = old_row[0] if old_row else None
            
            # Upsert config
            cursor.execute("""
                INSERT INTO system_config (key, value, updated_at) 
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """, (key, str_value, now))
            
            # Insert audit log
            cursor.execute("""
                INSERT INTO config_audit_log (timestamp, key, old_value, new_value, reason, changed_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (now, key, old_value, str_value, reason, changed_by))
            
            conn.commit()
            print(f"[DB] Config '{key}' updated. Mode: {str_value}. Reason: {reason}")

    def set_system_alert(self, message: str, level: str = "warning"):
        """Sets a system-wide alert for the dashboard."""
        alert_data = {
            "message": message,
            "level": level,
            "timestamp": time.time()
        }
        self.set_config("system_alert", alert_data, reason="System alert triggered")

    def clear_system_alert(self):
        """Clears the current system alert."""
        self.set_config("system_alert", None, reason="System alert cleared")

    def get_system_alert(self) -> Optional[Dict[str, Any]]:
        """Retrieves the current active system alert."""
        return self.get_config("system_alert")

