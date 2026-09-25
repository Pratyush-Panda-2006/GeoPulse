import sys
import os
from pathlib import Path

def check_path(path_str, name, is_required=True):
    p = Path(path_str)
    if p.exists():
        print(f"[OK] {name}")
    else:
        status = "[MISSING]" if is_required else "[OPTIONAL/MISSING]"
        print(f"{status} {name} (expected at {path_str})")

def main():
    print("GeoPulse Readiness Check")
    print("------------------------")
    repo_root = Path(__file__).resolve().parent.parent
    
    # Python
    print(f"[OK] Python {sys.version.split()[0]}")
    
    # Env
    check_path(repo_root / "backend" / ".env", "Backend .env", True)
    
    # Models
    check_path(repo_root / "models" / "external" / "RemoteCLIP-RN50.pt", "RemoteCLIP Model", True)
    check_path(repo_root / "models" / "external" / "rsicd_remoteclip_rn50.index", "Exp FAISS Index", True)
    check_path(repo_root / "models" / "external" / "metadata.json", "Exp Metadata", True)
    check_path(repo_root / "models" / "external" / "geopulse_archive.index", "Prod FAISS Index", True)
    check_path(repo_root / "models" / "external" / "geopulse_archive_metadata.json", "Prod Metadata", True)
    check_path(repo_root / "models" / "snunet" / "best.pt", "SNUNet Checkpoint (Inference requires imagery)", True)
    check_path(repo_root / "models" / "ChangeFormer" / "checkpoints" / "ChangeFormerV6_LEVIR" / "best_ckpt.pt", "ChangeFormer Checkpoint (Inference requires imagery)", True)
    
    # Frontend architecture
    check_path(repo_root / "frontend" / "overview.html", "Frontend (Legacy)", True)
    check_path(repo_root / "frontend" / "intelligence.html", "Intelligence UI", True)
    check_path(repo_root / "frontend" / "telemetry.html", "Telemetry Dashboard", True)
    check_path(repo_root / "frontend_3d" / "package.json", "Frontend 3D App", True)
    check_path(repo_root / "vercel.json", "Vercel Config", True)

if __name__ == "__main__":
    main()
