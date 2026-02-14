import json
import time
from src.core.database import DatabaseManager
from src.core.memory import LogRetriever
from src.llm.client import LLMClient

def test_biomemory():
    print("--- Starting Biological Memory Verification ---")
    db = DatabaseManager()
    llm = LLMClient()
    retriever = LogRetriever(db, llm)
    
    # 1. Test save_memory with HLM features
    print("[Test 1] Saving a high-emotion memory...")
    content = "マスターが新しいメモリーシステムを褒めてくれた！最高に嬉しい。"
    mid = db.save_memory(
        content=content,
        user_id=1,
        sentiment=0.8,
        emotions=["happy", "joy"],
        memory_type="chat"
    )
    print(f"Memory saved with ID: {mid}")
    
    # 2. Test semantic search + Alaya reranking
    print("[Test 2] Searching for memories about 'praise' or 'feelings'...")
    results = retriever.get_semantic_memories(query="褒められた時の気持ち", limit=3)
    
    for m in results:
        print(f"- Content: {m['content']}")
        print(f"  Similarity: (calculated in rerank)")
        print(f"  Alaya Score: {m.get('_alaya_score', 0.0):.4f}")
        print(f"  Retrievability: {m.get('_retrievability', 0.0):.4f}")
    
    # 3. Test Character Card registration
    print("[Test 3] Registering a Character Card...")
    card = {
        "identity": {"name": "TestRito", "nickname": "T-Rito"},
        "behavior": {
            "personality": "Strict and testing.",
            "system_prompt": "You are a test人格。",
            "post_history_instructions": "Verify all results strictly."
        }
    }
    db.register_character_card(card, role="router", active=True)
    print("Character Card registered.")
    
    # 4. Verify loading in Router context
    persona = db.get_active_persona(role="router")
    print(f"Active Persona: {persona['name']}")
    if persona.get('metadata_json'):
        meta = json.loads(persona['metadata_json'])
        print(f"Metadata instructions: {meta.get('behavior', {}).get('post_history_instructions')}")

if __name__ == "__main__":
    test_biomemory()
