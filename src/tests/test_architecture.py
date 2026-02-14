import os
import sys
# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.docker_manager import DockerManager
from src.controller.policy import Controller

def test_docker_and_controller():
    print("--- Starting Architecture Verification ---")
    
    # 1. Test DockerManager Command Execution
    docker = DockerManager()
    print("[1] Testing Docker command execution and sync...")
    # Ensure cleanup
    if os.path.exists("win.txt"): os.remove("win.txt")
    
    res = docker.run_in_container("echo 'victory' > win.txt")
    if res["status"] == "success":
        if os.path.exists("win.txt"):
            with open("win.txt", "r") as f:
                content = f.read().strip()
                if content == "victory":
                    print("✅ Docker command execution and sync successful!")
                else:
                    print(f"❌ Unexpected content: {content}")
            os.remove("win.txt")
        else:
            print("❌ File was not synced back to host.")
    else:
        print(f"❌ Docker execution failed: {res}")

    # 2. Test Controller Logic for standard tools
    print("[2] Testing Controller policy check...")
    controller = Controller()
    from src.controller.policy import ToolRequest
    req = ToolRequest(tool_name="post_sns", parameters={"text": "hello"}, reason="social")
    if controller.check_policy(req):
        print("✅ Controller policy check working.")
    else:
        print("❌ Controller policy check failed.")


if __name__ == "__main__":
    test_docker_and_controller()
