#!/usr/bin/env bash
# Bootstrap entrypoint for public-base-image deploys (no private registry required).
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
export PYTHONUNBUFFERED=1

# Prefer Runpod network/cache volume when present and writable.
if [[ -d /runpod-volume ]] && touch /runpod-volume/.write_test 2>/dev/null; then
  rm -f /runpod-volume/.write_test
  VOL=/runpod-volume
else
  VOL=/opt/h3-data
  mkdir -p "$VOL"
fi

export HF_HOME="${HF_HOME:-$VOL/huggingface-cache}"
export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-$HF_HOME}"
export OUTPUT_DIR="${OUTPUT_DIR:-/tmp/h3_outputs}"
mkdir -p "$HF_HOME" "$OUTPUT_DIR" /opt/h3

echo "[h3-entry] vol=$VOL cuda=$(command -v nvidia-smi || true)"
nvidia-smi -L || true

if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v git >/dev/null 2>&1 || ! command -v gcc >/dev/null 2>&1; then
  apt-get update
  apt-get install -y --no-install-recommends \
    build-essential ffmpeg git curl ca-certificates libgl1 libglib2.0-0
fi

APP_DIR=/opt/h3/app
REPO_URL="${H3_REPO_URL:-https://github.com/ruizmr/minimax-h3-runpod.git}"
REPO_REF="${H3_REPO_REF:-main}"

if [[ ! -f "$APP_DIR/handler.py" ]]; then
  rm -rf "$APP_DIR"
  git clone --depth 1 --branch "$REPO_REF" "$REPO_URL" "$APP_DIR"
else
  cd "$APP_DIR"
  git fetch --depth 1 origin "$REPO_REF" || true
  git reset --hard "origin/$REPO_REF" 2>/dev/null || git checkout -f "$REPO_REF" || true
fi

cd "$APP_DIR"

# System site-packages in the pytorch image already have torch; install the rest there.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "[h3-entry] starting handler"
exec python -u handler.py
