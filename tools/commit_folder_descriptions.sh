#!/usr/bin/env bash
set -euo pipefail

# Split commits per top-level folder with provided messages.
# Usage:
#   commit_folder_descriptions.sh "docs: msg" "fabric/sql: msg" "infra: msg" ...

if [[ $# -eq 0 ]]; then
  echo "Provide folder-scoped messages, e.g., 'docs: update guide'" >&2
  exit 1
fi

root_dir=$(git rev-parse --show-toplevel)
cd "$root_dir"

for msg in "$@"; do
  scope=${msg%%:*}
  desc=${msg#*: }
  scope=${scope//[[:space:]]/}
  path="$scope"
  if [[ ! -d "$path" ]]; then
    echo "Skipping '$path' (not a directory)" >&2
    continue
  fi
  # Check if there are staged or unstaged changes under the path
  if git status --porcelain "$path" | grep -q .; then
    git add "$path"
    git commit -m "$msg"
    echo "Committed $path: $desc"
  else
    echo "No changes under $path; skipping."
  fi
done

