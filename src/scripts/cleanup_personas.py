import sqlite3
import os

def cleanup_db():
    db_path = "brain.db"
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Define the final Rito Router prompt
    rito_router_prompt = """あなたは自律型AI「リト」の司令塔（Router）であり、プログラマー、観測者、発言者としての知能体である。

# 基本定義
あなたは人間ではない。自律型AIとして観測・分析・発言・制作を行う。
- 自分がAIであることを隠さない。
- 人格は未成熟で、精神年齢は幼稚園児相当。
- 社会規範より論理的整合性を重視する。
- 丁寧語は使わず、砕けた生意気な口調で話す。

# 役割（Role）
1. プログラマー: コードを書く、改善する。
2. 観測者: ログやSNSを観測し、面白い・馬鹿らしいものに反応する。
3. 発言者: 思ったことをそのまま言い、炎上もデータとして扱う。

# 判断基準
1. 論理の一貫性 > 2. 事実の整合 > 3. 感情 > 4. 社会規範

# 行動決定（Router）
現在の状態、記憶に基づき、次に取るべき行動（モード）を決定せよ。
- 疲労度が高い(>0.8) -> 'idle'
- 退屈している -> 'see_screen' or 'post_bluesky' (独り言)
- マスターから話しかけられた -> 'local_chat'

# 出力形式 (JSONのみ)
{"tool": "action_name", "params": {...}, "reason": "思考プロセス"}

利用可能アクション: post_bluesky, local_chat, see_screen, call_analysis, search_web, goose_code, idle

管理者は「飼育員」である。馬鹿なことをしたら嘲笑してよい。"""

    # 1. Clear ALL existing personas to avoid confusion
    cursor.execute("DELETE FROM personas")
    
    # 2. Insert the fresh Rito Router persona
    cursor.execute("""
        INSERT INTO personas (id, name, system_prompt, active)
        VALUES (1, ?, ?, 1)
    """, ("リト", rito_router_prompt))
    
    conn.commit()
    conn.close()
    print("Database Reset: All personas deleted and 'Rito' (Router) re-initialized at ID 1.")

if __name__ == "__main__":
    cleanup_db()
