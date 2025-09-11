#!/usr/bin/env bash
set -euo pipefail

python --version
pip --version

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Environment ready. To run tests: tools/run_tests.sh"
