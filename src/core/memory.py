import sqlite3
import time
import json
import struct
from typing import List, Dict, Any, Optional
from src.core.database import DatabaseManager
from src.core.memory_reranker import AlayaReranker
from src.llm.client import LLMClient

class LogRetriever:
    """
    Retrieves and filters logs/memories from the database.
    Act as a read-only interface for Analysis LLM.
    """
    def __init__(self, db_manager: DatabaseManager, llm_client: Optional[LLMClient] = None):
        self.db_manager = db_manager
        self.llm = llm_client or LLMClient()
        self.reranker = AlayaReranker()

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(v1, v2))
        magnitude1 = sum(a * a for a in v1) ** 0.5
        magnitude2 = sum(a * a for a in v2) ** 0.5
        if not magnitude1 or not magnitude2:
            return 0.0
        return dot_product / (magnitude1 * magnitude2)

    def _decode_vector(self, blob: bytes) -> List[float]:
        if not blob:
            return []
        # Assuming FLOAT32 array
        count = len(blob) // 4
        return list(struct.unpack(f'{count}f', blob))

    def get_recent_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent N actions logs.
        """
        with self.db_manager.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM actions_log ORDER BY timestamp DESC LIMIT ?", 
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_logs_by_time_range(self, start_ts: float, end_ts: float) -> List[Dict[str, Any]]:
        """
        Get logs within a specific time range.
        """
        with self.db_manager.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM actions_log WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp ASC",
                (start_ts, end_ts)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_user_memories(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get specific memories related to a user.
        """
        with self.db_manager.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM memories WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_semantic_memories(self, query: str, user_id: Optional[int] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves memories using semantic search and Alaya biological reranking.
        """
        # 1. Get embedding for query
        query_vec = self.llm.get_embedding(query)
        if not query_vec:
            # Fallback to keyword search? or just return empty
            return self.get_user_memories(user_id, limit) if user_id else []

        # 2. Fetch candidates from DB
        all_memories = []
        with self.db_manager.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute("SELECT * FROM memories WHERE user_id = ?", (user_id,))
            else:
                cursor.execute("SELECT * FROM memories")
            
            all_memories = [dict(row) for row in cursor.fetchall()]

        if not all_memories:
            return []

        # 3. Calculate similarities
        similarities = []
        for mem in all_memories:
            mem_vec = self._decode_vector(mem.get('embedding_vector'))
            sim = self._cosine_similarity(query_vec, mem_vec)
            similarities.append(sim)

        # 4. Rerank using Alaya Engine (Biological factor)
        reranked = self.reranker.rerank(all_memories, similarities)
        
        # 5. Take top N and update their fixation (stability)
        top_results = reranked[:limit]
        
        self._update_memory_fixation([m['id'] for m in top_results])
        
        return top_results

    def _update_memory_fixation(self, memory_ids: List[int]):
        """
        Update stability and access time for retrieved memories.
        """
        now = time.time()
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            for mid in memory_ids:
                # Fetch current stability
                cursor.execute("SELECT stability, recall_count FROM memories WHERE id = ?", (mid,))
                row = cursor.fetchone()
                if row:
                    new_stability = self.reranker.update_stability(row['stability'] or 1.0, row['recall_count'] or 0)
                    cursor.execute("""
                        UPDATE memories 
                        SET stability = ?, last_accessed_at = ?, recall_count = recall_count + 1 
                        WHERE id = ?
                    """, (new_stability, now, mid))
            conn.commit()

    def search_logs(self, keyword: str) -> List[Dict[str, Any]]:

        """
        Simple keyword search in logs.
        """
        with self.db_manager.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # Note: This is a simple LIKE search. For production, consider FTS5.
            param = f"%{keyword}%"
            cursor.execute(
                "SELECT * FROM actions_log WHERE detail LIKE ? OR reason LIKE ? ORDER BY timestamp DESC LIMIT 20",
                (param, param)
            )
            return [dict(row) for row in cursor.fetchall()]
