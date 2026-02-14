"""
Relationship Analyzer - Phase 3
Automatically suggests relationship tags based on conversation logs
"""
from typing import Dict, List, Any
import json

class RelationshipAnalyzer:
    """Analyzes user logs to suggest relationship tags"""
    
    def __init__(self, db_manager, llm_client):
        self.db = db_manager
        self.llm = llm_client
    
    def analyze_relationship(self, user_id: int) -> Dict[str, Any]:
        """
        Analyze a user's conversation history and suggest relationship tags.
        
        Returns:
            {
                "tags": ["👔 上司", "🤝 同僚"],
                "confidence": 0.87,
                "reason": "敬語使用率92%、指示を仰ぐパターン検出"
            }
        """
        # Get user's conversation logs
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get memories related to this user
            cursor.execute("""
                SELECT content, emotion_tags, timestamp 
                FROM memories 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 50
            """, (user_id,))
            memories = cursor.fetchall()
            
            # Get user info
            cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
        
        if not memories or not user:
            return {
                "tags": [],
                "confidence": 0.0,
                "reason": "No conversation history found"
            }
        
        # Format logs for LLM
        logs_text = "\n".join([
            f"[{m['timestamp']}] {m['content']} (emotion: {m['emotion_tags']})"
            for m in memories[:20]  # Use latest 20
        ])
        
        # Get Active Persona (Analysis)
        active_persona = self.db.get_active_persona(role="analysis")
        system_prompt = active_persona["system_prompt"] if active_persona else "あなたは分析担当のAIリトだ。"
        
        prompt = f"""以下のユーザー「{user['username']}」との会話ログを分析し、社会的関係性を判定してください。

会話ログ:
{logs_text}

以下のカテゴリから適切なタグを1〜3個選択してください:
- 上位階層: 👑 マスター, 👔 上司, 🎓 先生, 👨‍👩‍👧 保護者
- 同等階層: 🤝 同僚, 👥 友人, 🎮 仲間, 💍 パートナー
- 下位階層: 🔧 部下, 📚 生徒, 👶 子供, 🤖 アシスタント
- 特殊関係: ❤️ 家族, 🌟 VIP, ⚠️ 要注意, 🚫 ブロック

JSON形式で返答してください:
{{
  "tags": ["選択したタグ"],
  "confidence": 0.0〜1.0の信頼度,
  "reason": "判定理由（日本語、簡潔に）"
}}"""
        
        try:
            response = self.llm.generate(prompt, system_prompt=system_prompt)
            # Try to extract JSON from response
            if "{" in response:
                json_start = response.index("{")
                json_end = response.rindex("}") + 1
                result = json.loads(response[json_start:json_end])
                return result
            else:
                return {
                    "tags": [],
                    "confidence": 0.0,
                    "reason": "LLM response parse error"
                }
        except Exception as e:
            print(f"[RelationshipAnalyzer] Error: {e}")
            return {
                "tags": [],
                "confidence": 0.0,
                "reason": f"Analysis error: {str(e)}"
            }
    
    def get_all_suggestions(self) -> List[Dict[str, Any]]:
        """Get tag suggestions for all users with conversation history"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT user_id 
                FROM memories 
                WHERE user_id IS NOT NULL
            """)
            users = cursor.fetchall()
        
        suggestions = []
        for user in users:
            user_id = user['user_id']
            analysis = self.analyze_relationship(user_id)
            if analysis['tags']:
                suggestions.append({
                    "user_id": user_id,
                    "analysis": analysis
                })
        
        return suggestions

if __name__ == "__main__":
    from src.core.database import DatabaseManager
    from src.llm.client import LLMClient
    
    db = DatabaseManager()
    llm = LLMClient()
    analyzer = RelationshipAnalyzer(db, llm)
    
    # Test with user_id=1 if exists
    result = analyzer.analyze_relationship(1)
    print(f"[Test] Analysis result: {json.dumps(result, indent=2, ensure_ascii=False)}")
