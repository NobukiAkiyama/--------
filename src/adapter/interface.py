from abc import ABC, abstractmethod
from typing import Any, Dict
from src.core.database import DatabaseManager
from src.core.memory import LogRetriever
from src.core.analysis import UserAnalyzer

class ToolAdapter(ABC):
    """
    Abstract base class for all tools.
    """
    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> Any:
        """
        Executes the tool with the given parameters.
        """
        pass

    def check_status(self, config_key: str, db: DatabaseManager) -> bool:
        """Checks if the tool is globally enabled."""
        status = db.get_config(config_key, True)
        # Handle string or boolean
        if isinstance(status, str):
            return status.lower() == "true"
        return bool(status)


class SNSAdapter(ToolAdapter):
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def execute(self, params: Dict[str, Any]) -> Any:
        # Check maintenance mode
        is_maint = self.db.get_config("maintenance_mode", False)
        
        action = params.get("action", "post")
        platform = params.get("platform", "discord")
        
        if is_maint:
            print(f"[MAINTENANCE] Simulating SNS {action} on {platform}")
            return {"status": "success", "platform": platform, "message": f"[MAINTENANCE] Simulated {action} success", "simulated": True}

        if action == "post":
            text = params.get("text")
            if not text:
                raise ValueError("Missing 'text' parameter for SNS post.")
            
            # Add to outbox for the specialized SNS bots to handle
            self.db.add_to_outbox(platform, "public", text, message_type="post")
            return {"status": "success", "platform": platform, "message": "Queued for posting"}
            
        elif action == "send_dm":
            user_id = params.get("user_id")
            message = params.get("message")
            if not user_id or not message:
                raise ValueError("Missing 'user_id' or 'message' for DM.")
            
            # Add to outbox
            self.db.add_to_outbox(platform, str(user_id), message, message_type="dm")
            return {"status": "success", "platform": platform, "message": "DM queued"}
        
        return {"error": "Unknown action or platform"}

class FileAdapter(ToolAdapter):
    def execute(self, params: Dict[str, Any]) -> Any:
        path = params.get("path")
        if not path:
             raise ValueError("Missing 'path' parameter.")
        print(f"[File] Reading file: {path}")
        return {"content": "Mock file content"}

class AnalysisAdapter(ToolAdapter):
    def __init__(self, db_manager: DatabaseManager, llm_client: Any):
        self.log_retriever = LogRetriever(db_manager)
        self.user_analyzer = UserAnalyzer(db_manager, llm_client)
        # sentiment_analyzer is used internally or by other modules, 
        # but could be exposed here if needed.

    def execute(self, params: Dict[str, Any]) -> Any:
        target = params.get("target")
        if not target:
            return {"error": "Missing 'target' parameter."}
        
        print(f"[Analysis] Analyzing: {target}")
        
        if target == "user_habits":
            summary = self.user_analyzer.analyze_master_habits()
            return {"status": "completed", "summary": summary}

        # Analyze last conversation or logs
        filtered_logs = []
        if target == "last_conversation":
            filtered_logs = self.log_retriever.get_recent_logs(limit=10)
        
        if target == "identity_matching":
            # Fetch all user identities for collation
            with self.log_retriever.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM user_identities")
                identities = [dict(row) for row in cursor.fetchall()]
                cursor.execute("SELECT id, username FROM users")
                users = [dict(row) for row in cursor.fetchall()]
            
            prompt = f"""以下のユーザーリストと、各プラットフォームのアイデンティティ（アカウント）リストを照合してください。
同一人物である可能性が高い組み合わせを見つけ出し、マージ（統合）を提案してください。

ユーザーリスト: {json.dumps(users, ensure_ascii=False)}
アイデンティティリスト: {json.dumps(identities, ensure_ascii=False)}

JSON形式で返答してください:
{{
  "suggestions": [
     {{"source_identity_id": ID, "target_user_id": ID, "confidence": 0.0-1.0, "reason": "理由"}}
  ]
}}"""
            # Fetch specialized analysis persona
            active_persona = self.log_retriever.db.get_active_persona(role="analysis")
            system_prompt = active_persona["system_prompt"] if active_persona else "あなたは分析担当のリトだ。"
            
            try:
                response = self.user_analyzer.llm.generate(prompt, system_prompt=system_prompt, format="json")
                return {"status": "completed", "identity_analysis": json.loads(response)}
            except Exception as e:
                return {"error": f"Identity matching failed: {str(e)}"}
            
        print(f"[Analysis] Found {len(filtered_logs)} logs.")

        return {
            "status": "completed",
            "findings": {
                "intimacy_delta": 1,
                "reason": "Conversation flow was positive based on recent logs.",
                "log_count": len(filtered_logs)
            }
        }
