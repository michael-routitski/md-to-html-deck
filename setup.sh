#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON=${PYTHON:-python3}

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    printf 'Python interpreter not found: %s\n' "$PYTHON" >&2
    exit 1
fi

"$PYTHON" -m venv "$SCRIPT_DIR/.venv"
"$SCRIPT_DIR/.venv/bin/python" -m pip install -r "$SCRIPT_DIR/md-slide-compiler/requirements.txt"