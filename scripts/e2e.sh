#!/bin/sh
# Browser tests against a freshly reset demo database.
#   sh scripts/e2e.sh                 # milestone suites, then a second reset and the full demo walkthrough
#   sh scripts/e2e.sh m6-field        # one suite, after a reset
set -e
cd "$(dirname "$0")/.."

reset() {
  if ! docker compose exec -T -e LP_ALLOW_RESET=true api python -m app.seed.reset > /dev/null 2>&1; then
    echo "reset failed"
    docker compose exec -T -e LP_ALLOW_RESET=true api python -m app.seed.reset 2>&1 | tail -20
    exit 1
  fi
  echo "demo database reset"
}

run() {
  docker compose --profile e2e run --rm -T e2e npx playwright test "$@"
}

if [ "$#" -gt 0 ]; then
  reset
  run "$@"
else
  reset
  run m10-real m11-sources
  # The walkthrough starts from a fresh demo, as a presenter would.
  reset
  run m9-demo
fi
