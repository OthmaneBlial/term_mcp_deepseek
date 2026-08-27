#!/usr/bin/env bash
set -euo pipefail

RELEASE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RELEASE_PYTHON="${PYTHON_BIN:-python3}"
RELEASE_OUTPUT="${1:-$RELEASE_ROOT/dist}"

case "$RELEASE_PYTHON" in
  /*) ;;
  */*)
    RELEASE_PYTHON="$(cd "$(dirname "$RELEASE_PYTHON")" && pwd)/$(basename "$RELEASE_PYTHON")"
    ;;
  *)
    RELEASE_PYTHON="$(command -v "$RELEASE_PYTHON")"
    ;;
esac

if [[ -n "$(git -C "$RELEASE_ROOT" status --porcelain)" ]]; then
  echo "release check requires a clean worktree" >&2
  exit 2
fi

if [[ -d "$RELEASE_OUTPUT" ]] && find "$RELEASE_OUTPUT" -mindepth 1 -maxdepth 1 -print -quit | read -r _; then
  echo "release output must be empty: $RELEASE_OUTPUT" >&2
  exit 2
fi

"$RELEASE_PYTHON" -c "import build, twine" 2>/dev/null || {
  echo "install development dependencies first: python -m pip install -e '.[dev]'" >&2
  exit 2
}

RELEASE_TMP="$(mktemp -d)"
RELEASE_SOURCE="$RELEASE_TMP/source"
RELEASE_DIST="$RELEASE_TMP/dist"
RELEASE_INSTALL="$RELEASE_TMP/install"
RELEASE_WORKSPACE="$RELEASE_TMP/workspace"
mkdir -p "$RELEASE_SOURCE" "$RELEASE_DIST" "$RELEASE_WORKSPACE"

git -C "$RELEASE_ROOT" archive --format=tar HEAD | tar -xf - -C "$RELEASE_SOURCE"

RELEASE_VERSION="$("$RELEASE_PYTHON" -c "import sys; sys.path.insert(0, '$RELEASE_SOURCE'); from term_mcp_deepseek._version import VERSION; print(VERSION)")"
RELEASE_TAG="$(git -C "$RELEASE_ROOT" describe --tags --exact-match HEAD 2>/dev/null || true)"
if [[ -n "$RELEASE_TAG" && "$RELEASE_TAG" != "v$RELEASE_VERSION" ]]; then
  echo "tag $RELEASE_TAG does not match package version $RELEASE_VERSION" >&2
  exit 2
fi

cd "$RELEASE_SOURCE"
"$RELEASE_PYTHON" -m build --sdist --wheel --outdir "$RELEASE_DIST"
"$RELEASE_PYTHON" -m twine check "$RELEASE_DIST"/*

"$RELEASE_PYTHON" - <<PY
from pathlib import Path
from zipfile import ZipFile

wheel = next(Path("$RELEASE_DIST").glob("*.whl"))
required = {
    "term_mcp_deepseek/schemas/recipe.schema.json",
    "term_mcp_deepseek/schemas/receipt.schema.json",
    "term_mcp_deepseek/static/app.css",
    "term_mcp_deepseek/static/app.js",
    "term_mcp_deepseek/static/chat.html",
    "term_mcp_deepseek/static/favicon.svg",
}
with ZipFile(wheel) as archive:
    missing = sorted(required - set(archive.namelist()))
if missing:
    raise SystemExit(f"wheel is missing runtime assets: {missing}")
PY

"$RELEASE_PYTHON" -m venv "$RELEASE_INSTALL"
"$RELEASE_INSTALL/bin/python" -m pip install --quiet \
  --constraint "$RELEASE_SOURCE/constraints.txt" \
  "$RELEASE_DIST"/*.whl

INSTALLED_VERSION="$($RELEASE_INSTALL/bin/term-mcp version)"
if [[ "$INSTALLED_VERSION" != "$RELEASE_VERSION" ]]; then
  echo "installed CLI version $INSTALLED_VERSION does not match $RELEASE_VERSION" >&2
  exit 2
fi

RELEASE_TOKEN="release-check-token-that-is-longer-than-thirty-two"
AUTH_TOKEN="$RELEASE_TOKEN" WORKSPACE_ROOT="$RELEASE_WORKSPACE" \
  "$RELEASE_INSTALL/bin/term-mcp" doctor --json >/dev/null
DEEPSEEK_API_KEY="" "$RELEASE_INSTALL/bin/term-mcp" demo --json >/dev/null

AUTH_TOKEN="$RELEASE_TOKEN" \
WORKSPACE_ROOT="$RELEASE_WORKSPACE" \
ALLOWED_ORIGINS="http://127.0.0.1:8765" \
  "$RELEASE_INSTALL/bin/term-mcp" serve --host 127.0.0.1 --port 8765 \
  >"$RELEASE_TMP/server.log" 2>&1 &
RELEASE_SERVER_PID=$!

RELEASE_HEALTH_OK=0
for RELEASE_ATTEMPT in 1 2 3 4 5 6 7 8 9 10; do
  if "$RELEASE_INSTALL/bin/python" -c \
    "import urllib.request; assert urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=1).status == 200" \
    2>/dev/null; then
    RELEASE_HEALTH_OK=1
    break
  fi
  sleep 1
done

if [[ "$RELEASE_HEALTH_OK" -ne 1 ]]; then
  sed -n '1,160p' "$RELEASE_TMP/server.log" >&2
  kill -TERM "$RELEASE_SERVER_PID" 2>/dev/null || true
  exit 1
fi

"$RELEASE_INSTALL/bin/python" - <<'PY'
import json
import urllib.request

root = urllib.request.urlopen("http://127.0.0.1:8765/", timeout=2).read().decode()
schema = json.load(
    urllib.request.urlopen("http://127.0.0.1:8765/schemas/receipt-1.0.json", timeout=2)
)
assert "Approval-first mission control" in root
assert schema["title"] == "Term MCP DeepSeek execution receipt"
PY

kill -TERM "$RELEASE_SERVER_PID"
wait "$RELEASE_SERVER_PID" || true

cd "$RELEASE_DIST"
"$RELEASE_PYTHON" - <<'PY'
import hashlib
from pathlib import Path

artifacts = sorted(path for path in Path(".").iterdir() if path.is_file())
lines = []
for artifact in artifacts:
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    lines.append(f"{digest}  {artifact.name}")
Path("SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

mkdir -p "$RELEASE_OUTPUT"
cp "$RELEASE_DIST"/* "$RELEASE_OUTPUT"/

echo "release-check: ok (v$RELEASE_VERSION)"
echo "artifacts: $RELEASE_OUTPUT"
