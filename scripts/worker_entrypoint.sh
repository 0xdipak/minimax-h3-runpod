#!/usr/bin/env bash
# Bootstrap entrypoint for public-base-image deploys (no private registry required).
# Prefer the baked ghcr.io/ruizmr/minimax-h3-runpod image once the package is public.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
export PYTHONUNBUFFERED=1
export HF_HOME="${HF_HOME:-/runpod-volume/huggingface-cache}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-$HF_HOME}"
export OUTPUT_DIR="${OUTPUT_DIR:-/tmp/h3_outputs}"

mkdir -p "$HF_HOME" "$OUTPUT_DIR" /opt/h3

if ! command -v ffmpeg >/dev/null 2>&1; then
  apt-get update
  apt-get install -y --no-install-recommends ffmpeg git libgl1 libglib2.0-0
fi

APP_DIR=/opt/h3/app
REPO_URL="${H3_REPO_URL:-https://github.com/ruizmr/minimax-h3-runpod.git}"
REPO_REF="${H3_REPO_REF:-main}"

if [[ ! -f "$APP_DIR/handler.py" ]]; then
  rm -rf "$APP_DIR"
  git clone --depth 1 --branch "$REPO_REF" "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"
# Keep worker code fresh on each cold start without full reinstall when possible.
git fetch --depth 1 origin "$REPO_REF" || true
git checkout -f "FETCH_HEAD" 2>/dev/null || git checkout -f "$REPO_REF" || true

VENV_DIR=/runpod-volume/h3-venv
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  python -m venv "$VENV_DIR" || true
fi

# Prefer volume venv when writable; otherwise use system python/pip.
if [[ -x "$VENV_DIR/bin/python" ]]; then
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
fi

pip install --upgrade pip
pip install -r requirements.txt

exec python -u handler.py
