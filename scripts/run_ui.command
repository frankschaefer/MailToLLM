#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

if [ -x "$VENV_DIR/bin/python" ]; then
  PYTHON_BIN="$VENV_DIR/bin/python"
else
  PYTHON_BIN="$(command -v python3 || true)"
fi

if [ -z "$PYTHON_BIN" ]; then
  echo "python3 not found. Please install Python 3."
  read -r _
  exit 1
fi

export PYTHONPATH="$ROOT_DIR/src:${PYTHONPATH:-}"

# Run the app and capture exit code
"$PYTHON_BIN" -m mailtollm.ui.app
EXIT_CODE=$?

# If successful (exit code 0), close terminal automatically
if [ $EXIT_CODE -eq 0 ]; then
  osascript -e 'tell application "Terminal" to close first window' &> /dev/null || true
  exit 0
fi

# If error occurred, keep terminal open and wait for user
echo ""
echo "App exited with error code: $EXIT_CODE"
echo "Press Enter to close this window..."
read -r _
exit $EXIT_CODE
