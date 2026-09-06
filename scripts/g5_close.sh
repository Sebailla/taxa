#!/usr/bin/env bash
# Phase 6a G5 hydration-baseline runtime harness.
#
# Authoritative contract (per openspec/changes/complete-taxa-frontend-migration
# /tasks.md §Phase 6a, and the user authorization for Phase 6a):
#
#   1. Run `scripts/reconstruct_hydration_baseline.py` to produce the
#      legacy baseline artifact (or a fail-closed placeholder).
#   2. If the React candidate build (`out/`) exists and the candidate
#      artifact (`out/hydration-candidate.json`) is missing, run
#      `scripts/capture_hydration_candidate.py` to drive Playwright +
#      Chromium against a local static server that serves `out/`, and
#      emit the candidate artifact (or a fail-closed placeholder).
#   3. Run `scripts/measure_hydration.py --baseline <b> --candidate <c>
#      --report-out <r>` against the positions 1-12-landed candidate
#      build (Phase 6a only runs after positions 1-12 land; in the
#      current apply phase the candidate is also gated by the same
#      "candidate must exist" precondition).
#   4. Write a versioned status record under
#      `openspec/changes/complete-taxa-frontend-migration/evidence/g5/`
#      so the apply worker can audit the harness without re-running it.
#
# The harness is fail-closed by construction. It MUST NEVER flip G5:
# the apply worker is the only authority that may flip the gate, and
# only after both:
#   * the captured baseline is `source: "captured"` (NOT a placeholder)
#   * the baseline vs candidate comparison exits 0 (no regression)
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
#   0  Both preconditions met (real baseline + non-regressing
#      comparison). G5 may flip on the apply worker's separate
#      authority; this script does NOT flip the gate.
#   2  Precondition not met (placeholder baseline or regression
#      detected); status.json records the reason.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE_DIR="${REPO_ROOT}/openspec/changes/complete-taxa-frontend-migration/evidence/g5"

FIXTURE_WEB_ROOT="${G5_FIXTURE_WEB_ROOT:-${REPO_ROOT}/tools/g3-legacy-fixture/web}"
BASELINE_OUT="${G5_OUT:-${REPO_ROOT}/web/dist/evidence-baseline.json}"
BUILD_DIR="${G5_BUILD_DIR:-${REPO_ROOT}/out}"
CANDIDATE_OUT_DEFAULT="${REPO_ROOT}/out/hydration-candidate.json"

CANDIDATE_JSON=""
if [[ -n "${G5_CANDIDATE:-}" ]]; then
  CANDIDATE_JSON="${G5_CANDIDATE}"
elif [[ -f "${CANDIDATE_OUT_DEFAULT}" ]]; then
  # Convention: positions 1-12 build's Playwright capture is written
  # here by the apply worker's separate capture step (or by Step 2
  # below when the build directory exists but the artifact is
  # missing). If absent after Step 2, there is nothing to compare
  # against and G5 stays blocked.
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
log "Phase 6a step 1/4: reconstruct legacy baseline"
log "  fixture_web_root: ${FIXTURE_WEB_ROOT}"
log "  out:              ${BASELINE_OUT}"

CAPTURE_EXIT=0
python3 "${REPO_ROOT}/scripts/reconstruct_hydration_baseline.py" \
    --fixture-web-root "${FIXTURE_WEB_ROOT}" \
    --out "${BASELINE_OUT}" || CAPTURE_EXIT=$?

BASELINE_SOURCE="$(python3 -c "
import json, sys
try:
    doc = json.load(open('${BASELINE_OUT}'))
    print(doc.get('source', 'unknown'))
except Exception as e:
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
  python3 - "${STATUS_JSON}" "${CAPTURED_AT}" "${BASELINE_OUT}" "${CANDIDATE_JSON:-}" <<'PY'
import json, sys, datetime, os
status_path, captured_at, baseline_out, candidate = sys.argv[1:5]
baseline_doc = {}
try:
    baseline_doc = json.load(open(baseline_out))
except Exception:
    pass
blocker = baseline_doc.get("blocker") or (
    f"reconstruct_hydration_baseline.py exited non-zero or emitted a "
    f"placeholder (source={baseline_doc.get('source','unknown')}); see "
    f"{baseline_out} and the apply environment's playwright/chromium "
    f"installation."
)
status = {
    "gate": "G5",
    "status": "blocked",
    "captured_at": captured_at,
    "baseline_path": baseline_out,
    "baseline_source": baseline_doc.get("source", "unknown"),
    "candidate_path": candidate or None,
    "regression": None,
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
# artifact is missing, drive the candidate capture. This step is the
# minimal extension that closes the Phase 6a gap: the harness now
# produces BOTH halves of the comparison instead of waiting for a
# separate apply-worker invocation. The capture itself is fail-closed
# (it writes a placeholder on any failure); the harness then surfaces
# the candidate source in `status.json` so the apply worker can
# distinguish a captured candidate from a placeholder.
# ---------------------------------------------------------------------------
CANDIDATE_BUILD_DIR="${BUILD_DIR}"
CANDIDATE_OUT="${CANDIDATE_OUT_DEFAULT}"

if [[ -d "${CANDIDATE_BUILD_DIR}" && ! -f "${CANDIDATE_OUT}" ]]; then
  log "Phase 6a step 2/4: candidate capture (build_dir=${CANDIDATE_BUILD_DIR})"
  CANDIDATE_CAPTURE_EXIT=0
  python3 "${REPO_ROOT}/scripts/capture_hydration_candidate.py" \
      --build-dir "${CANDIDATE_BUILD_DIR}" \
      --out "${CANDIDATE_OUT}" \
      || CANDIDATE_CAPTURE_EXIT=$?
  if [[ "${CANDIDATE_CAPTURE_EXIT}" -ne 0 ]]; then
    log "candidate capture failed (exit=${CANDIDATE_CAPTURE_EXIT}); leaving G5 blocked"
  fi
  # Re-resolve CANDIDATE_JSON in case the capture wrote the artifact
  # even on a non-zero exit (placeholder path).
  if [[ -z "${G5_CANDIDATE:-}" && -f "${CANDIDATE_OUT}" ]]; then
    CANDIDATE_JSON="${CANDIDATE_OUT}"
  fi
elif [[ ! -d "${CANDIDATE_BUILD_DIR}" ]]; then
  log "Phase 6a step 2/4: no candidate build_dir at ${CANDIDATE_BUILD_DIR}; skipping capture"
else
  log "Phase 6a step 2/4: candidate artifact already present at ${CANDIDATE_OUT}; skipping capture"
fi

# ---------------------------------------------------------------------------
# Step 3 - run baseline vs candidate regression comparison (if candidate
# is available). If absent, this is also a fail-closed precondition.
# ---------------------------------------------------------------------------
COMPARISON_EXIT=0
REGRESSION_JSON="{}"

if [[ -z "${CANDIDATE_JSON}" || ! -f "${CANDIDATE_JSON}" ]]; then
  log "no candidate artifact at ${CANDIDATE_JSON:-<unset>}; cannot compare"
  python3 - "${STATUS_JSON}" "${CAPTURED_AT}" "${BASELINE_OUT}" "" <<'PY'
import json, sys
status_path, captured_at, baseline_out, _ = sys.argv[1:5]
status = {
    "gate": "G5",
    "status": "blocked",
    "captured_at": captured_at,
    "baseline_path": baseline_out,
    "baseline_source": "captured",
    "candidate_path": None,
    "regression": None,
    "blocker": (
        "no candidate artifact available; the positions 1-12-landed "
        "candidate build has not yet been captured by the apply worker. "
        "Run the candidate capture (out/hydration-candidate.json) and "
        "re-run scripts/g5_close.sh."
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

log "Phase 6a step 3/4: regression comparison"
log "  baseline: ${BASELINE_OUT}"
log "  candidate: ${CANDIDATE_JSON}"

# Source gate: the comparison MUST only run when the candidate is a
# real capture (`source: "captured"`). A placeholder has source
# "unavailable" and all-zero metrics; comparing it against the real
# baseline would report an arbitrary improvement (delta = -100%)
# that masks the actual environmental blocker. Treat the placeholder
# as a fail-closed precondition.
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
  python3 - "${STATUS_JSON}" "${CAPTURED_AT}" "${BASELINE_OUT}" "${CANDIDATE_JSON}" "${CANDIDATE_SOURCE}" "${CANDIDATE_BLOCKER}" <<'PY'
import json, sys
(status_path, captured_at, baseline_out, candidate, candidate_source, candidate_blocker) = sys.argv[1:7]
status = {
    "gate": "G5",
    "status": "blocked",
    "captured_at": captured_at,
    "baseline_path": baseline_out,
    "baseline_source": "captured",
    "candidate_path": candidate,
    "candidate_source": candidate_source,
    "regression": None,
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
  python3 - "${STATUS_JSON}" "${CAPTURED_AT}" "${BASELINE_OUT}" "${CANDIDATE_JSON}" "${REPORT_JSON}" "${COMPARISON_EXIT}" <<'PY'
import json, sys
(status_path, captured_at, baseline_out, candidate, report, comp_exit) = sys.argv[1:7]
regression_axes = []
initial_paint_delta = None
interaction_latency_delta = None
try:
    rep = json.load(open(report))
    regression_axes = rep.get("regressing_axes", [])
    initial_paint_delta = rep.get("initial_paint_delta_pct")
    interaction_latency_delta = rep.get("interaction_latency_delta_pct")
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
    "regressing_axes": regression_axes,
    "initial_paint_delta_pct": initial_paint_delta,
    "interaction_latency_delta_pct": interaction_latency_delta,
    "comparison_exit_code": int(comp_exit),
    "blocker": (
        f"measure_hydration.py exited {comp_exit}; baseline vs candidate "
        f"comparison regressed on {', '.join(regression_axes) or 'unknown axis'}. "
        f"G5 must NOT flip until both deltas are <= 0 %."
    ),
    "action_required": (
        "fix the candidate so neither initial_paint nor interaction_latency "
        "regress vs baseline, then re-capture and re-run scripts/g5_close.sh."
    ),
}
with open(status_path, "w") as f:
    json.dump(status, f, indent=2)
    f.write("\n")
PY
  exit 2
fi

# Both preconditions met - record PASS but DO NOT flip the gate from
# this script. The apply worker is the only authority that may flip
# G5 (per openspec/.../apply-progress.md §Cutover activation sequence).
log "Phase 6a step 4/4: preconditions met; status=ready (G5 still gated on apply worker)"
python3 - "${STATUS_JSON}" "${CAPTURED_AT}" "${BASELINE_OUT}" "${CANDIDATE_JSON}" "${REPORT_JSON}" <<'PY'
import json, sys
(status_path, captured_at, baseline_out, candidate, report) = sys.argv[1:6]
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
    "regressing_axes": [],
    "initial_paint_delta_pct": rep.get("initial_paint_delta_pct"),
    "interaction_latency_delta_pct": rep.get("interaction_latency_delta_pct"),
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
