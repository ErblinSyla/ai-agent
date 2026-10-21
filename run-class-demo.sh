#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root"

assignment="${AI_REVIEW_ASSIGNMENT:-/c/Users/erbli/OneDrive/Desktop/ai-assignment-01}"
reviewer_config="config/reviewer-groq.local.yaml"

for required in .env .venv/Scripts/activate "$reviewer_config"; do
  if [[ ! -f "$required" ]]; then
    printf 'FAIL: required local file is missing: %s\n' "$required" >&2
    exit 1
  fi
done
if [[ ! -d "$assignment" ]]; then
  printf 'FAIL: assignment directory is missing: %s\n' "$assignment" >&2
  printf 'Set AI_REVIEW_ASSIGNMENT to its Git Bash path and retry.\n' >&2
  exit 1
fi

# The CLI loads .env with shell variables taking precedence. Never display its values.
source .venv/Scripts/activate
run_id="$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p reports
out_dir="$(mktemp -d "reports/class-demo-$run_id-XXXXXX")"

set +e
python -m reviewer.cli review-local "$assignment" --task all --out "$out_dir" \
  --reviewer-config "$reviewer_config" --ai-review
cli_status=$?
set -e
if (( cli_status != 0 )); then
  printf 'FAIL: reviewer CLI exited with status %s; output directory: %s\n' "$cli_status" "$out_dir" >&2
  exit "$cli_status"
fi

report="$out_dir/ai-assignment-01.json"
if [[ ! -f "$report" ]]; then
  printf 'FAIL: expected report was not created: %s\n' "$report" >&2
  exit 1
fi
python -m reviewer.verify_report "$report"
