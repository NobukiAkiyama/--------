import subprocess
import os
import tempfile
import uuid
from typing import Dict, Any, List, Optional

class DockerManager:
    """
    Manages ephemeral Docker containers for secure task execution.
    Provides isolation between the AI's technical actions and the host system.
    """
    def __init__(self, default_image: str = "python:3.11-slim"):
        self.default_image = default_image
        self._check_docker_available()

    def _check_docker_available(self):
        try:
            subprocess.run(["docker", "--version"], check=True, capture_output=True)
            print("[DockerManager] Connected to Docker daemon.")
        except Exception:
            print("[DockerManager] Warning: Docker not found or not running.")

    def _get_docker_path(self, path: str) -> str:
        """
        Converts a Windows path to a Docker-friendly format (/c/path/...).
        """
        abs_path = os.path.abspath(path)
        # Handle drive letter (C:\ -> /c/)
        if ":" in abs_path:
            drive, rest = abs_path.split(":", 1)
            return f"/{drive.lower()}{rest.replace('\\', '/')}"
        return abs_path.replace('\\', '/')

    def run_in_container(self, command: str, image: Optional[str] = None, workspace_path: str = ".") -> Dict[str, Any]:
        """
        Executes a command inside a fresh Docker container by copying files in and out.
        Bypasses volume mounting issues.
        """
        image = image or self.default_image
        abs_workspace = os.path.abspath(workspace_path)
        container_name = f"rito_exec_{uuid.uuid4().hex[:8]}"
        
        try:
            # 1. Create and Start container
            subprocess.run(["docker", "create", "--name", container_name, "-w", "/workspace", image, "sh", "-c", "sleep 3600"], check=True)
            subprocess.run(["docker", "start", container_name], check=True)
            
            # 2. Copy workspace into container
            print(f"[Docker] Copying workspace to container {container_name}...")
            # Note: docker cp . <container>:/workspace copies CONTENTS if we use trailing dot
            # We create the dir first
            subprocess.run(["docker", "exec", "-u", "root", container_name, "mkdir", "-p", "/workspace"], check=True)
            subprocess.run(["docker", "cp", f"{abs_workspace}/.", f"{container_name}:/workspace/"], check=True)
            
            # 3. Run command
            print(f"[Docker] Executing: {command}")
            result = subprocess.run(["docker", "exec", "-u", "root", container_name, "sh", "-c", command], capture_output=True, text=True)
            
            # 4. Copy results back
            print(f"[Docker] Syncing results back to {abs_workspace}...")
            subprocess.run(["docker", "cp", f"{container_name}:/workspace/.", f"{abs_workspace}/"], check=True)
            
            return {
                "status": "success" if result.returncode == 0 else "failed",
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
        finally:
            # Cleanup
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

    def apply_patch(self, diff_content: str, workspace_path: str = ".") -> Dict[str, Any]:
        """
        Applies a git-style diff inside a container using stdin for the diff.
        """
        abs_workspace = os.path.abspath(workspace_path)
        container_name = f"rito_patch_{uuid.uuid4().hex[:8]}"
        image = "alpine/git"
        
        try:
            # 1. Create and Start container
            subprocess.run(["docker", "create", "--name", container_name, "-w", "/workspace", image, "sh", "-c", "sleep 3600"], check=True)
            subprocess.run(["docker", "start", container_name], check=True)
            
            # 2. Copy workspace into container
            print(f"[Docker] Copying workspace to container {container_name}...")
            subprocess.run(["docker", "exec", "-u", "root", container_name, "mkdir", "-p", "/workspace"], check=True)
            subprocess.run(["docker", "cp", f"{abs_workspace}/.", f"{container_name}:/workspace/"], check=True)
            
            # 3. Apply patch via stdin using git apply
            print(f"[Docker] Applying patch via git apply...")
            result = subprocess.run(
                ["docker", "exec", "-i", "-u", "root", container_name, "git", "apply", "--no-index", "--ignore-whitespace"],
                input=diff_content,
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                print(f"[Docker] Patch applied. Syncing host...")
                subprocess.run(["docker", "cp", f"{container_name}:/workspace/.", f"{abs_workspace}/"], check=True)
                return {"status": "success", "stdout": result.stdout, "stderr": result.stderr}
            else:
                return {"status": "failed", "stdout": result.stdout, "stderr": result.stderr}
                    
        except Exception as e:
            return {"status": "error", "error": str(e)}
        finally:
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

if __name__ == "__main__":
    # Test execution
    manager = DockerManager()
    res = manager.run_in_container("ls -la")
    print(res)
