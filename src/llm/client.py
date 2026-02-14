from typing import List, Dict, Any, Optional
import json
import requests
import os

class LLMClient:
    """
    OllamaクライアントでLLM APIとやり取りする
    """
    def __init__(self, model: str = None):
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        # Use environment variable or provided model or default
        self.model = model or os.getenv("ROUTER_MODEL", "qwen2.5:7b")
        
    def generate(self, prompt: str, format: str = None) -> str:
        """
        Sends a request to the Ollama API.
        """
        url = f"{self.ollama_url}/api/chat"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False
        }

        if json_mode:
            payload["format"] = "json"

        try:
            print(f"[LLM] Requesting completion from {self.model_name}...")
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            content = result.get("message", {}).get("content", "")
            print(f"[LLM] Raw Content: {content}")
            return content

        except requests.exceptions.ConnectionError:
            print("[LLM] Error: Could not connect to Ollama. Is it running on port 11434?")
            return "{}" # Return empty JSON to avoid crash in parse
        except Exception as e:
            print(f"[LLM] Error: {e}")
            return "{}"

    def get_embedding(self, text: str, model: str = None) -> List[float]:
        """
        Generates an embedding vector for the given text using Ollama.
        """
        url = f"{self.ollama_url}/api/embeddings"
        embed_model = model or os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
        
        payload = {
            "model": embed_model,
            "prompt": text
        }
        
        try:
            print(f"[LLM] Generating embedding using {embed_model}...")
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            return result.get("embedding", [])
        except Exception as e:
            print(f"[LLM] Embedding Error: {e}")
            return []

    def parse_tool_request(self, response: str) -> Optional[Dict[str, Any]]:

        """
        Parses the JSON response from the LLM into a dictionary.
        """
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            print(f"[LLM] Failed to parse JSON response: {response}")
            return None
