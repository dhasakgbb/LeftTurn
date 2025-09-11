#!/usr/bin/env bash
set -euo pipefail

echo "Linting with flake8..."
flake8

echo "Running unit tests..."
pytest -q

echo "All good."
