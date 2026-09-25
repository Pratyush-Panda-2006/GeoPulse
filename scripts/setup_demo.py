import sys
import os
import json
from pathlib import Path

def main():
    print("GeoPulse Demo Setup")
    print("===================")
    
    # 1. Check Python version
    if sys.version_info >= (3, 9):
        print("[OK] Python")
    else:
        print("[WARN] Python 3.9+ recommended")
        
    repo_root = Path(__file__).resolve().parent.parent
    
    # 2 & 3. Create required directories
    models_dir = repo_root / "models"
    (models_dir / "external").mkdir(parents=True, exist_ok=True)
    (models_dir / "snunet").mkdir(parents=True, exist_ok=True)
    (models_dir / "ChangeFormer" / "checkpoints" / "ChangeFormerV6_LEVIR").mkdir(parents=True, exist_ok=True)
    
    # 4 & 5. Read manifest and check status
    manifest_path = repo_root / "scripts" / "assets_manifest.json"
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    missing = []
    for asset in manifest["assets"]:
        dest = repo_root / asset["destination"]
        if dest.exists():
            print(f"[OK] {asset['name']}")
        else:
            print(f"[MISSING] {asset['name']} (requires manual download to {dest})")
            missing.append(asset)
            
    # 8. Check .env
    env_path = repo_root / "backend" / ".env"
    env_example = repo_root / "backend" / ".env.example"
    if not env_path.exists():
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_path)
            print("[OK] Created backend/.env from .env.example")
        else:
            print("[WARN] backend/.env.example missing")
    else:
        print("[OK] backend/.env already exists")
        
    # Read env to check for secrets
    with open(env_path, "r") as f:
        env_content = f.read()
    
    warnings = []
    if "CDSE_CLIENT_ID=" in env_content and "CDSE_CLIENT_ID=your_id" in env_content:
        warnings.append("CDSE credentials not configured")
    if "NVIDIA_API_KEY=" in env_content and "NVIDIA_API_KEY=your_key" in env_content:
        warnings.append("NVIDIA_API_KEY not configured")
        
    for w in warnings:
        print(f"[WARN] {w}")
        
    print("\nGeoPulse setup check complete.")
    if missing:
        print(f"\nYou still need to manually download {len(missing)} external assets.")
        
if __name__ == "__main__":
    main()
