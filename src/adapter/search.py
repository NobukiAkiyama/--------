import requests
from typing import Dict, Any, List, Optional
import os

class SearchAdapter:
    """
    Web search adapter with dual strategy:
    1. Ollama native web_search (primary, requires newer Ollama)
    2. DuckDuckGo search (fallback, always available)
    """
    def __init__(self, ollama_url: Optional[str] = None):
        self.ollama_url = ollama_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.use_ollama_search = True  # Try Ollama first
        
        # Lazy import for fallback
        self.ddg = None
    
    def _init_ddg(self):
        """Lazy initialize DuckDuckGo search"""
        if self.ddg is None:
            try:
                from duckduckgo_search import DDGS
                self.ddg = DDGS()
                print("[Search] DuckDuckGo search initialized")
            except ImportError:
                print("[Search] Warning: duckduckgo-search not installed. Run: pip install duckduckgo-search")
    
    def search_with_ollama(self, query: str, model: str = "qwen2.5:7b") -> Optional[str]:
        """
        Search using Ollama's native web_search capability.
        Returns None if not supported or on error.
        """
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": f"Search the web and answer: {query}",
                    "web_search": True,  # Enable native web search
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                print(f"[Search] Ollama web search failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"[Search] Ollama web search error: {e}")
            return None
    
    def search_with_duckduckgo(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Fallback search using DuckDuckGo.
        Returns list of search results with title, url, and snippet.
        """
        self._init_ddg()
        
        if self.ddg is None:
            return []
        
        try:
            results = self.ddg.text(query, max_results=max_results)
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                }
                for r in results
            ]
        except Exception as e:
            print(f"[Search] DuckDuckGo search error: {e}")
            return []
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute web search.
        
        Params:
            - query: str - Search query
            - max_results: int - Maximum results (for DDG fallback, default: 5)
            - use_llm: bool - If True, use Ollama to summarize results (default: True)
        
        Returns:
            - results: list or str - Search results
            - source: str - "ollama" or "duckduckgo"
        """
        query = params.get("query")
        if not query:
            return {"error": "Missing 'query' parameter"}
        
        max_results = params.get("max_results", 5)
        use_llm = params.get("use_llm", True)
        
        print(f"[Search] Searching for: {query}")
        
        # Strategy 1: Try Ollama native web search
        if self.use_ollama_search and use_llm:
            ollama_result = self.search_with_ollama(query)
            if ollama_result:
                return {
                    "status": "success",
                    "results": ollama_result,
                    "source": "ollama_native",
                    "query": query
                }
        
        # Strategy 2: Fallback to DuckDuckGo
        ddg_results = self.search_with_duckduckgo(query, max_results)
        
        if not ddg_results:
            return {
                "error": "No search results found",
                "query": query
            }
        
        # If use_llm, summarize DDG results with Ollama
        if use_llm:
            summary_prompt = f"""以下の検索結果を要約してください。

検索クエリ: {query}

検索結果:
{chr(10).join([f"{i+1}. {r['title']}: {r['snippet']}" for i, r in enumerate(ddg_results)])}

要約:"""
            
            try:
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": "qwen2.5:7b",
                        "prompt": summary_prompt,
                        "stream": False
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    summary = response.json().get("response", "")
                    return {
                        "status": "success",
                        "results": summary,
                        "raw_results": ddg_results,
                        "source": "duckduckgo_with_llm",
                        "query": query
                    }
            except Exception as e:
                print(f"[Search] LLM summarization failed: {e}")
        
        # Return raw DDG results
        return {
            "status": "success",
            "results": ddg_results,
            "source": "duckduckgo",
            "query": query
        }

if __name__ == "__main__":
    # Test search
    adapter = SearchAdapter()
    
    result = adapter.execute({
        "query": "最新のAI技術トレンド",
        "max_results": 3
    })
    
    print(f"\n[Test] Search result: {result}")
