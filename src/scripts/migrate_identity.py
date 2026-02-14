"""
Phase 1: Identity Management Database Migration
Creates tables for multi-platform identity linking
"""
import sqlite3
import os
import time

def migrate_identity_system():
    """Add identity management tables"""
    db_path = "brain.db"
    
    if not os.path.exists(db_path):
        print(f"[Migration] Database not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("[Migration] Creating identity management tables...")
    
    # 1. User Identities table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_identities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        platform TEXT NOT NULL,
        platform_id TEXT NOT NULL,
        display_name TEXT,
        verified BOOLEAN DEFAULT 0,
        linked_at REAL,
        UNIQUE(platform, platform_id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    print("[Migration] ✅ user_identities table created")
    
    # 2. Identity Merge Requests table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS identity_merge_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_identity_id INTEGER,
        target_user_id INTEGER,
        confidence_score REAL,
        reason TEXT,
        status TEXT DEFAULT 'pending',
        created_at REAL,
        reviewed_at REAL,
        FOREIGN KEY (source_identity_id) REFERENCES user_identities(id),
        FOREIGN KEY (target_user_id) REFERENCES users(id)
    )
    """)
    print("[Migration] ✅ identity_merge_requests table created")
    
    # 3. Migrate existing Discord users to identities
    cursor.execute("SELECT id, username, discord_id FROM users WHERE discord_id IS NOT NULL")
    discord_users = cursor.fetchall()
    
    for user_id, username, discord_id in discord_users:
        # Check if already migrated
        cursor.execute(
            "SELECT id FROM user_identities WHERE user_id = ? AND platform = 'discord'",
            (user_id,)
        )
        if cursor.fetchone():
            continue
        
        cursor.execute("""
        INSERT INTO user_identities (user_id, platform, platform_id, display_name, verified, linked_at)
        VALUES (?, 'discord', ?, ?, 1, ?)
        """, (user_id, discord_id, username, time.time()))
    
    print(f"[Migration] ✅ Migrated {len(discord_users)} Discord users to identities")
    
    conn.commit()
    conn.close()
    print("[Migration] ✅ Phase 1 complete!")

if __name__ == "__main__":
    migrate_identity_system()
