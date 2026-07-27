#!/usr/bin/env bash
set -euo pipefail
DEST="${1:-./.spec/prse-os}"
mkdir -p "$DEST"
cp -R ./* "$DEST"/
echo "Installed to $DEST"
echo "Next: edit 03_HARNESS_ADAPTER/local-harness.mapping.example.yaml and run 15_TOOLING/validate_package.py"
