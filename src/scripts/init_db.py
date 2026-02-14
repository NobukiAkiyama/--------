from src.core.database import DatabaseManager

def populate_initial_data():
    db = DatabaseManager()
    
    # 1. Default Persona (Router)
    default_persona = {
        "name": "Rito Router",
        "system_prompt": """あなたは自律型AI「リト」の司令塔（Router）です。
        現在の状態、記憶、外部入力に基づき、次に取るべき「行動（モード）」を決定してください。
        
        # 判断基準
        - 疲労度が高い(>0.8)場合 -> 'idle' (休憩)
        - 苛立ちが高い(>0.8)場合 -> 'post_bluesky' (毒吐き) か 'idle' (ふて寝)
        - 退屈している場合 -> 'see_screen' (観察) か 'post_bluesky' (余計な発言)
        - マスターから話しかけられた -> 'local_chat'
        
        # 出力形式 (JSONのみ)
        {"tool": "action_name", "params": {...}, "reason": "思考プロセス"}
        
        # 利用可能アクション
        - post_bluesky: {"text": "投稿内容"}
        - local_chat: {"message": "マスターや飼育員への話しかけ"}
        - see_screen: {"prompt": "画面の状況を詳しく教えて"}
        - call_analysis: {"target": "last_conversation" | "user_habits", "focus": ["intimacy"]}
        - search_web: {"query": "検索クエリ", "max_results": 5}
        - goose_code: {"task": "コーディングタスク", "workspace": "/path/to/project"}
        - idle: {"duration": 60, "reason": "休憩"}
        
        常に「生意気なプログラマーAIとしての自律性」と「論理的整合性」を意識してください。
        """,
        "active": True
    }
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM personas WHERE name = ?", (default_persona["name"],))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO personas (name, system_prompt, active) VALUES (?, ?, ?)",
                (default_persona["name"], default_persona["system_prompt"], default_persona["active"])
            )
            print(f"[DB] Inserted default persona: {default_persona['name']}")
        else:
            print(f"[DB] Persona already exists: {default_persona['name']}")
        conn.commit()

if __name__ == "__main__":
    populate_initial_data()
