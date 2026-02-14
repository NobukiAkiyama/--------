from typing import Dict, Any
from src.adapter.interface import ToolAdapter

class LocalChatAdapter(ToolAdapter):
    """
    Adapter for communicating with the master directly via console (or future GUI).
    """
    def execute(self, params: Dict[str, Any]) -> Any:
        message = params.get("message")
        if not message:
            return {"error": "Missing 'message' parameter."}
            
        print(f"\n[Local Chat] AI: {message}")
        
        # In a real app, this might wait for input, 
        # but for an autonomous loop, it might just be a 'send' action.
        # If we want to wait for reply:
        # response = input("[Local Chat] Master (You): ")
        # return {"master_response": response}
        
        # For now, let's assume it's a one-way message or asynchronous 
        # (the loop will pick up input later via an event queue or input check).
        
        return {"status": "sent", "recipient": "master"}
