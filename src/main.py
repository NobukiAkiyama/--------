import time
import json
from src.core.state_manager import StateManager
from src.controller.policy import Controller, ToolRequest
from src.llm.client import LLMClient
from src.adapter.interface import SNSAdapter, FileAdapter, AnalysisAdapter
from src.adapter.vision import VisionAdapter
from src.adapter.image_post import ImagePostAdapter
from src.adapter.local_chat import LocalChatAdapter
from src.adapter.goose import GooseAdapter
from src.adapter.search import SearchAdapter

from src.core.database import DatabaseManager
from src.core.memory import LogRetriever

class RitoAI:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.llm_client = LLMClient()
        self.log_retriever = LogRetriever(self.db_manager, self.llm_client)
        self.state_manager = StateManager()
        self.controller = Controller(self.db_manager)

        self.llm_client = LLMClient()
        self.adapters = {
            "post_sns": SNSAdapter(self.db_manager),
            "read_file": FileAdapter(),
            "call_analysis": AnalysisAdapter(self.db_manager, self.llm_client),
            "see_screen": VisionAdapter(self.db_manager), 
            "post_image": ImagePostAdapter(),
            "local_chat": LocalChatAdapter(),
            "goose_code": GooseAdapter(self.db_manager),
            "search_web": SearchAdapter(),
        }
        # In the future, we can systematically update all adapters to accept db_manager
        print("[System] Rito AI V2.0 Initialized.")

    def run_cycle(self):
        """
        Executes one cycle of the agent's life.
        """
        # 1. Update Internal State
        current_state = self.state_manager.update()
        print(f"[State] Anger: {current_state.anger:.2f}, Fatigue: {current_state.fatigue:.2f}")

        # 2. Check for Pending Events (Priority Queue)
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM pending_events WHERE processed = 0 ORDER BY priority_score DESC, timestamp ASC LIMIT 1"
            )
            event = cursor.fetchone()
            
        event_info = "なし"
        if event:
            event = dict(event)
            payload = json.loads(event['payload'])
            event_info = f"タイプ: {event['source_type']}, 内容: {payload.get('content', '情報なし')}, 送信者: {payload.get('username', '不明')}"
            print(f"[Queue] Processing event: {event['source_type']} from {payload.get('username')}")

        # 3. Get Active Persona (Router)
        active_persona = self.db_manager.get_active_persona(role="router")
        if not active_persona:
            print("[System] No active router persona found.")
            return

        # 4. Context: Person-specific memories (Alaya)
        memories = []
        if event and 'username' in payload:
            user = self.db_manager.get_user(payload['username'])
            if user:
                # Get biology-inspired semantic memories
                memories = self.log_retriever.get_semantic_memories(
                    query=payload.get('content', ''),
                    user_id=user['id'],
                    limit=3
                )

        memory_context = ""
        if memories:
            memory_context = "\n関連する記憶:\n" + "\n".join([f"- {m['content']} (想起スコア: {m['_alaya_score']:.2f})" for m in memories])

        # 5. Ask LLM for Action Proposal based on State
        system_prompt = active_persona["system_prompt"]
        
        # Influence prompt with Character Card metadata if exists
        if active_persona.get("metadata_json"):
            try:
                card = json.loads(active_persona["metadata_json"])
                # Could add scenario or post_history_instructions
                instr = card.get("behavior", {}).get("post_history_instructions", "")
                if instr:
                    system_prompt += f"\n\n追加指令: {instr}"
            except:
                pass

        prompt = f"""
        現在の状態: 怒り={current_state.anger:.2f}, Fatigue={current_state.fatigue:.2f}
        外部イベント: {event_info}
        {memory_context}
        目的: 状況に応じた最適な行動を選択してください。
        利用可能なツール: {list(self.adapters.keys())} ("idle" も含む)
        
        思考プロセスを日本語で簡潔に記述し、実行するツールを選択せよ。
        """
        
        response_json = self.llm_client.generate_response(prompt, system_prompt, json_mode=True)
        
        request_dict = self.llm_client.parse_tool_request(response_json)
        if not request_dict:
            print("[System] Invalid JSON from LLM.")
            return

        # Execute Tool (if valid)
        if request_dict:
            # Mark event as processed if it was handled
            if event:
                with self.db_manager.get_connection() as conn:
                    conn.execute("UPDATE pending_events SET processed = 1 WHERE id = ?", (event['id'],))
                    conn.commit()

        # Execute Tool (if valid)
        if request_dict:
            # Policy Check
            tool_req = ToolRequest(
                tool_name=request_dict["tool"],
                parameters=request_dict["params"],
                reason=request_dict.get("reason", "No reason provided")
            )
            
            if self.controller.check_policy(tool_req):
                tool_name = request_dict["tool"]
                params = request_dict["params"]
                
                if tool_name == "goose_code":
                    # 1. Technical Advisor (Goose) generates a proposal
                    proposal_result = self.adapters["goose_code"].execute(params)
                    
                    # 2. Execution Authority (Controller) validates and executes in Docker
                    final_result = self.controller.execute_technical_proposal(proposal_result)
                    print(f"[Execution] Proposal result: {final_result}")
                    
                elif tool_name in self.adapters:
                    result = self.adapters[tool_name].execute(params)
                    print(f"[Execution] Result: {result}")
                    
                    # --- Master Action Logging Logic ---
                    if tool_name == "see_screen" and "content" in result:
                        self.db_manager.log_master_action(
                            activity_type="vision_analysis", 
                            detail=result["content"]
                        )
                    # -----------------------------------
                
                elif tool_name == "idle":
                    duration = params.get("duration", 30)
                    print(f"[Router] Decided to IDLE for {duration} seconds.")
                    time.sleep(duration)
                    return
                
                else:
                    print(f"[Execution] Error: Tool {tool_name} not found.")
            else:
                print(f"[Controller] Denied: {request_dict}")


    def run_loop(self, interval: int = 10):
        print("[System] Starting autonomous loop...")
        try:
            while True:
                print(f"\n--- Cycle Start ({time.ctime()}) ---")
                self.run_cycle()
                
                # Dynamic Logic: If Fatigue is high, sleep longer?? 
                # For now, we trust the 'idle' tool to handle long waits.
                # Only add short baseline wait here.
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("[System] Shutdown.")

if __name__ == "__main__":
    ai = RitoAI()
    # Run once for testing
    ai.run_cycle()
