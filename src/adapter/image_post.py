from src.adapter.interface import ToolAdapter
from typing import Dict, Any

class ImagePostAdapter(ToolAdapter):
    def execute(self, params: Dict[str, Any]) -> Any:
        image_data = params.get("image_base64")
        text = params.get("text", "")
        
        if not image_data:
            return {"error": "No image data provided."}
            
        # Mock posting logic
        print(f"[SNS] Posting image with text: {text}")
        # In real impl, decode base64 and upload to Bluesky/Twitter
        
        return {"status": "success", "platform": "bluesky_mock"}
