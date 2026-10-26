# shared by the scheduled jobs (bin/daily.sh, bin/weekly.sh): `step` runs one command and
# remembers if it failed, and `finish` exits 1 if any did. steps keep going after a failure,
# since none needs the one before it to have succeeded (a failed sheet sync leaves the
# venues as they were, which can still be fetched), but the host still marks the run failed.

cd "$(dirname "$0")/.." || exit 1
failed=()

step() {
  echo "=== $(date -u '+%Y-%m-%d %H:%M:%S') UTC: $*"
  if ! "$@"; then
    echo "=== failed: $*"
    failed+=("$*")
  fi
}

finish() {
  if [ ${#failed[@]} -gt 0 ]; then
    echo "=== ${#failed[@]} step(s) failed:"
    printf '  %s\n' "${failed[@]}"
    exit 1
  fi
  echo "=== every step succeeded"
}
