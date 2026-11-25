#!/bin/sh
# Browser tests against a freshly reset database with the saved real screen replayed (D-065).
#   sh scripts/e2e.sh                 # every suite, after a reset and a replay
#   sh scripts/e2e.sh m9-desk         # one suite, after a reset and a replay
# The tests write test records: run them on a separate stack (README) and reset it afterwards.
# Needs LP_PIPELINE_TOKEN in the environment (the same value as in .env) and the pipeline venv.
set -e
cd "$(dirname "$0")/.."
SCREEN=${LP_E2E_SCREEN:-reports/screen/2026-11-22}

reset() {
  if ! docker compose exec -T -e LP_ALLOW_RESET=true api python -m app.seed.reset > /dev/null 2>&1; then
    echo "reset failed"
    docker compose exec -T -e LP_ALLOW_RESET=true api python -m app.seed.reset 2>&1 | tail -20
    exit 1
  fi
  "${LP_VENV:-/c/lp-cache/venv/Scripts}/lp" replay "$SCREEN" > /dev/null
  echo "database reset, real screen replayed"
}

run() {
  docker compose --profile e2e run --rm -T e2e npx playwright test "$@"
}

reset
run "$@"
