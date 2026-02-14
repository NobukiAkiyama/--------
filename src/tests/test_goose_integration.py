import os
import sys
from src.adapter.goose import GooseAdapter

def test_goose_integration():
    print("--- Starting Goose Integration Test ---")
    adapter = GooseAdapter()
    
    if not adapter.goose_available:
        print("❌ Goose CLI not available. Skipping test.")
        return

    print(f"✅ Goose Binary Found at: {adapter.goose_exe}")
    
    # Simple task: create a test file
    task = "Create a file named 'goose_test.txt' with the content 'Goose was here'"
    print(f"Executing task: {task}")
    
    result = adapter.execute({"task": task})
    
    if result.get("status") == "success":
        print("✅ Goose execution SUCCESS")
        if result.get("proposal"):
            print("📜 Generated Proposal Diff:")
            print(result["proposal"])
        else:
            print("⚠️ No proposal generated (which might be okay if no file changes were made)")
    else:
        print(f"❌ Goose execution FAILED: {result.get('error')}")

if __name__ == "__main__":
    # Ensure src is in path
    sys.path.append(os.getcwd())
    test_goose_integration()
