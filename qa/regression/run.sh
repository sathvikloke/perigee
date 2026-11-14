#!/usr/bin/env bash
# Perigee regression suite (worker 23). Run from anywhere; exits non-zero on any failure.
#
#   PERIGEE_DATA_ROOT=/path/to/research/build_data qa/regression/run.sh          # offline suite
#   PERIGEE_DATA_ROOT=... qa/regression/run.sh --live http://127.0.0.1:8050     # + 1 IRSA search, 1 cutout
#
# Without PERIGEE_DATA_ROOT the raw-data steps (real-processor seam test, audit_all,
# check_acceptance) are reported as SKIP, not PASS.
set -uo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
PY="$REPO/.venv/bin/python"
OUT="${QA_OUT:-$(mktemp -d)}"
LIVE=""
[[ "${1:-}" == "--live" ]] && LIVE="${2:-http://127.0.0.1:8050}"
cd "$REPO" || exit 2

declare -a ROWS
fail=0
step() { # name, command...
  local name="$1"; shift
  local log="$OUT/$(echo "$name" | tr ' /' '__').log"
  if "$@" >"$log" 2>&1; then ROWS+=("PASS  $name"); else ROWS+=("FAIL  $name  (log: $log)"); fail=1; fi
}
skip() { ROWS+=("SKIP  $1  ($2)"); }

echo "commit $(git rev-parse HEAD)  logs in $OUT"

step "backend pytest" "$PY" -m pytest backend/tests -q -p no:cacheprovider
step "deploy_check --app" "$PY" -m backend.platform.deploy_check --app
step "frontend vitest" bash -c "cd frontend && npx vitest run"
step "frontend build" bash -c "cd frontend && npm run build"

if [[ -n "${PERIGEE_DATA_ROOT:-}" && -d "${PERIGEE_DATA_ROOT}" ]]; then
  step "audit_all (183 frames)" "$PY" -m tools.ingest.audit_all --data-root "$PERIGEE_DATA_ROOT" --out "$OUT/audit.json"
  # check_acceptance always exits 0; fail on any False column.
  step "check_acceptance --all (189 records)" bash -c "
    '$PY' science/reviews/acceptance/check_acceptance.py --data-root \"\$PERIGEE_DATA_ROOT\" --all --out '$OUT/acceptance.json' >/dev/null &&
    '$PY' -c 'import json,sys; m=json.load(open(sys.argv[1]))[\"matrix\"]; f=[(r[\"frame_key\"],c) for r in m for c,v in r.items() if v is False]; print(len(m),\"records\",f); sys.exit(1 if f or len(m)<189 else 0)' '$OUT/acceptance.json'"
else
  skip "audit_all" "PERIGEE_DATA_ROOT not set"
  skip "check_acceptance" "PERIGEE_DATA_ROOT not set"
fi

if [[ -n "$LIVE" ]]; then
  step "live search + frame + JSON 404 ($LIVE)" "$PY" qa/regression/live_check.py --base "$LIVE"
else
  skip "live_check" "pass --live <api base> with the API running"
fi

printf '%s\n' "${ROWS[@]}"
exit $fail
