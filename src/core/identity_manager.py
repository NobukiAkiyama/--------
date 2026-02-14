"""
Identity Manager - Phase 2
Handles multi-platform identity linking and merge requests
"""
from typing import Dict, List, Optional, Any
import time
import json

class IdentityManager:
    """Manages user identities across multiple platforms"""
    
    def __init__(self, db_manager, llm_client=None):
        self.db = db_manager
        self.llm = llm_client
    
    def register_identity(
        self, 
        user_id: int, 
        platform: str, 
        platform_id: str, 
        display_name: Optional[str] = None,
        verified: bool = False
    ) -> int:
        """
        Register a new identity for a user.
        
        Args:
            user_id: ID of the user in users table
            platform: 'discord', 'bluesky', 'twitter', etc.
            platform_id: Platform-specific ID
            display_name: User's display name on that platform
            verified: Whether this identity is verified
        
        Returns:
            identity_id
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if identity already exists
            cursor.execute(
                "SELECT id FROM user_identities WHERE platform = ? AND platform_id = ?",
                (platform, platform_id)
            )
            existing = cursor.fetchone()
            
            if existing:
                return existing['id']
            
            cursor.execute("""
                INSERT INTO user_identities 
                (user_id, platform, platform_id, display_name, verified, linked_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, platform, platform_id, display_name, int(verified), time.time()))
            
            conn.commit()
            return cursor.lastrowid
    
    def find_user_by_identity(self, platform: str, platform_id: str) -> Optional[int]:
        """Find user_id by platform identity"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id FROM user_identities WHERE platform = ? AND platform_id = ?",
                (platform, platform_id)
            )
            result = cursor.fetchone()
            return result['user_id'] if result else None
    
    def get_user_identities(self, user_id: int) -> List[Dict]:
        """Get all identities for a user"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM user_identities WHERE user_id = ?",
                (user_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def create_merge_request(
        self,
        source_identity_id: int,
        target_user_id: int,
        confidence: float,
        reason: str
    ) -> int:
        """
        Create a request to merge an identity into a user account.
        Requires manual approval.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO identity_merge_requests
                (source_identity_id, target_user_id, confidence_score, reason, status, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?)
            """, (source_identity_id, target_user_id, confidence, reason, time.time()))
            conn.commit()
            return cursor.lastrowid
    
    def get_pending_merge_requests(self) -> List[Dict]:
        """Get all pending merge requests"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    mr.*,
                    ui.platform,
                    ui.platform_id,
                    ui.display_name,
                    u.username as target_username
                FROM identity_merge_requests mr
                JOIN user_identities ui ON mr.source_identity_id = ui.id
                JOIN users u ON mr.target_user_id = u.id
                WHERE mr.status = 'pending'
                ORDER BY mr.created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def approve_merge_request(self, request_id: int) -> bool:
        """Approve a merge request and link the identity"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get request details
            cursor.execute(
                "SELECT source_identity_id, target_user_id FROM identity_merge_requests WHERE id = ?",
                (request_id,)
            )
            request = cursor.fetchone()
            if not request:
                return False
            
            # Update identity to point to target user
            cursor.execute(
                "UPDATE user_identities SET user_id = ?, verified = 1 WHERE id = ?",
                (request['target_user_id'], request['source_identity_id'])
            )
            
            # Mark request as approved
            cursor.execute(
                "UPDATE identity_merge_requests SET status = 'approved', reviewed_at = ? WHERE id = ?",
                (time.time(), request_id)
            )
            
            conn.commit()
            return True
    
    def reject_merge_request(self, request_id: int) -> bool:
        """Reject a merge request"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE identity_merge_requests SET status = 'rejected', reviewed_at = ? WHERE id = ?",
                (time.time(), request_id)
            )
            conn.commit()
            return True
    
    def auto_detect_merge_candidates(self) -> List[Dict]:
        """
        Detect potential same-person identities.
        Uses LLM if available, falls back to heuristic.
        """
        # 1. Fetch all identities
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, platform, platform_id, display_name
                FROM user_identities
            """)
            identities = [dict(row) for row in cursor.fetchall()]
            cursor.execute("SELECT id, username FROM users")
            users = [dict(row) for row in cursor.fetchall()]
        
        # 2. Use LLM if prompt-driven analysis is possible
        if self.llm:
            active_persona = self.db.get_active_persona(role="analysis")
            system_prompt = active_persona["system_prompt"] if active_persona else "あなたは分析担当のリトだ。"
            
            prompt = f"""以下のユーザーリストと、各プラットフォームのアイデンティティ（アカウント）リストを照合してください。
同一人物である可能性が高い組み合わせを見つけ出し、理由と共に提案してください。

ユーザーリスト: {json.dumps(users, ensure_ascii=False)}
アイデンティティリスト: {json.dumps(identities, ensure_ascii=False)}

JSON形式のみで返答してください:
{{
  "suggestions": [
     {{"identity1_id": ID, "identity2_id": ID, "confidence": 0.0-1.0, "reason": "理由"}}
  ]
}}"""
            try:
                response = self.llm.generate(prompt, system_prompt=system_prompt, format="json")
                data = json.loads(response)
                # Map back to internal ID format if needed or return suggestions
                return data.get("suggestions", [])
            except Exception as e:
                print(f"[IdentityManager] LLM detection failed: {e}")

        # 3. Simple heuristic fallback: match by display_name
        candidates = []
        for i, id1 in enumerate(identities):
            for id2 in identities[i+1:]:
                if id1['user_id'] == id2['user_id']:
                    continue
                
                name1 = (id1['display_name'] or "").lower()
                name2 = (id2['display_name'] or "").lower()
                
                if name1 and name2 and (name1 == name2 or name1 in name2 or name2 in name1):
                    candidates.append({
                        "identity1_id": id1['id'],
                        "identity2_id": id2['id'],
                        "confidence": 0.7,
                        "reason": f"Similar display names: {id1['display_name']} ≈ {id2['display_name']}"
                    })
        
        return candidates

if __name__ == "__main__":
    from src.core.database import DatabaseManager
    
    db = DatabaseManager()
    manager = IdentityManager(db)
    
    print("[Test] Getting pending merge requests...")
    requests = manager.get_pending_merge_requests()
    print(f"[Test] Found {len(requests)} pending requests")
