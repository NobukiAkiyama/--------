import sqlite3
import os

def migrate_relationship_tags():
    """
    Add 'tags' column to users table for social relationship tags.
    Tags are stored as JSON array.
    """
    db_path = "brain.db"
    
    if not os.path.exists(db_path):
        print(f"[Migration] Database not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if tags column exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'tags' not in columns:
        print("[Migration] Adding 'tags' column to users table...")
        cursor.execute("ALTER TABLE users ADD COLUMN tags TEXT DEFAULT '[]'")
        conn.commit()
        print("[Migration] ✅ 'tags' column added successfully")
    else:
        print("[Migration] 'tags' column already exists")
    
    conn.close()

if __name__ == "__main__":
    migrate_relationship_tags()
