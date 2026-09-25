# GeoPulse

## Overview
GeoPulse is a semantic/multimodal satellite imagery retrieval and multi-temporal change analysis platform.

## Architecture
- `frontend/`: default/original GeoPulse static website
- `frontend/intelligence.html`: Semantic text and image-to-image retrieval UI
- `frontend/telemetry.html`: Restored original telemetry dashboard
- `frontend_3d/`: isolated React/Vite/Cesium 2D→3D application
- `backend/`: FastAPI AI backend
- `vercel.json`: Configuration to deploy `frontend/` as the default static application

## Requirements
- Python 3.9+ compatible environment
- Node.js and npm (for `frontend_3d` only)
- 16 GB RAM recommended
- GPU is optional (the current verified system runs on CPU-only PyTorch)
- Sufficient disk space for model checkpoints and FAISS indexes

## Getting Started

### 1. Fresh Clone & Setup
Clone this repository and run the setup script:
```bash
python scripts/setup_demo.py
```

### 2. AI Model Assets (Manual Download Required)
The following large external assets are required but intentionally NOT committed to Git. They must be acquired manually and placed in the appropriate folders as indicated by `scripts/setup_demo.py`:
- `RemoteCLIP-RN50.pt` (Visual language model) -> `models/external/`
- FAISS indexes and metadata files -> `models/external/`
- SNUNet-CD checkpoint (`best.pt`) -> `models/snunet/`
- ChangeFormer checkpoint (`best_ckpt.pt`) -> `models/ChangeFormer/checkpoints/ChangeFormerV6_LEVIR/`

*Note: You must obtain these files separately and place them in your local filesystem. This project is not fully clone-and-run without them.*

### 3. Environment Configuration
Copy the `.env.example` file to `.env`:
```bash
copy backend/.env.example backend/.env
```
Fill in `.env` with your API keys (e.g., NVIDIA, CDSE) and adjust model paths if needed. The default configuration uses paths relative to the repository.

### 4. Readiness Check
Before starting, run the readiness check to ensure all models and configs are in place:
```bash
python scripts/check_demo.py
```

### 5. Starting the Backend and Frontend
To easily launch both the FastAPI backend and the default static frontend, use:
```bash
python scripts/start_demo.py
```
Open: http://127.0.0.1:5500/overview.html

### 6. Optional: 2D→3D Viewer
If you want to view the React application:
```bash
cd frontend_3d
npm install
npm run dev
```

## AI Features
The following features are accessible via `frontend/intelligence.html` and the backend:
- SNUNet-CD SAR change detection
- ChangeFormer change detection
- Semantic text retrieval
- Image-to-image retrieval
- Archive text/image retrieval

## Troubleshooting
- **Missing model/index**: Run `python scripts/check_demo.py` to see which asset is missing.
- **Port already in use**: Ensure no other background process is using port 8000 or 5500.
