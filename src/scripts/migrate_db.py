import sqlite3
from src.core.database import DatabaseManager

def migrate_db():
    print("[Migration] Starting database migration...")
    db = DatabaseManager()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Update Personas Table
        cursor.execute("PRAGMA table_info(personas)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'role' not in columns:
            print("[Migration] Adding 'role' to personas...")
            cursor.execute("ALTER TABLE personas ADD COLUMN role TEXT")
        
        if 'metadata_json' not in columns:
            print("[Migration] Adding 'metadata_json' to personas...")
            cursor.execute("ALTER TABLE personas ADD COLUMN metadata_json TEXT")

        # 2. Update Memories Table
        cursor.execute("PRAGMA table_info(memories)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'embedding_vector' not in columns:
            print("[Migration] Adding 'embedding_vector' to memories...")
            cursor.execute("ALTER TABLE memories ADD COLUMN embedding_vector BLOB")
            
        if 'stability' not in columns:
            print("[Migration] Adding 'stability' to memories...")
            cursor.execute("ALTER TABLE memories ADD COLUMN stability REAL DEFAULT 1.0")

        if 'base_importance' not in columns:
            print("[Migration] Adding 'base_importance' to memories...")
            cursor.execute("ALTER TABLE memories ADD COLUMN base_importance REAL DEFAULT 0.5")

        if 'last_accessed_at' not in columns:
            print("[Migration] Adding 'last_accessed_at' to memories...")
            cursor.execute("ALTER TABLE memories ADD COLUMN last_accessed_at REAL")

        if 'recall_count' not in columns:
            print("[Migration] Adding 'recall_count' to memories...")
            cursor.execute("ALTER TABLE memories ADD COLUMN recall_count INTEGER DEFAULT 0")

        # 3. Check if master_actions table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='master_actions'")
        if not cursor.fetchone():
            print("[Migration] Creating 'master_actions' table...")
            cursor.execute("""
            CREATE TABLE master_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                activity_type TEXT,
                detail TEXT,
                sentiment TEXT
            )
            """)

            print("[Migration] Table 'master_actions' created.")
            
        conn.commit()
    print("[Migration] Migration completed.")

if __name__ == "__main__":
    migrate_db()
