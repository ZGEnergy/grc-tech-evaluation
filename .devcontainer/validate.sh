#!/usr/bin/env bash
#
# validate.sh -- Smoke-test all six power-system tools inside the devcontainer.
#
# Usage:  bash .devcontainer/validate.sh
#
# Runs each tool's verify_install script in sequence. Exits non-zero on the
# first failure. Must be run from inside the devcontainer where all runtimes
# and dependencies are pre-installed (see PRD-01 Dockerfile).

set -euo pipefail

# Resolve the repository root relative to this script's location.
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EVAL_DIR="${REPO_ROOT}/evaluations"

passed=0
failed=0

run_tool() {
    local tool="$1"
    shift
    printf "%-20s" "${tool}..."
    if "$@"; then
        echo "PASS"
        ((passed++)) || true
    else
        echo "FAIL"
        ((failed++)) || true
        exit 1
    fi
}

echo "=== Smoke Test Validation ==="
echo ""

# --- Python tools (uv run, each in its own .venv) ---
run_tool "gridcal" \
    uv run --project "${EVAL_DIR}/gridcal" python "${EVAL_DIR}/gridcal/verify_install.py"

run_tool "pandapower" \
    uv run --project "${EVAL_DIR}/pandapower" python "${EVAL_DIR}/pandapower/verify_install.py"

run_tool "pypsa" \
    uv run --project "${EVAL_DIR}/pypsa" python "${EVAL_DIR}/pypsa/verify_install.py"

# --- Julia tools (julia --project) ---
run_tool "powermodels" \
    julia --project="${EVAL_DIR}/powermodels" "${EVAL_DIR}/powermodels/verify_install.jl"

run_tool "powersimulations" \
    julia --project="${EVAL_DIR}/powersimulations" "${EVAL_DIR}/powersimulations/verify_install.jl"

# --- Octave tool (must cd for relative path in verify_install.m) ---
run_tool "matpower" \
    bash -c "cd '${EVAL_DIR}/matpower' && octave --no-gui --eval 'run(\"verify_install.m\")'"

echo ""
echo "=== Results: ${passed} passed, ${failed} failed ==="
exit 0
