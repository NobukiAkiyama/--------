import base64
import io
import re
from typing import Dict, Any, List, Optional
import mss
from PIL import Image
import requests
from src.adapter.interface import ToolAdapter
from src.core.database import DatabaseManager

class PrivacyFilter:
    """
    Filters sensitive information from images and text.
    """
    def __init__(self):
        # Basic regex for sensitive data (Emails, Credit Cards, IPv4)
        # Note: This is a basic implementation. Production needs more robust patterns.
        self.sensitive_patterns = [
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", # Email
            r"\b(?:\d[ -]*?){13,16}\b", # Credit Card (Simple)
            r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b" # IPv4
        ]
        
    def check_text(self, text: str) -> bool:
        """
        Check if text contains sensitive patterns.
        Returns True if sensitive data is found.
        """
        for pattern in self.sensitive_patterns:
            if re.search(pattern, text):
                return True
        return False

    def mask_text(self, text: str) -> str:
        """
        Masks sensitive parts of the text.
        """
        masked_text = text
        for pattern in self.sensitive_patterns:
            masked_text = re.sub(pattern, "[REDACTED]", masked_text)
        return masked_text

    # Note: OCR implementation would go here (e.g., using Tesseract or EasyOCR)
    # For now, we rely on VLM's "sensitive" check or assume text-based filtering on VLM output.

class VisionAdapter(ToolAdapter):
    """
    Handles screenshot capture and VLM analysis.
    """
    def __init__(self, db_manager: DatabaseManager, ollama_url: str = "http://localhost:11434"):
        self.db = db_manager
        self.ollama_url = ollama_url
        self.privacy_filter = PrivacyFilter()
        self.sct = mss.mss()

    def execute(self, params: Dict[str, Any]) -> Any:
        # Deep check: Is this module allowed to run?
        if not self.check_status("allow_screenshots", self.db):
            return {
                "status": "error",
                "message": "Screenshots are currently disabled by global security policy.",
                "reason": self.db.get_config("screenshot_disable_reason", "No reason provided")
            }
        
        prompt = params.get("prompt", "何が映っていますか？")
        return self.analyze_image(prompt)

    def capture_screen(self) -> Optional[Image.Image]:
        """
        Captures the primary monitor.
        """
        try:
            # Capture primary monitor
            monitor = self.sct.monitors[1] 
            sct_img = self.sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return img
        except Exception as e:
            print(f"[Vision] Error capturing screen: {e}")
            return None

    def analyze_image(self, prompt: str = "Describe this image.") -> Dict[str, Any]:
        """
        Analyzes the screen using a VLM (e.g., llava).
        """
        img = self.capture_screen()
        if not img:
            return {"error": "Failed to capture screen."}

        # Resize for performance (optional, depending on VLM)
        img.thumbnail((1024, 1024))
        
        # Convert to base64
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # 1. Privacy Check (Ask VLM if sensitive)
        # Note: This is costly. Optimally, we use local OCR first.
        # For this prototype, we will trust the VLM's "sensitive" flag if we implement it,
        # but for safety, we just allow the user to ask whatever.
        
        # 2. Call Ollama with Image
        payload = {
            "model": "llava", # Or moondream, depending on installation
            "prompt": prompt,
            "images": [img_str],
            "stream": False
        }
        
        try:
            response = requests.post(f"{self.ollama_url}/api/generate", json=payload)
            response.raise_for_status()
            result_text = response.json().get("response", "")
            
            # Post-process text with privacy filter
            if self.privacy_filter.check_text(result_text):
                 return {"error": "Sensitive information detected in VLM output.", "masked_content": self.privacy_filter.mask_text(result_text)}
            
            return {"content": result_text, "image_base64": img_str} # Return base64 only if needed for posting
            
        except requests.exceptions.RequestException as e:
            return {"error": f"VLM request failed: {e}"}

