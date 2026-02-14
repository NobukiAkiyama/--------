import sqlite3
from src.core.database import DatabaseManager

def migrate_users_for_discord():
    print("[Migration] Adding Discord support to users table...")
    db = DatabaseManager()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Check if discord_id column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'discord_id' not in columns:
            print("[Migration] Adding discord_id column...")
            cursor.execute("ALTER TABLE users ADD COLUMN discord_id TEXT")
        
        if 'relationship_level' not in columns:
            print("[Migration] Adding relationship_level column...")
            cursor.execute("ALTER TABLE users ADD COLUMN relationship_level INTEGER DEFAULT 50")
        
        if 'relationship_type' not in columns:
            print("[Migration] Adding relationship_type column...")
            cursor.execute("ALTER TABLE users ADD COLUMN relationship_type TEXT DEFAULT 'stranger'")
        
        if 'notes' not in columns:
            print("[Migration] Adding notes column...")
            cursor.execute("ALTER TABLE users ADD COLUMN notes TEXT DEFAULT ''")
            
        conn.commit()
    print("[Migration] Discord migration completed.")

if __name__ == "__main__":
    migrate_users_for_discord()
