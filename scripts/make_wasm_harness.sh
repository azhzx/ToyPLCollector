#!/usr/bin/env bash
# Assemble a standalone test harness for the riddle toypl wasm.
# Usage: scripts/make_wasm_harness.sh <path-to-toypl_wasm.wasm> <out-dir> [port]
set -euo pipefail

WASM="$1"
OUT="$2"
PORT="${3:-8124}"
SITE="$(cd "$(dirname "$0")/.." && pwd)/_site"

mkdir -p "$OUT"
cp "$WASM" "$OUT/riddle.wasm"
cp "$SITE/wasm-runner.js" "$OUT/wasm-runner.js"

python3 - "$SITE/play/riddle.html" "$OUT/index.html" <<'PY'
import sys, pathlib
src = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
src = src.replace('"playground": null', '"playground": "riddle.wasm"')
src = src.replace('src="../wasm-runner.js"', 'src="wasm-runner.js"')
pathlib.Path(sys.argv[2]).write_text(src, encoding="utf-8")
PY

echo "harness ready → $OUT (serving on :$PORT)"
