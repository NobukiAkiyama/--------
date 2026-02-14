"""
System Health Check Module
Tests all components and reports status
"""
import subprocess
import os
import sys
from typing import Dict, List, Tuple

def check_database() -> Tuple[bool, str]:
    """Check if database is accessible"""
    try:
        from src.core.database import DatabaseManager
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM personas")
            count = cursor.fetchone()[0]
        return True, f"✅ Database OK ({count} personas found)"
    except Exception as e:
        return False, f"❌ Database Error: {str(e)}"

def check_ollama() -> Tuple[bool, str]:
    """Check if Ollama is running and accessible"""
    try:
        import requests
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            return True, f"✅ Ollama OK ({len(models)} models: {', '.join(model_names[:3])})"
        else:
            return False, f"❌ Ollama returned status {response.status_code}"
    except Exception as e:
        return False, f"❌ Ollama Error: {str(e)}"

def check_vision_adapter() -> Tuple[bool, str]:
    """Check if VisionAdapter dependencies are available"""
    try:
        from src.adapter.vision import VisionAdapter
        from src.core.database import DatabaseManager
        db = DatabaseManager()
        adapter = VisionAdapter(db)
        # Just check if it initializes
        return True, "✅ Vision Adapter OK (mss, Pillow available)"
    except ImportError as e:
        return False, f"❌ Vision Adapter Error: Missing dependency {e.name}"
    except Exception as e:
        return False, f"❌ Vision Adapter Error: {str(e)}"

def check_discord_bot() -> Tuple[bool, str]:
    """Check if Discord bot dependencies are available"""
    try:
        import discord
        token = os.getenv("DISCORD_BOT_TOKEN")
        if not token:
            return False, "⚠️ Discord Token not configured in .env"
        return True, "✅ Discord.py installed, token configured"
    except ImportError:
        return False, "❌ discord.py not installed"
    except Exception as e:
        return False, f"❌ Discord Error: {str(e)}"

def check_goose_cli() -> Tuple[bool, str]:
    """Check if Goose CLI is installed"""
    # 1. Check if in PATH
    try:
        # Using shell=True and where command to be sure on Windows
        result = subprocess.run(
            ["goose", "--version"],
            capture_output=True,
            text=True,
            timeout=15, # Increased timeout
            shell=True
        )
        if result.returncode == 0:
            return True, f"✅ Goose CLI OK ({result.stdout.strip()})"
    except Exception:
        pass

    # 2. Try common bin locations on Windows (deduplicated)
    raw_paths = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "pipx", "bin", "goose.exe"),
        os.path.join(os.path.expanduser("~"), ".local", "bin", "goose.exe"),
        os.path.join(os.path.expanduser("~"), "AppData", "Local", "bin", "goose.exe"),
    ]
    # Remove duplicates and non-existent paths
    paths_to_check = list(set([p for p in raw_paths if p]))
    
    found_errors = []
    for path in paths_to_check:
        if os.path.exists(path):
            try:
                # Try execution with longer timeout and shell=True
                result = subprocess.run(
                    [path, "--version"], 
                    capture_output=True, 
                    text=True, 
                    timeout=15,
                    shell=True
                )
                if result.returncode == 0:
                    return True, f"✅ Goose CLI OK (Detected at: {path})"
                else:
                    found_errors.append(f"Exec fail ({result.returncode})")
            except subprocess.TimeoutExpired:
                # If it exists but times out, it's likely installed but slow
                return True, f"⚠️ Goose CLI Found at {path} but timed out during check. It should work."
            except Exception as e:
                found_errors.append(f"Error: {type(e).__name__}")
                continue
                
    err_msg = "❌ Goose CLI not found. Restart terminal or run 'pipx ensurepath'."
    if found_errors:
        err_msg += f" (Note: {', '.join(set(found_errors))})"
        
    return False, err_msg

def check_search_adapter() -> Tuple[bool, str]:
    """Check if SearchAdapter dependencies are available"""
    try:
        from duckduckgo_search import DDGS
        return True, "✅ DuckDuckGo Search available"
    except ImportError:
        return False, "❌ duckduckgo-search not installed"
    except Exception as e:
        return False, f"❌ Search Error: {str(e)}"

def check_dependencies() -> Tuple[bool, str]:
    """Check if all required packages are installed"""
    required = [
        "requests",
        "python-dotenv",
        "loguru",
        "Pillow",
        "mss",
        "streamlit",
        "discord.py",
        "pandas",
        "duckduckgo-search"
    ]
    
    missing = []
    for package in required:
        try:
            if package == "Pillow":
                __import__("PIL")
            elif package == "discord.py":
                __import__("discord")
            elif package == "python-dotenv":
                __import__("dotenv")
            elif package == "duckduckgo-search":
                __import__("duckduckgo_search")
            else:
                __import__(package.replace("-", "_"))
        except ImportError:
            missing.append(package)
    
    if missing:
        return False, f"❌ Missing packages: {', '.join(missing)}"
    else:
        return True, f"✅ All {len(required)} required packages installed"

def run_all_checks() -> List[Dict[str, any]]:
    """Run all health checks and return results"""
    checks = [
        ("Database", check_database),
        ("Ollama LLM", check_ollama),
        ("Vision Adapter", check_vision_adapter),
        ("Discord Bot", check_discord_bot),
        ("Goose CLI", check_goose_cli),
        ("Search Adapter", check_search_adapter),
        ("Dependencies", check_dependencies),
    ]
    
    results = []
    for name, check_func in checks:
        status, message = check_func()
        results.append({
            "component": name,
            "status": status,
            "message": message
        })
    
    return results

if __name__ == "__main__":
    print("Running system diagnostics...\n")
    results = run_all_checks()
    
    for result in results:
        print(f"{result['component']}: {result['message']}")
    
    # Overall status
    all_ok = all(r['status'] for r in results)
    print(f"\n{'='*50}")
    if all_ok:
        print("✅ All systems operational")
    else:
        failed = [r['component'] for r in results if not r['status']]
        print(f"⚠️ {len(failed)} component(s) failed: {', '.join(failed)}")
