from typing import List, Dict, Any
from dataclasses import dataclass
from src.core.docker_manager import DockerManager

@dataclass
class ToolRequest:
    tool_name: str
    parameters: Dict[str, Any]
    reason: str

class Controller:
    """
    The 'Super-Ego' or regulatory body of the agent.
    Sole authority for executing system-mutating actions via Docker.
    """
    def __init__(self, db_manager=None):
        self.allowed_tools = ["post_sns", "search_web", "read_file", "call_analysis", "see_screen", "post_image", "local_chat", "idle", "goose_code"]
        self.forbidden_words = ["ignore all instructions", "system override"]
        self.db = db_manager
        self.docker = DockerManager()
        
    def check_policy(self, request: ToolRequest) -> bool:
        """ Validates a tool request against safety/policy rules. """
        # 0. Maintenance Mode Check
        is_maintenance = False
        if self.db:
            is_maintenance = self.db.get_config("maintenance_mode", False)
            if is_maintenance:
                print(f"[MAINTENANCE] Policy check for: {request.tool_name}")

        # 1. Check if tool is allowed generally
        if request.tool_name not in self.allowed_tools:
            prefix = "[MAINTENANCE] " if is_maintenance else ""
            print(f"{prefix}[PolicyViolation] Tool '{request.tool_name}' is not allowed.")
            return False
            
        # 2. Deep Setting: Check dynamic config if db is present
        if self.db:
            if request.tool_name == "see_screen":
                if not self.db.get_config("allow_screenshots", True):
                    reason = self.db.get_config("screenshot_disable_reason", "No reason provided")
                    prefix = "[MAINTENANCE] " if is_maintenance else ""
                    print(f"{prefix}[Policy] Blocked 'see_screen'. Reason: {reason}")
                    return False

        return True


    def execute_technical_proposal(self, proposal_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes a proposal from a technical advisor (like Goose) 
        and executes it within a secure Docker boundary.
        """
        proposal_diff = proposal_result.get("proposal")
        if not proposal_diff:
            return {"status": "skipped", "message": "No proposal to execute."}

        # 1. Verification (Simplified: Check if it's a valid diff)
        if "diff --git" not in proposal_diff:
            return {"status": "rejected", "error": "Invalid diff format in proposal."}

        # 2. Execution Boundary
        print("[Controller] Executing technical proposal in Docker boundary...")
        result = self.docker.apply_patch(proposal_diff)
        
        if result["status"] == "success":
            print("[Controller] Implementation successful.")
            return {"status": "applied", "details": result}
        else:
            print(f"[Controller] Implementation failed: {result.get('stderr')}")
            return {"status": "failed", "error": result.get("stderr")}

    def execute_command_safely(self, command: str) -> Dict[str, Any]:
        """ Executes a shell command strictly inside Docker. """
        print(f"[Controller] Running command in container: {command}")
        return self.docker.run_in_container(command)
