#!/bin/sh
# Reset the demo database, then run browser tests. Usage: sh scripts/e2e.sh [test filter]
set -e
cd "$(dirname "$0")/.."
docker compose exec -T -e LP_ALLOW_RESET=true api python -m app.seed.reset > /dev/null 2>&1 || {
  echo "reset failed"; docker compose exec -T -e LP_ALLOW_RESET=true api python -m app.seed.reset 2>&1 | tail -20; exit 1; }
echo "demo database reset"
docker compose --profile e2e run --rm -T e2e npx playwright test "$@"
