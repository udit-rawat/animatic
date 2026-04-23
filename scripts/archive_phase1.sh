#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ARCHIVE_DIR="$ROOT_DIR/legacy/phase1-pipeline"

FILES=(
  "pipeline/scraper.py"
  "pipeline/ranker.py"
  "pipeline/scripter.py"
  "pipeline/verifier.py"
  "pipeline/scene_planner.py"
  "pipeline/param_extractor.py"
)

echo "Phase 1 archive prep"
echo "Root: $ROOT_DIR"
echo "Archive dir: $ARCHIVE_DIR"
echo

for rel in "${FILES[@]}"; do
  src="$ROOT_DIR/$rel"
  dst="$ARCHIVE_DIR/$(basename "$rel")"

  if [[ ! -f "$src" ]]; then
    echo "skip: missing $rel"
    continue
  fi

  echo "move: $rel -> legacy/phase1-pipeline/$(basename "$rel")"
done

echo
echo "Dry run only."
echo "When ready, replace echo-only loop with mv commands after imports are removed from run.py."
