import math
import time
from typing import List, Dict, Any

class AlayaReranker:
    """
    Biological re-ranking engine for Rito AI's memories.
    Implements: Forgetting Curve (Ebbinghaus), Emotional Bias, and Stability Fixation.
    """
    
    def __init__(self, weights: Dict[str, float] = None):
        # Default weights for reranking
        self.weights = weights or {
            "similarity": 0.5,
            "retrievability": 0.3,
            "emotion": 0.2
        }
        # Decay constant alpha for stability fixation
        self.fixation_alpha = 0.1 

    def calculate_score(self, memory: Dict[str, Any], query_similarity: float) -> float:
        """
        Calculates the final 'Recall Score' for a given memory.
        """
        now = time.time()
        
        # 1. Similarity (S) - already provided from vector search
        S = query_similarity
        
        # 2. Retrievability (R) - Forgetting Curve logic
        # R = exp(- delta_t / stability)
        last_ts = memory.get('last_accessed_at') or memory.get('timestamp') or now
        delta_t = max(0, now - last_ts)
        # Convert delta_t to hours or days for more meaningful decay? 
        # Let's use hours for now. (delta_t / 3600)
        stability = memory.get('stability') or 1.0
        R = math.exp(-(delta_t / 3600.0) / stability)
        
        # 3. Emotional Intensity (E)
        E = abs(memory.get('sentiment_score') or 0.0)
        # Add bonus for specific high-intensity emotion tags if available
        # (This is simplified for now)
        
        # Final Score
        total_score = (self.weights["similarity"] * S) + \
                      (self.weights["retrievability"] * R) + \
                      (self.weights["emotion"] * E)
                      
        return total_score

    def rerank(self, memories: List[Dict[str, Any]], query_similarities: List[float]) -> List[Dict[str, Any]]:
        """
        Reranks a list of memories based on biological scores.
        """
        scored_memories = []
        for i, memory in enumerate(memories):
            similarity = query_similarities[i]
            score = self.calculate_score(memory, similarity)
            
            # Add calculated score in-place to dict for logging/display
            mem_with_score = dict(memory)
            mem_with_score['_alaya_score'] = score
            mem_with_score['_retrievability'] = math.exp(-( (time.time() - (memory.get('last_accessed_at') or memory.get('timestamp') or time.time())) / 3600.0) / (memory.get('stability') or 1.0))
            scored_memories.append(mem_with_score)
            
        # Sort by total score descending
        return sorted(scored_memories, key=lambda x: x['_alaya_score'], reverse=True)

    def update_stability(self, current_stability: float, recall_count: int) -> float:
        """
        Updates memory stability based on recall (Fixation).
        """
        # Stability increases when remembered
        return current_stability * (1.0 + self.fixation_alpha)
