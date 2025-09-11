#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Compile Bicep to ARM template
bicep build "$ROOT_DIR/bicep/main.bicep" --outfile "$SCRIPT_DIR/mainTemplate.json"

# Create managed application package
zip -j "$SCRIPT_DIR/leftturn-managedapp.zip" "$SCRIPT_DIR/mainTemplate.json" "$SCRIPT_DIR/createUiDefinition.json"

echo "Package created: $SCRIPT_DIR/leftturn-managedapp.zip"
