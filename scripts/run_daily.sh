#!/usr/bin/env bash
# Daily run for Linux/macOS (cron example at bottom).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Default dry-run. Change to: python -m src.cli run --apply
CMD=(python -m src.cli run)

echo "[$(date -Iseconds)] Starting: ${CMD[*]}"
"${CMD[@]}"
echo "[$(date -Iseconds)] Done"

# Cron example (09:00 daily):
# 0 9 * * * /path/to/naukri-apply/scripts/run_daily.sh >> /path/to/naukri-apply/data/cron.log 2>&1
