import subprocess
import time
import os
import sys
from pathlib import Path

def main():
    repo_root = Path(__file__).resolve().parent.parent
    
    print("Starting GeoPulse FastAPI Backend...")
    # Using relative path to .venv if exists, else global python
    backend_env = dict(os.environ)
    backend_cmd = [sys.executable, "-m", "uvicorn", "src.api.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"]
    backend_proc = subprocess.Popen(backend_cmd, cwd=repo_root / "backend", env=backend_env)
    
    time.sleep(2)
    
    print("Starting GeoPulse Legacy Frontend...")
    frontend_cmd = [sys.executable, "-m", "http.server", "5500"]
    frontend_proc = subprocess.Popen(frontend_cmd, cwd=repo_root / "frontend")
    
    print("\n===========================================")
    print("GeoPulse is running!")
    print("Backend API: http://127.0.0.1:8000")
    print("Frontend: http://127.0.0.1:5500/overview.html")
    print("Press Ctrl+C to stop both servers.")
    print("===========================================\n")
    
    try:
        backend_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        backend_proc.terminate()
        frontend_proc.terminate()

if __name__ == "__main__":
    main()
