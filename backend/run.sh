#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." 
python3 -m pip install -r backend/requirements.txt
# Run API on :8000
uvicorn backend.app:app --host 0.0.0.0 --port 8000
