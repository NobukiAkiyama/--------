import time
import json
from src.core.database import DatabaseManager
from src.controller.policy import Controller, ToolRequest
from src.adapter.vision import VisionAdapter

def test_config_system():
    print("--- Starting Dynamic Config & Audit Verification ---")
    db = DatabaseManager()
    controller = Controller(db)
    vision = VisionAdapter(db)
    
    # 1. Enable screenshots and test
    print("[Test 1] Enabling screenshots...")
    db.set_config("allow_screenshots", True, reason="Verification start")
    
    req = ToolRequest(tool_name="see_screen", parameters={"prompt": "test"}, reason="unit test")
    if controller.check_policy(req):
        print("Controller: ALLOWED (Expected)")
    else:
        print("Controller: BLOCKED (Unexpected)")
        
    # 2. Disable screenshots with a REASON
    print("\n[Test 2] Disabling screenshots with a specific reason...")
    disable_reason = "Privacy protection activated during sensitive work."
    db.set_config("allow_screenshots", False, reason=disable_reason)
    db.set_config("screenshot_disable_reason", disable_reason, reason="Metadata sync")
    
    # 3. Verify Controller blocks it
    print("\n[Test 3] Controller Policy Check (Disabled)...")
    if not controller.check_policy(req):
        print("Controller: BLOCKED (Expected)")
    else:
        print("Controller: ALLOWED (Unexpected)")

    # 4. Verify Module itself blocks it (Deep Setting)
    print("\n[Test 4] Module execution check (Disabled)...")
    result = vision.execute({"prompt": "test"})
    print(f"Module Result: {result.get('status')} - {result.get('message')}")
    print(f"Recorded Reason: {result.get('reason')}")

    # 5. Check Audit Log
    print("\n[Test 5] Checking Audit Log for 'allow_screenshots'...")
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM config_audit_log WHERE key = 'allow_screenshots' ORDER BY timestamp DESC")
        logs = cursor.fetchall()
        for log in logs:
            print(f"- Change: {log['old_value']} -> {log['new_value']} | Reason: {log['reason']}")

if __name__ == "__main__":
    test_config_system()
