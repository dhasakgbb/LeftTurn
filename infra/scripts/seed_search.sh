#!/usr/bin/env bash
set -euo pipefail

# Seed Azure AI Search data-plane assets: data source, skillset, index, and indexer.
# Requires: az CLI and env vars SEARCH_SERVICE, SEARCH_ADMIN_KEY.

set -euo pipefail

if [[ -z "${SEARCH_SERVICE:-}" || -z "${SEARCH_ADMIN_KEY:-}" ]]; then
  echo "Please set SEARCH_SERVICE and SEARCH_ADMIN_KEY environment variables." >&2
  exit 1
fi

API_VERSION="2023-11-01"
BASE="https://${SEARCH_SERVICE}.search.windows.net"

DS_NAME="${DS_NAME:-contracts-ds}"
INDEX_NAME="${INDEX_NAME:-contracts}"
SKILLSET_NAME="${SKILLSET_NAME:-contracts-skillset}"
INDEXER_NAME="${INDEXER_NAME:-contracts-indexer}"

CONTAINER="${SEARCH_DS_CONTAINER:-contracts}"
CONN_STRING="${SEARCH_DS_CONNECTION_STRING:-${AZURE_STORAGE_CONNECTION_STRING:-}}"

if [[ -z "$CONN_STRING" ]]; then
  echo "Set SEARCH_DS_CONNECTION_STRING or AZURE_STORAGE_CONNECTION_STRING for the data source." >&2
  exit 1
fi

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

# --- Data Source ---
cat >"$tmpdir/ds.json" <<EOF
{
  "name": "$DS_NAME",
  "type": "azureblob",
  "credentials": { "connectionString": "$CONN_STRING" },
  "container": { "name": "$CONTAINER" }
}
EOF

echo "Creating/Updating data source: $DS_NAME"
az rest --method put \
  --uri "$BASE/datasources/$DS_NAME?api-version=$API_VERSION" \
  --headers "Content-Type=application/json" "api-key=$SEARCH_ADMIN_KEY" \
  --body @"$tmpdir/ds.json" >/dev/null

# --- Skillset ---
echo "Creating/Updating skillset: $SKILLSET_NAME"
az rest --method put \
  --uri "$BASE/skillsets/$SKILLSET_NAME?api-version=$API_VERSION" \
  --headers "Content-Type=application/json" "api-key=$SEARCH_ADMIN_KEY" \
  --body @infra/search/skillset.contracts.json >/dev/null

# --- Index ---
echo "Creating/Updating index: $INDEX_NAME"
az rest --method put \
  --uri "$BASE/indexes/$INDEX_NAME?api-version=$API_VERSION" \
  --headers "Content-Type=application/json" "api-key=$SEARCH_ADMIN_KEY" \
  --body @infra/search/index.contracts.json >/dev/null

# --- Indexer ---
cat >"$tmpdir/indexer.json" <<EOF
{
  "name": "$INDEXER_NAME",
  "dataSourceName": "$DS_NAME",
  "targetIndexName": "$INDEX_NAME",
  "skillsetName": "$SKILLSET_NAME",
  "schedule": { "interval": "PT2H" }
}
EOF

echo "Creating/Updating indexer: $INDEXER_NAME"
az rest --method put \
  --uri "$BASE/indexers/$INDEXER_NAME?api-version=$API_VERSION" \
  --headers "Content-Type=application/json" "api-key=$SEARCH_ADMIN_KEY" \
  --body @"$tmpdir/indexer.json" >/dev/null

echo "✅ Search seed completed: ds=$DS_NAME, index=$INDEX_NAME, skillset=$SKILLSET_NAME, indexer=$INDEXER_NAME"
