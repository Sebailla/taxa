#!/usr/bin/env bash
# Phase 6a G5 hydration-baseline runtime harness (G5 1+9 protocol).
#
# Authoritative G5 1+9 contract (per the user authorization +
# openspec/changes/complete-taxa-frontend-migration/design.md
# §"G5 — hydration baseline" and tasks.md §Phase 6a):
#
#   1. Run `scripts/reconstruct_hydration_baseline.py
#      --warmup-count 1 --samples-retained 9` to produce the legacy
#      baseline artifact (or a fail-closed placeholder).
#   2. If the React candidate build (`out/`) exists and the candidate
#      artifact (`out/hydration-candidate.json`) is missing, run
#      `scripts/capture_hydration_candidate.py
#      --warmup-count 1 --samples-retained 9` to drive Playwright +
#      Chromium against a local static server that serves `out/`, and
#      emit the candidate artifact (or a fail-closed placeholder).
#   3. Run `scripts/measure_hydration.py --baseline <b> --candidate <c>
#      --report-out <r>` to compare baseline vs candidate on the
#      DOMContentLoaded median. The gate is the absolute median delta
#      <= 10 ms (G5 1+9 protocol).
#   4. Write a versioned status record under
#      `openspec/changes/complete-taxa-frontend-migration/evidence/g5/`
#      so the apply worker can audit the harness without re-running it.
#      The status.json carries threshold_ms (10.0), medians, delta,
#      pass verdict, and provenance so a reviewer can audit the gate.
#
# The harness is fail-closed by construction. It MUST NEVER flip G5:
# the apply worker is the only authority that may flip the gate, and
# only after both:
#   * the captured baseline is `source: "captured"` (NOT a placeholder)
#   * the baseline vs candidate comparison exits 0 (delta_ms <= 10 ms)
#
# When either precondition fails, the harness writes a `status.json`
# that explicitly records G5 as `blocked` with a `blocker` field naming
# the environmental or regression reason. The script's own exit code
# reflects the verdict so callers can chain on it.
#
# Inputs (positional / env):
#   G5_FIXTURE_WEB_ROOT  - override the frozen fixture root (default
#                          tools/g3-legacy-fixture/web)
#   G5_OUT               - override the baseline artifact path
#                          (default web/dist/evidence-baseline.json)
#   G5_BUILD_DIR         - override the candidate build directory
#                          (default out/)
#   G5_STATUS_JSON       - override the status.json path (no default;
#                          tests use this to keep the harness output
#                          out of the production evidence directory)
#   G5_REPORT_JSON       - override the regression-report.json path
#                          (no default; same rationale)
#   G5_CANDIDATE         - override the candidate artifact path (no
#                          default; the harness auto-detects under
#                          out/ only if the apply worker has already
#                          captured one)
#
# Exit codes:
#   0  Both preconditions met (real baseline + delta_ms <= 10 ms).
#      G5 may flip on the apply worker's separate authority; this
#      script does NOT flip the gate.
#   2  Precondition not met (placeholder baseline or regression
#      detected); status.json records the reason.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE_DIR="${REPO_ROOT}/openspec/changes/complete-taxa-frontend-migration/evidence/g5"

FIXTURE_WEB_ROOT="${G5_FIXTURE_WEB_ROOT:-${REPO_ROOT}/tools/g3-legacy-fixture/web}"
BASELINE_OUT="${G5_OUT:-${REPO_ROOT}/web/dist/evidence-baseline.json}"
BUILD_DIR="${G5_BUILD_DIR:-${REPO_ROOT}/out}"
CANDIDATE_OUT_DEFAULT="${REPO_ROOT}/out/hydration-candidate.json"

# G5 1+9 protocol constants — see design.md §"G5 — hydration baseline".
G5_WARMUP_COUNT=1
G5_SAMPLES_RETAINED=9
G5_THRESHOLD_MS=10.0

CANDIDATE_JSON=""
if [[ -n "${G5_CANDIDATE:-}" ]]; then
  CANDIDATE_JSON="${G5_CANDIDATE}"
elif [[ -f "${CANDIDATE_OUT_DEFAULT}" ]]; then
  CANDIDATE_JSON="${CANDIDATE_OUT_DEFAULT}"
fi

REPORT_JSON="${G5_REPORT_JSON:-${EVIDENCE_DIR}/regression-report.json}"
STATUS_JSON="${G5_STATUS_JSON:-${EVIDENCE_DIR}/status.json}"

mkdir -p "${EVIDENCE_DIR}"

CAPTURED_AT="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

log() { printf "[g5_close.sh] %s\n" "$*" >&2; }

# ---------------------------------------------------------------------------
# Step 1 - attempt the legacy baseline reconstruction
# ---------------------------------------------------------------------------
log "G5 1+9 step 1/4: reconstruct legacy baseline"
log "  fixture_web_root:    ${FIXTURE_WEB_ROOT}"
log "  out:                 ${BASELINE_OUT}"
log "  warmup_count:        ${G5_WARMUP_COUNT}"
log "  samples_retained:    ${G5_SAMPLES_RETAINED}"

CAPTURE_EXIT=0
python3 "${REPO_ROOT}/scripts/reconstruct_hydration_baseline.py" \
    --fixture-web-root "${FIXTURE_WEB_ROOT}" \
    --out "${BASELINE_OUT}" \
    --warmup-count "${G5_WARMUP_COUNT}" \
    --samples-retained "${G5_SAMPLES_RETAINED}" || CAPTURE_EXIT=$?

BASELINE_SOURCE="$(python3 -c "
import json
try:
    doc = json.load(open('${BASELINE_OUT}'))
    print(doc.get('source', 'unknown'))
except Exception:
    print('unreadable')
" 2>/dev/null || echo "unreadable")"

BASELINE_BLOCKER="$(python3 -c "
import json
try:
    doc = json.load(open('${BASELINE_OUT}'))
    print(doc.get('blocker', ''))
except Exception:
    pass
" 2>/dev/null || true)"

if [[ "${CAPTURE_EXIT}" -ne 0 || "${BASELINE_SOURCE}" != "captured" ]]; then
  log "baseline reconstruction did NOT produce a captured artifact"
  log "  exit=${CAPTURE_EXIT}  source=${BASELINE_SOURCE}"
  log "  blocker=${BASELINE_BLOCKER}"
  STATUS_JSON="${STATUS_JSON}" CAPTURED_AT="${CAPTURED_AT}" \
    BASELINE_OUT="${BASELINE_OUT}" CANDIDATE_JSON="${CANDIDATE_JSON:-}" \
    G5_THRESHOLD_MS="${G5_THRESHOLD_MS}" \
    python3 <<'PY'
import json, os
status_path = os.environ["STATUS_JSON"]
captured_at = os.environ["CAPTURED_AT"]
baseline_out = os.environ["BASELINE_OUT"]
candidate = os.environ.get("CANDIDATE_JSON") or None
threshold_ms = float(os.environ["G5_THRESHOLD_MS"])
baseline_doc = {}
try:
    baseline_doc = json.load(open(baseline_out))
except Exception:
    pass
blocker = baseline_doc.get("blocker") or (
    "reconstruct_hydration_baseline.py exited non-zero or emitted a "
    "placeholder (source={}); see {} and the apply environment's "
    "playwright/chromium installation."
).format(baseline_doc.get("source", "unknown"), baseline_out)
status = {
    "gate": "G5",
    "status": "blocked",
    "captured_at": captured_at,
    "baseline_path": baseline_out,
    "baseline_source": baseline_doc.get("source", "unknown"),
    "candidate_path": candidate,
    "regression": None,
    "threshold_ms": threshold_ms,
    "baseline_median_ms": None,
    "candidate_median_ms": None,
    "delta_ms": None,
    "blocker": blocker,
    "action_required": (
        "install playwright + chromium (per requirements-dev.txt) on the "
        "apply worker, then re-run scripts/g5_close.sh to produce a real "
        "captured baseline; G5 stays blocked until that runs."
    ),
}
with open(status_path, "w") as f:
    json.dump(status, f, indent=2)
    f.write("\n")
PY
  exit 2
fi

# ---------------------------------------------------------------------------
# Step 2 - if the React candidate build (`out/`) exists and the candidate
# artifact is missing, drive the candidate capture.
# ---------------------------------------------------------------------------
CANDIDATE_BUILD_DIR="${BUILD_DIR}"
CANDIDATE_OUT="${CANDIDATE_OUT_DEFAULT}"

if [[ -d "${CANDIDATE_BUILD_DIR}" && ! -f "${CANDIDATE_OUT}" ]]; then
  log "G5 1+9 step 2/4: candidate capture (build_dir=${CANDIDATE_BUILD_DIR})"
  log "  warmup_count:        ${G5_WARMUP_COUNT}"
  log "  samples_retained:    ${G5_SAMPLES_RETAINED}"
  CANDIDATE_CAPTURE_EXIT=0
  python3 "${REPO_ROOT}/scripts/capture_hydration_candidate.py" \
      --build-dir "${CANDIDATE_BUILD_DIR}" \
      --out "${CANDIDATE_OUT}" \
      --warmup-count "${G5_WARMUP_COUNT}" \
      --samples-retained "${G5_SAMPLES_RETAINED}" \
      || CANDIDATE_CAPTURE_EXIT=$?
  if [[ "${CANDIDATE_CAPTURE_EXIT}" -ne 0 ]]; then
    log "candidate capture failed (exit=${CANDIDATE_CAPTURE_EXIT}); leaving G5 blocked"
  fi
  if [[ -z "${G5_CANDIDATE:-}" && -f "${CANDIDATE_OUT}" ]]; then
    CANDIDATE_JSON="${CANDIDATE_OUT}"
  fi
elif [[ ! -d "${CANDIDATE_BUILD_DIR}" ]]; then
  log "G5 1+9 step 2/4: no candidate build_dir at ${CANDIDATE_BUILD_DIR}; skipping capture"
else
  log "G5 1+9 step 2/4: candidate artifact already present at ${CANDIDATE_OUT}; skipping capture"
fi

# ---------------------------------------------------------------------------
# Step 3 - run baseline vs candidate regression comparison (if candidate
# is available).
# ---------------------------------------------------------------------------
COMPARISON_EXIT=0
REGRESSION_JSON="{}"

if [[ -z "${CANDIDATE_JSON}" || ! -f "${CANDIDATE_JSON}" ]]; then
  log "no candidate artifact at ${CANDIDATE_JSON:-<unset>}; cannot compare"
  STATUS_JSON="${STATUS_JSON}" CAPTURED_AT="${CAPTURED_AT}" \
    BASELINE_OUT="${BASELINE_OUT}" G5_THRESHOLD_MS="${G5_THRESHOLD_MS}" \
    python3 <<'PY'
import json, os
status_path = os.environ["STATUS_JSON"]
captured_at = os.environ["CAPTURED_AT"]
baseline_out = os.environ["BASELINE_OUT"]
threshold_ms = float(os.environ["G5_THRESHOLD_MS"])
status = {
    "gate": "G5",
    "status": "blocked",
    "captured_at": captured_at,
    "baseline_path": baseline_out,
    "baseline_source": "captured",
    "candidate_path": None,
    "regression": None,
    "threshold_ms": threshold_ms,
    "baseline_median_ms": None,
    "candidate_median_ms": None,
    "delta_ms": None,
    "blocker": (
        "no candidate artifact available; the React candidate build "
        "has not yet been captured by the apply worker. Run the "
        "candidate capture (out/hydration-candidate.json) and re-run "
        "scripts/g5_close.sh."
    ),
    "action_required": (
        "produce out/hydration-candidate.json via the candidate capture "
        "step, then re-run scripts/g5_close.sh; G5 stays blocked until "
        "both baseline and candidate are real captures."
    ),
}
with open(status_path, "w") as f:
    json.dump(status, f, indent=2)
    f.write("\n")
PY
  exit 2
fi

log "G5 1+9 step 3/4: regression comparison"
log "  baseline:   ${BASELINE_OUT}"
log "  candidate:  ${CANDIDATE_JSON}"
log "  threshold:  ${G5_THRESHOLD_MS} ms"

CANDIDATE_SOURCE="$(python3 -c "
import json
try:
    doc = json.load(open('${CANDIDATE_JSON}'))
    print(doc.get('source', 'unknown'))
except Exception:
    print('unreadable')
" 2>/dev/null || echo "unreadable")"

CANDIDATE_BLOCKER="$(python3 -c "
import json
try:
    doc = json.load(open('${CANDIDATE_JSON}'))
    print(doc.get('blocker', ''))
except Exception:
    pass
" 2>/dev/null || true)"

if [[ "${CANDIDATE_SOURCE}" != "captured" ]]; then
  log "candidate artifact is NOT a real capture (source=${CANDIDATE_SOURCE}); G5 blocked"
  log "  blocker=${CANDIDATE_BLOCKER}"
  STATUS_JSON="${STATUS_JSON}" CAPTURED_AT="${CAPTURED_AT}" \
    BASELINE_OUT="${BASELINE_OUT}" CANDIDATE_JSON="${CANDIDATE_JSON}" \
    CANDIDATE_SOURCE="${CANDIDATE_SOURCE}" CANDIDATE_BLOCKER="${CANDIDATE_BLOCKER}" \
    G5_THRESHOLD_MS="${G5_THRESHOLD_MS}" \
    python3 <<'PY'
import json, os
status_path = os.environ["STATUS_JSON"]
captured_at = os.environ["CAPTURED_AT"]
baseline_out = os.environ["BASELINE_OUT"]
candidate = os.environ["CANDIDATE_JSON"]
candidate_source = os.environ["CANDIDATE_SOURCE"]
candidate_blocker = os.environ.get("CANDIDATE_BLOCKER") or ""
threshold_ms = float(os.environ["G5_THRESHOLD_MS"])
status = {
    "gate": "G5",
    "status": "blocked",
    "captured_at": captured_at,
    "baseline_path": baseline_out,
    "baseline_source": "captured",
    "candidate_path": candidate,
    "candidate_source": candidate_source,
    "regression": None,
    "threshold_ms": threshold_ms,
    "baseline_median_ms": None,
    "candidate_median_ms": None,
    "delta_ms": None,
    "blocker": (
        candidate_blocker
        or f"candidate artifact at {candidate} is not a real capture "
           f"(source={candidate_source}); the comparison must not run on "
           f"placeholder metrics."
    ),
    "action_required": (
        "fix the candidate capture so it produces source='captured' "
        "(see scripts/capture_hydration_candidate.py and the apply "
        "environment's playwright/chromium install) and re-run "
        "scripts/g5_close.sh."
    ),
}
with open(status_path, "w") as f:
    json.dump(status, f, indent=2)
    f.write("\n")
PY
  exit 2
fi

set +e
python3 "${REPO_ROOT}/scripts/measure_hydration.py" \
    --baseline "${BASELINE_OUT}" \
    --candidate "${CANDIDATE_JSON}" \
    --report-out "${REPORT_JSON}"
COMPARISON_EXIT=$?
set -e

# ---------------------------------------------------------------------------
# Step 4 - record the verdict
# ---------------------------------------------------------------------------
if [[ "${COMPARISON_EXIT}" -ne 0 ]]; then
  log "comparison exited non-zero (regression or schema failure); G5 blocked"
  STATUS_JSON="${STATUS_JSON}" CAPTURED_AT="${CAPTURED_AT}" \
    BASELINE_OUT="${BASELINE_OUT}" CANDIDATE_JSON="${CANDIDATE_JSON}" \
    REPORT_JSON="${REPORT_JSON}" COMPARISON_EXIT="${COMPARISON_EXIT}" \
    G5_THRESHOLD_MS="${G5_THRESHOLD_MS}" \
    python3 <<'PY'
import json, os
status_path = os.environ["STATUS_JSON"]
captured_at = os.environ["CAPTURED_AT"]
baseline_out = os.environ["BASELINE_OUT"]
candidate = os.environ["CANDIDATE_JSON"]
report = os.environ["REPORT_JSON"]
comp_exit = int(os.environ["COMPARISON_EXIT"])
threshold_ms = float(os.environ["G5_THRESHOLD_MS"])
baseline_median_ms = None
candidate_median_ms = None
delta_ms = None
try:
    rep = json.load(open(report))
    baseline_median_ms = rep.get("baseline_median_ms")
    candidate_median_ms = rep.get("candidate_median_ms")
    delta_ms = rep.get("delta_ms")
except Exception:
    pass
status = {
    "gate": "G5",
    "status": "blocked",
    "captured_at": captured_at,
    "baseline_path": baseline_out,
    "baseline_source": "captured",
    "candidate_path": candidate,
    "regression": True,
    "threshold_ms": threshold_ms,
    "baseline_median_ms": baseline_median_ms,
    "candidate_median_ms": candidate_median_ms,
    "delta_ms": delta_ms,
    "comparison_exit_code": comp_exit,
    "blocker": (
        f"measure_hydration.py exited {comp_exit}; baseline vs candidate "
        f"comparison regressed (delta_ms={delta_ms} exceeds threshold "
        f"{threshold_ms} ms). G5 must NOT flip until delta_ms <= "
        f"{threshold_ms} ms."
    ),
    "action_required": (
        f"fix the candidate so the absolute DOMContentLoaded median "
        f"delta is <= {threshold_ms} ms vs baseline, then re-capture "
        f"and re-run scripts/g5_close.sh."
    ),
}
with open(status_path, "w") as f:
    json.dump(status, f, indent=2)
    f.write("\n")
PY
  exit 2
fi

# Both preconditions met - record ready status but DO NOT flip the gate
# from this script. The apply worker is the only authority that may flip
# G5 (per openspec/.../apply-progress.md §Cutover activation sequence).
log "G5 1+9 step 4/4: preconditions met; status=ready (G5 still gated on apply worker)"
STATUS_JSON="${STATUS_JSON}" CAPTURED_AT="${CAPTURED_AT}" \
  BASELINE_OUT="${BASELINE_OUT}" CANDIDATE_JSON="${CANDIDATE_JSON}" \
  REPORT_JSON="${REPORT_JSON}" G5_THRESHOLD_MS="${G5_THRESHOLD_MS}" \
  python3 <<'PY'
import json, os
status_path = os.environ["STATUS_JSON"]
captured_at = os.environ["CAPTURED_AT"]
baseline_out = os.environ["BASELINE_OUT"]
candidate = os.environ["CANDIDATE_JSON"]
report = os.environ["REPORT_JSON"]
threshold_ms = float(os.environ["G5_THRESHOLD_MS"])
rep = {}
try:
    rep = json.load(open(report))
except Exception:
    pass
status = {
    "gate": "G5",
    "status": "ready",
    "captured_at": captured_at,
    "baseline_path": baseline_out,
    "baseline_source": "captured",
    "candidate_path": candidate,
    "regression": False,
    "threshold_ms": threshold_ms,
    "baseline_median_ms": rep.get("baseline_median_ms"),
    "candidate_median_ms": rep.get("candidate_median_ms"),
    "delta_ms": rep.get("delta_ms"),
    "blocker": None,
    "action_required": (
        "apply worker may now flip G5 to PASS in apply-progress.md §Status "
        "(see openspec/.../tasks.md §Cutover activation sequence step 5)."
    ),
}
with open(status_path, "w") as f:
    json.dump(status, f, indent=2)
    f.write("\n")
PY
exit 0