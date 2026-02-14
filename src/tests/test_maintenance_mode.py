from src.core.database import DatabaseManager
from src.controller.policy import Controller, ToolRequest
from src.adapter.interface import SNSAdapter

def test_maintenance_mode():
    print("--- Starting Maintenance & Check Mode Verification ---")
    db = DatabaseManager()
    controller = Controller(db)
    sns = SNSAdapter(db)
    
    # 1. Normal Mode
    print("[Test 1] Normal Mode...")
    db.set_config("maintenance_mode", False, reason="Switch to normal")
    req = ToolRequest(tool_name="read_file", parameters={"path": "test.txt"}, reason="normal work")
    controller.check_policy(req) # Should print without [MAINTENANCE]
    
    # 2. Maintenance Mode
    print("\n[Test 2] Maintenance Mode...")
    db.set_config("maintenance_mode", True, reason="Verification tests")
    controller.check_policy(req) # Should print WITH [MAINTENANCE]
    
    # 3. SNS Simulation in Maintenance
    print("\n[Test 3] SNS Simulation...")
    res = sns.execute({"action": "post", "platform": "discord", "text": "Test maintenance post"})
    print(f"SNS Result: {res}")
    if res.get("simulated"):
        print("✅ SNS Simulation Success (No real post queued)")
    else:
        print("❌ SNS Still Queuing Real Post!")

    # 4. Check policy for forbidden tool in maintenance
    print("\n[Test 4] Forbidden tool in maintenance...")
    req_bad = ToolRequest(tool_name="nuclear_launch", parameters={}, reason="oops")
    controller.check_policy(req_bad) # Should print [MAINTENANCE] [PolicyViolation]

    print("\n--- Verification Finished ---")

if __name__ == "__main__":
    test_maintenance_mode()
