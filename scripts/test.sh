#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
for script in scripts/*.sh; do bash -n "$script"; done
python3 -m py_compile scripts/init-env.py
docker build --target test -t mahad-media:tests .
project="mahad-ci-$$"
cleanup() { docker compose -p "$project" -f compose.ci.yaml down --volumes >/dev/null; }
trap cleanup EXIT
docker compose -p "$project" -f compose.ci.yaml up --build --abort-on-container-exit --exit-code-from test
