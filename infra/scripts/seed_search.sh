#!/usr/bin/env bash
set -euo pipefail

# Seed Azure AI Search index and skillset using data-plane REST API.
# Requires: az CLI logged in and SEARCH_SERVICE, SEARCH_ADMIN_KEY env vars.

if [[ -z "${SEARCH_SERVICE:-}" || -z "${SEARCH_ADMIN_KEY:-}" ]]; then
  echo "Please set SEARCH_SERVICE and SEARCH_ADMIN_KEY environment variables." >&2
  exit 1
fi

API_VERSION="2023-11-01"
BASE="https://${SEARCH_SERVICE}.search.windows.net"

echo "Creating skillset..."
az rest \
  --method put \
  --uri "$BASE/skillsets/contracts-skillset?api-version=$API_VERSION" \
  --headers "Content-Type=application/json" "api-key=$SEARCH_ADMIN_KEY" \
  --body @infra/search/skillset.contracts.json >/dev/null

echo "Creating index..."
az rest \
  --method put \
  --uri "$BASE/indexes/contracts?api-version=$API_VERSION" \
  --headers "Content-Type=application/json" "api-key=$SEARCH_ADMIN_KEY" \
  --body @infra/search/index.contracts.json >/dev/null

echo "Done."
