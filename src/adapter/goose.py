import subprocess
import json
import tempfile
import os
from typing import Dict, Any, Optional
from pathlib import Path

class GooseAdapter:
    """
    Adapter for Square's Goose AI coding assistant.
    Executes Goose via subprocess for coding tasks only.
    """
    def __init__(self, db_manager=None):
        self.db = db_manager
        self.goose_exe = self._binary_search()
        self.goose_available = self.goose_exe is not None
        if not self.goose_available:
            print("[Goose] Warning: Goose CLI not found. Install via: pipx install goose-ai")
            if self.db:
                self.db.set_system_alert("Goose CLI not found in PATH or standard locations.", level="error")
    
    def _binary_search(self) -> Optional[str]:
        """Search for Goose binary in PATH and common locations"""
        # 1. Check in PATH
        try:
            result = subprocess.run(
                ["goose", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                shell=True
            )
            if result.returncode == 0:
                return "goose"
        except Exception:
            pass
            
        # 2. Check common pipx locations on Windows
        paths = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "pipx", "bin", "goose.exe"),
            os.path.join(os.path.expanduser("~"), ".local", "bin", "goose.exe"),
            os.path.join(os.path.expanduser("~"), "AppData", "Local", "bin", "goose.exe")
        ]
        for p in paths:
            if os.path.exists(p):
                try:
                    result = subprocess.run([p, "--version"], capture_output=True, timeout=5)
                    if result.returncode == 0:
                        return p
                except Exception:
                    continue
        return None
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a coding task via Goose and generate a proposal (diff).
        
        This implementation clones the current workspace to a temporary directory,
        allows Goose to perform work there, and then returns the diff of changes.
        """
        if not self.goose_available:
            return {
                "error": "Goose CLI not installed.",
                "status": "unavailable"
            }
        
        task = params.get("task")
        if not task:
            return {"error": "Missing 'task' parameter"}
        
        main_workspace = params.get("workspace", os.getcwd())
        
        # 1. Create a temporary workspace for Goose to 'play' in
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"[Goose] Cloning workspace to {temp_dir} for proposal...")
            # Use git clone or simple copy if not a git repo
            # Simple recursive copy for now for reliability
            import shutil
            # Only copy source files to avoid bloat (ignore .git, __pycache__, etc)
            ignore_patterns = shutil.ignore_patterns('.git', '__pycache__', 'venv', '.env', 'brain.db')
            shutil.copytree(main_workspace, temp_dir, dirs_exist_ok=True, ignore=ignore_patterns)
            
            # Initialize temporary git repo in temp_dir to capture diffs
            subprocess.run(["git", "init"], cwd=temp_dir, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=temp_dir, capture_output=True)
            subprocess.run(["git", "commit", "-m", "baseline"], cwd=temp_dir, capture_output=True)

        # 2. Execute Goose in the temp workspace
        try:
            # Create a temporary instruction file
            instruction_file = os.path.join(temp_dir, "instructions.txt")
            with open(instruction_file, "w", encoding="utf-8") as f:
                f.write(task)
            
            cmd = [self.goose_exe, "run", "--instructions", "instructions.txt"]
            print(f"[Goose] Generating proposal for task in {temp_dir}...")
            
            import threading
            import time

            # Start process with popen to allow interactive response & monitoring
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=temp_dir,
                encoding='utf-8',
                errors='replace',
                bufsize=1
                # shell=True # Should not be needed if using full path
            )

            all_output = []
            
            def monitor_stream(stream, name):
                try:
                    for line in iter(stream.readline, ''):
                        if not line: break
                        clean_line = line.strip()
                        if clean_line:
                            print(f"[Goose {name}] {clean_line}")
                            all_output.append(line)
                            
                            # Resilience: Automatic y/n response
                            # Detecting various prompt patterns
                            prompt_triggers = ["(y/n)", "[y/n]", "sure?", "proceed?", "allow?", "overwrite?"]
                            if any(trigger in clean_line.lower() for trigger in prompt_triggers):
                                print(f"[Goose] Detected prompt! Auto-answering 'y'...")
                                try:
                                    process.stdin.write("y\n")
                                    process.stdin.flush()
                                except Exception as e:
                                    print(f"[Goose] Failed to write to stdin: {e}")
                except Exception as e:
                    print(f"[Goose] Stream monitor error: {e}")

            stdout_thread = threading.Thread(target=monitor_stream, args=(process.stdout, "OUT"), daemon=True)
            stderr_thread = threading.Thread(target=monitor_stream, args=(process.stderr, "ERR"), daemon=True)
            
            stdout_thread.start()
            stderr_thread.start()
            
            try:
                # Wait with timeout (5 minutes)
                rc = process.wait(timeout=300)
            except subprocess.TimeoutExpired:
                print("[Goose] Timeout reached! Sending alert...")
                if self.db:
                    self.db.set_system_alert("Goose process timed out during code generation. Manual check recommended.", level="error")
                process.kill()
                return {"status": "timeout", "error": "Goose timed out (300s)."}
            
            stdout_thread.join(timeout=5)
            stderr_thread.join(timeout=5)
            
            if rc != 0:
                last_logs = "".join(all_output[-15:])
                if self.db:
                    self.db.set_system_alert(f"Goose failed (RC {rc}). Task might be incomplete.", level="error")
                return {"status": "failed", "error": f"Goose failed (RC {rc}).\nLast logs:\n{last_logs}"}
            
            # 3. Capture the diff as the 'Proposal'
            diff_res = subprocess.run(
                ["git", "diff", "HEAD"],
                capture_output=True,
                text=True,
                cwd=temp_dir
            )
            
            proposal_diff = diff_res.stdout
            
            if not proposal_diff:
                return {
                    "status": "success",
                    "output": "No changes were proposed.",
                    "proposal": None
                }
            
            return {
                "status": "success",
                "output": "".join(all_output),
                "proposal": proposal_diff,
                "rationale": "Generated via Goose technical analysis with automatic resilience handling."
            }
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def execute_simple(self, task: str, workspace: Optional[str] = None) -> str:
        """
        Simplified execution interface.
        Returns only the output text.
        """
        result = self.execute({
            "task": task,
            "workspace": workspace or os.getcwd()
        })
        
        if result.get("status") == "success":
            return result.get("output", "")
        else:
            return f"Error: {result.get('error', 'Unknown error')}"

if __name__ == "__main__":
    # Test Goose availability
    adapter = GooseAdapter()
    
    if adapter.goose_available:
        print("[Test] Goose is available")
        
        # Simple test
        result = adapter.execute({
            "task": "Create a simple hello world function in Python"
        })
        
        print(f"[Test] Result: {result}")
    else:
        print("[Test] Goose not installed. Install with: pipx install goose-ai")
