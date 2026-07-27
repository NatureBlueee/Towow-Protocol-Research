#!/usr/bin/env bash
set -euo pipefail

DEST="${1:-./.spec/prse-ai-native}"

mkdir -p "$DEST"
cp -R ./* "$DEST"/

echo "Installed PRSE AI Native SpecKit to: $DEST"
echo "Next:"
echo "1) edit $DEST/03_harness_adapter/local-harness.mapping.example.yaml"
echo "2) map your local Harness concepts"
echo "3) run the smoke tests in $DEST/05_conformance/smoke_tests.yaml"
echo "4) load $DEST/06_projects/summon/project.manifest.yaml"
