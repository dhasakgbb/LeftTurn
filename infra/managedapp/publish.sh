#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE="$SCRIPT_DIR/leftturn-managedapp.zip"

if [[ ! -f "$PACKAGE" ]]; then
  echo "Package $PACKAGE not found. Run package.sh first." >&2
  exit 1
fi

: "${OFFER_ID:?Set OFFER_ID to your Partner Center offer ID}"

# Requires Azure CLI with partnercenter extension and authenticated session.
az extension add --name partnercenter >/dev/null 2>&1 || true

az partnercenter marketplace package upload \
  --offer-id "$OFFER_ID" \
  --package-path "$PACKAGE"
