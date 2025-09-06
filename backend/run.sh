#!/usr/bin/env bash
set -euo pipefail # Exit immediately if a command exits with a non-zero status. Exit if a variable is used unset.

# Navigate to the script's directory (backend/)
SCRIPT_DIR="$(dirname "$0")"
cd "$SCRIPT_DIR"

# --- Create and activate virtual environment (relative to backend/ directory) ---
VENV_PATH="./.venv" # Use a relative path for the venv from backend/
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$VENV_PATH"
fi

echo "Activating virtual environment..."
# Source the activate script for the current shell
source "$VENV_PATH/bin/activate"

# --- Install/upgrade dependencies into the virtual environment ---
echo "Installing/upgrading backend dependencies..."
# This command is idempotent enough for --upgrade and installing missing packages.
# It will ensure all requirements are met without complex pre-checks.
# The 'requirements.txt' is correctly referenced relative to the current CWD (backend/).
pip install --no-cache-dir --upgrade -r "requirements.txt"

# Ensure uvicorn[standard] is installed explicitly in case it's not a direct requirement
# or if it was pulled as a minimal dependency previously.
# Check if uvicorn is actually installed in the active venv
if ! python -c "import uvicorn" &> /dev/null; then
    echo "uvicorn not found in virtual environment. Installing..."
    pip install "uvicorn[standard]"
fi

# --- IMPORTANT: Change to the project ROOT directory (flowCFD/) before running uvicorn ---
# This ensures that 'backend' is treated as a Python package for absolute imports (e.g., 'from backend.database import ...').
PROJECT_ROOT=$(cd .. && pwd)
cd "$PROJECT_ROOT"

echo "Backend setup complete. Starting Uvicorn server from $PROJECT_ROOT..."
# Corrected Uvicorn command: now we are in PROJECT_ROOT, so import backend.app
# --host 0.0.0.0 is needed for containerized/network access, 127.0.0.1 for local only
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000