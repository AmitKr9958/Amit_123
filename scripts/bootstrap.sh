#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
playwright install chromium
cp -n .env.example .env || true
cp -n data/profile.example.yaml data/profile.yaml || true
python -m src.cli init-db
echo "Ready. Edit data/profile.yaml and config/preferences.yaml, then: python -m src.cli login"
