#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_VENV="$PROJECT_DIR/.venv"

if [[ ! -x "$PROJECT_VENV/bin/python" ]]; then
  python3 -m venv "$PROJECT_VENV"
fi

"$PROJECT_VENV/bin/python" -m pip install --quiet --upgrade pip
"$PROJECT_VENV/bin/python" -m pip install --quiet --editable "$PROJECT_DIR"

if [[ $# -eq 0 ]]; then
  set -- serve
fi

exec "$PROJECT_VENV/bin/python" -m term_mcp_deepseek "$@"
