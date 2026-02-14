import json
from typing import Dict, Any, List, Optional
from src.core.database import DatabaseManager
from src.llm.client import LLMClient

class SentimentAnalyzer:
    """
    Analyzes text to extract sentiment and emotion tags.
    """
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analyzes a single text string.
        Returns: {"sentiment": "positive"|"neutral"|"negative", "emotion_tags": ["happy", "excited"]}
        """
        prompt = f"""
        Analyze the sentiment of the following text.
        Text: "{text}"
        
        Output JSON only:
        {{
            "sentiment": "positive|neutral|negative",
            "score": float (-1.0 to 1.0),
            "emotions": ["list", "of", "emotions"]
        }}
        """
        response = self.llm.generate(prompt, format="json")
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            print(f"[Analysis] JSON Decode Error: {response}")
            return {"sentiment": "neutral", "score": 0.0, "emotions": []}

class UserAnalyzer:
    """
    Analyzes user behavior logs (master_actions) to build profiles.
    """
    def __init__(self, db_manager: DatabaseManager, llm_client: LLMClient):
        self.db = db_manager
        self.llm = llm_client

    def analyze_master_habits(self) -> str:
        """
        Summarizes master's recent actions.
        """
        # Fetch recent master actions
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM master_actions ORDER BY timestamp DESC LIMIT 50")
            rows = cursor.fetchall()
            
        if not rows:
            return "No recent master actions found."
            
        logs = "\n".join([f"- [{row['timestamp']}] {row['activity_type']}: {row['detail']}" for row in rows])
        
        prompt = f"""
        Analyze the following log of the user's (Master's) recent actions.
        Identify patterns, habits, and current state.
        
        Logs:
        {logs}
        
        Output a brief summary in Japanese (e.g., "Master has been coding Python for 3 hours and seems tired.").
        """
        return self.llm.generate(prompt)

    def find_anti_learning_topics(self) -> List[str]:
        """
        Identifies topics that caused negative reactions.
        """
        # Logic to fetch negative memories and extract topics
        # Placeholder for now
        return []
