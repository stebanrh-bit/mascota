#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR=/workspace/.cache/uv
uv sync --frozen
bash tools/setup-headless.sh
.venv/bin/python tools/headless.py .venv/bin/python -m mascota --smoke-test
