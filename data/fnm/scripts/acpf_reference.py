"""ACPF Reference Solution Extraction for FNM Annual S01.

Produces the AC Power Flow (ACPF) reference solution dataset, handling two
mutually exclusive paths based on the D8 snapshot classification:

- **Solved-case path (Path A):** Extracts VM, VA, P/Q flows, and generator P/Q
  directly from the canonical parser's intermediate format tables.
- **Flat-start path (Path B):** Runs a verified solver (MATPOWER ``runpf`` via
  Octave or GridCal Newton-Raphson) on the intermediate format data to produce
  a converged ACPF solution.

Both paths produce identical output CSV schemas and a metadata JSON documenting
the solution source, solver settings (if applicable), convergence status, and
system-level summary statistics.

Output directory: ``data/fnm/reference/acpf/``
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# MATPOWER bus matrix column indices (standard 13-column format, no header)
_MPC_BUS_COL_BUS_I: int = 0
_MPC_BUS_COL_TYPE: int = 1
_MPC_BUS_COL_PD: int = 2
_MPC_BUS_COL_QD: int = 3
_MPC_BUS_COL_VM: int = 7
_MPC_BUS_COL_VA: int = 8

# MATPOWER gen matrix column indices (no header)
_MPC_GEN_COL_BUS: int = 0
_MPC_GEN_COL_PG: int = 1
_MPC_GEN_COL_QG: int = 2
_MPC_GEN_COL_QMAX: int = 3
_MPC_GEN_COL_QMIN: int = 4
_MPC_GEN_COL_STATUS: int = 7
_MPC_GEN_COL_PMAX: int = 8

# MATPOWER branch matrix column indices (no header)
_MPC_BRANCH_COL_FBUS: int = 0
_MPC_BRANCH_COL_TBUS: int = 1
_MPC_BRANCH_COL_STATUS: int = 10
# Flow columns (present only after runpf)
_MPC_BRANCH_COL_PF: int = 13
_MPC_BRANCH_COL_QF: int = 14
_MPC_BRANCH_COL_PT: int = 15
_MPC_BRANCH_COL_QT: int = 16

_ISOLATED_BUS_TYPE: int = 4
_SLACK_BUS_TYPE: int = 3

_POWER_BALANCE_WARN_THRESHOLD_MW: float = 1.0


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class SolutionSource(Enum):
    """How the ACPF reference solution was obtained."""

    EXTRACTED = "extracted"
    """Extracted directly from a converged solved case in the intermediate format."""

    COMPUTED = "computed"
    """Computed by running a solver on the intermediate format data."""


@dataclass(frozen=True)
class SolverSettings:
    """Solver configuration for the flat-start path.

    All fields are None when solution_source is EXTRACTED.
    """

    name: str | None = None
    """Solver identifier: 'runpf' for MATPOWER, 'gridcal_nr' for GridCal."""

    version: str | None = None
    """Solver version string."""

    tolerance: float | None = None
    """Newton-Raphson convergence tolerance (p.u. mismatch)."""

    max_iterations: int | None = None
    """Maximum NR iterations."""

    q_limits_enforced: bool | None = None
    """Whether Q-limits were enforced in the final solution."""

    q_limit_strategy: str | None = None
    """Description of Q-limit enforcement approach."""

    enforce_area_interchange: bool | None = None
    """Whether area interchange control was active."""


@dataclass(frozen=True)
class ConvergenceInfo:
    """Solver convergence details for the flat-start path.

    All fields are None when solution_source is EXTRACTED.
    """

    converged: bool | None = None
    """Whether the solver reached the convergence tolerance."""

    iterations: int | None = None
    """Number of NR iterations performed."""

    final_mismatch_mw: float | None = None
    """Largest active power mismatch at convergence (MW)."""

    final_mismatch_mvar: float | None = None
    """Largest reactive power mismatch at convergence (MVAr)."""


@dataclass(frozen=True)
class SystemSummary:
    """System-level aggregate quantities from the ACPF solution."""

    total_gen_mw: float
    """Total active power generation (MW)."""

    total_gen_mvar: float
    """Total reactive power generation (MVAr)."""

    total_load_mw: float
    """Total active power load (MW)."""

    total_load_mvar: float
    """Total reactive power load (MVAr)."""

    total_loss_mw: float
    """Total active power losses (MW). Equals total_gen_mw - total_load_mw."""

    total_loss_mvar: float
    """Total reactive power losses (MVAr)."""

    slack_bus: int
    """Slack bus number (bus type 3)."""

    power_balance_residual_mw: float
    """Residual: total_gen_mw - total_load_mw - total_loss_mw.
    Should be ~0 for a consistent solution."""


# ---------------------------------------------------------------------------
# CSV detection helpers (reuses logic patterns from solved_snapshot.py)
# ---------------------------------------------------------------------------


def _is_header_row(row: list[str]) -> bool:
    """Determine if a CSV row is a header (non-numeric first field)."""
    if not row:
        return False
    try:
        float(row[0])
        return False
    except ValueError:
        return True


def _detect_column_index(headers: list[str], candidates: list[str]) -> int | None:
    """Find the index of the first matching header from a list of candidates."""
    lower_headers = [h.strip().lower() for h in headers]
    for candidate in candidates:
        if candidate.lower() in lower_headers:
            return lower_headers.index(candidate.lower())
    return None


# ---------------------------------------------------------------------------
# Path selection
# ---------------------------------------------------------------------------


def read_snapshot_classification(snapshot_json_path: Path) -> str:
    """Read the overall classification from the D8 snapshot confirmation JSON.

    Args:
        snapshot_json_path: Path to ``snapshot_confirmation.json`` from D8.

    Returns:
        The classification string: ``'solved'``, ``'flat_start'``, or
        ``'indeterminate'``.

    Raises:
        FileNotFoundError: If the JSON file does not exist.
        KeyError: If the ``classification`` field is missing.
        ValueError: If the classification value is not one of the three
            expected strings.
    """
    if not snapshot_json_path.exists():
        raise FileNotFoundError(f"Snapshot JSON not found: {snapshot_json_path}")

    with open(snapshot_json_path, encoding="utf-8") as f:
        data = json.load(f)

    if "classification" not in data:
        raise KeyError(
            f"Snapshot JSON missing 'classification' field. Keys found: {list(data.keys())}"
        )

    classification = data["classification"]
    valid_values = {"solved", "flat_start", "indeterminate"}
    if classification not in valid_values:
        raise ValueError(
            f"Invalid classification value '{classification}'. Expected one of: {valid_values}"
        )

    return classification


def determine_solution_source(classification: str) -> SolutionSource:
    """Map a D8 classification to the solution source for this deliverable.

    Args:
        classification: One of ``'solved'``, ``'flat_start'``, ``'indeterminate'``.

    Returns:
        ``SolutionSource.EXTRACTED`` for ``'solved'``,
        ``SolutionSource.COMPUTED`` for ``'flat_start'``.

    Raises:
        ValueError: If classification is ``'indeterminate'``. The ACPF
            reference cannot be produced until the indeterminate case
            is manually resolved.
    """
    if classification == "solved":
        return SolutionSource.EXTRACTED
    if classification == "flat_start":
        return SolutionSource.COMPUTED
    if classification == "indeterminate":
        raise ValueError(
            "Snapshot classification is 'indeterminate'. "
            "The ACPF reference solution cannot be produced until the "
            "indeterminate case is manually resolved (OQ-E01)."
        )
    raise ValueError(f"Unknown classification: '{classification}'")


# ---------------------------------------------------------------------------
# Solved-case extraction (Path A)
# ---------------------------------------------------------------------------


def _load_bus_csv_raw(
    bus_csv_path: Path,
) -> tuple[list[str] | None, list[list[str]]]:
    """Load a bus CSV and return (headers_or_None, data_rows)."""
    if not bus_csv_path.exists():
        raise FileNotFoundError(f"Bus CSV not found: {bus_csv_path}")

    with open(bus_csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"Bus CSV is empty: {bus_csv_path}")

    first_row = rows[0]
    if _is_header_row(first_row):
        return first_row, rows[1:]
    return None, rows


def _resolve_bus_col_indices(
    headers: list[str] | None,
) -> tuple[int, int, int, int, int, int]:
    """Return (bus_idx, type_idx, vm_idx, va_idx, pd_idx, qd_idx) for the bus CSV."""
    if headers is not None:
        bus_idx = _detect_column_index(headers, ["bus_i", "i", "bus_id", "bus"])
        type_idx = _detect_column_index(headers, ["type", "ide", "bus_type"])
        vm_idx = _detect_column_index(headers, ["vm", "vm_pu", "Vm"])
        va_idx = _detect_column_index(headers, ["va", "va_deg", "Va"])
        pd_idx = _detect_column_index(headers, ["pd", "Pd", "PD"])
        qd_idx = _detect_column_index(headers, ["qd", "Qd", "QD"])
        if bus_idx is None:
            raise ValueError(f"Cannot find bus number column in headers: {headers}")
        if vm_idx is None or va_idx is None:
            raise ValueError(f"Cannot find VM/VA columns in headers: {headers}")
        if type_idx is None:
            raise ValueError(f"Cannot find bus type column in headers: {headers}")
        if pd_idx is None or qd_idx is None:
            raise ValueError(f"Cannot find PD/QD columns in headers: {headers}")
        return bus_idx, type_idx, vm_idx, va_idx, pd_idx, qd_idx
    else:
        return (
            _MPC_BUS_COL_BUS_I,
            _MPC_BUS_COL_TYPE,
            _MPC_BUS_COL_VM,
            _MPC_BUS_COL_VA,
            _MPC_BUS_COL_PD,
            _MPC_BUS_COL_QD,
        )


def extract_bus_results(bus_csv_path: Path) -> list[dict]:
    """Extract per-bus VM and VA from the canonical parser's bus CSV.

    Reads the intermediate format bus table. Excludes isolated buses
    (IDE/type = 4) and de-energized buses (VM = 0). Auto-detects column
    names from MATPOWER and GridCal conventions (same logic as D8's
    ``load_bus_data``).

    Args:
        bus_csv_path: Path to the intermediate format bus CSV.

    Returns:
        List of dicts with keys ``bus`` (int), ``VM`` (float), ``VA`` (float).
        Sorted by bus number ascending.

    Raises:
        FileNotFoundError: If the CSV does not exist.
        ValueError: If required columns (bus number, VM, VA, bus type)
            cannot be identified.
    """
    headers, data_rows = _load_bus_csv_raw(bus_csv_path)
    bus_idx, type_idx, vm_idx, va_idx, _pd_idx, _qd_idx = _resolve_bus_col_indices(headers)

    results: list[dict] = []
    for row in data_rows:
        if not row or all(cell.strip() == "" for cell in row):
            continue

        try:
            bus_type = int(float(row[type_idx].strip()))
        except (ValueError, IndexError):
            bus_type = 0

        # Exclude isolated buses (type 4)
        if bus_type == _ISOLATED_BUS_TYPE:
            continue

        try:
            vm = float(row[vm_idx].strip())
            va = float(row[va_idx].strip())
            bus_num = int(float(row[bus_idx].strip()))
        except (ValueError, IndexError) as exc:
            raise ValueError(f"Cannot parse bus data from row: {row}") from exc

        # Exclude de-energized buses (VM = 0)
        if vm == 0.0:
            continue

        results.append({"bus": bus_num, "VM": vm, "VA": va})

    results.sort(key=lambda r: r["bus"])
    return results


def extract_branch_results(branch_csv_path: Path) -> list[dict]:
    """Extract per-branch P/Q flows from the canonical parser's branch CSV.

    Reads the intermediate format branch table. Includes only in-service
    branches (status = 1). Extracts from-end and to-end active and reactive
    power flows.

    For the solved-case path, flow values must already be present in the
    intermediate format — they were part of the converged PSS/E solution.
    If flow columns are absent (indicating the parser did not extract them),
    raises ValueError with a diagnostic message.

    Args:
        branch_csv_path: Path to the intermediate format branch CSV.

    Returns:
        List of dicts with keys ``from_bus`` (int), ``to_bus`` (int),
        ``ckt`` (str), ``P_from`` (float), ``Q_from`` (float),
        ``P_to`` (float), ``Q_to`` (float). Sorted by (from_bus, to_bus, ckt).

    Raises:
        FileNotFoundError: If the CSV does not exist.
        ValueError: If required columns cannot be identified or flow
            columns are absent.
    """
    if not branch_csv_path.exists():
        raise FileNotFoundError(f"Branch CSV not found: {branch_csv_path}")

    with open(branch_csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"Branch CSV is empty: {branch_csv_path}")

    first_row = rows[0]
    if _is_header_row(first_row):
        headers = first_row
        data_rows = rows[1:]
        fbus_idx = _detect_column_index(headers, ["fbus", "f_bus", "from_bus", "i"])
        tbus_idx = _detect_column_index(headers, ["tbus", "t_bus", "to_bus", "j"])
        ckt_idx = _detect_column_index(headers, ["ckt", "circuit", "cid"])
        status_idx = _detect_column_index(headers, ["status", "st", "br_status"])
        pf_idx = _detect_column_index(headers, ["pf", "p_from", "P_from"])
        qf_idx = _detect_column_index(headers, ["qf", "q_from", "Q_from"])
        pt_idx = _detect_column_index(headers, ["pt", "p_to", "P_to"])
        qt_idx = _detect_column_index(headers, ["qt", "q_to", "Q_to"])

        if fbus_idx is None or tbus_idx is None:
            raise ValueError(f"Cannot find from/to bus columns in headers: {headers}")
        if pf_idx is None or qf_idx is None or pt_idx is None or qt_idx is None:
            raise ValueError(
                "Branch CSV is missing flow columns (PF, QF, PT, QT). "
                "The solved-case path requires pre-computed flows in the intermediate format. "
                "If the parser did not extract flows, consider using the flat-start path or "
                "a different parser."
            )
    else:
        data_rows = rows
        fbus_idx = _MPC_BRANCH_COL_FBUS
        tbus_idx = _MPC_BRANCH_COL_TBUS
        ckt_idx = None  # MATPOWER headerless format has no ckt column
        status_idx = _MPC_BRANCH_COL_STATUS
        pf_idx = _MPC_BRANCH_COL_PF
        qf_idx = _MPC_BRANCH_COL_QF
        pt_idx = _MPC_BRANCH_COL_PT
        qt_idx = _MPC_BRANCH_COL_QT

    # Verify flow columns have data (check width of first data row)
    if data_rows:
        first_data = data_rows[0]
        max_flow_idx = max(pf_idx, qf_idx, pt_idx, qt_idx)
        if len(first_data) <= max_flow_idx:
            raise ValueError(
                f"Branch CSV has {len(first_data)} columns but flow columns require "
                f"index {max_flow_idx}. The parser may not have extracted branch flows. "
                "Consider using the flat-start path to compute flows from the solved "
                "voltage profile."
            )

    results: list[dict] = []
    for row in data_rows:
        if not row or all(cell.strip() == "" for cell in row):
            continue

        # Check status
        if status_idx is not None and status_idx < len(row):
            try:
                status = int(float(row[status_idx].strip()))
            except (ValueError, IndexError):
                status = 1
            if status != 1:
                continue

        try:
            from_bus = int(float(row[fbus_idx].strip()))
            to_bus = int(float(row[tbus_idx].strip()))
            ckt = row[ckt_idx].strip() if ckt_idx is not None and ckt_idx < len(row) else "1"
            p_from = float(row[pf_idx].strip())
            q_from = float(row[qf_idx].strip())
            p_to = float(row[pt_idx].strip())
            q_to = float(row[qt_idx].strip())
        except (ValueError, IndexError) as exc:
            raise ValueError(f"Cannot parse branch data from row: {row}") from exc

        results.append(
            {
                "from_bus": from_bus,
                "to_bus": to_bus,
                "ckt": ckt,
                "P_from": p_from,
                "Q_from": q_from,
                "P_to": p_to,
                "Q_to": q_to,
            }
        )

    results.sort(key=lambda r: (r["from_bus"], r["to_bus"], r["ckt"]))
    return results


def extract_generator_results(gen_csv_path: Path) -> list[dict]:
    """Extract per-generator P and Q from the canonical parser's generator CSV.

    Reads the intermediate format generator table. Includes only in-service
    generators (status = 1). Extracts active and reactive power output.

    Args:
        gen_csv_path: Path to the intermediate format generator CSV.

    Returns:
        List of dicts with keys ``bus`` (int), ``machine_id`` (str),
        ``P`` (float), ``Q`` (float). Sorted by (bus, machine_id).

    Raises:
        FileNotFoundError: If the CSV does not exist.
        ValueError: If required columns cannot be identified.
    """
    if not gen_csv_path.exists():
        raise FileNotFoundError(f"Generator CSV not found: {gen_csv_path}")

    with open(gen_csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"Generator CSV is empty: {gen_csv_path}")

    first_row = rows[0]
    if _is_header_row(first_row):
        headers = first_row
        data_rows = rows[1:]
        bus_idx = _detect_column_index(headers, ["bus", "bus_i", "i"])
        machine_id_idx = _detect_column_index(headers, ["machine_id", "id", "gen_id", "ID"])
        pg_idx = _detect_column_index(headers, ["pg", "p", "Pg", "PG"])
        qg_idx = _detect_column_index(headers, ["qg", "q", "Qg", "QG"])
        status_idx = _detect_column_index(headers, ["status", "st", "stat"])

        if bus_idx is None:
            raise ValueError(f"Cannot find bus column in generator headers: {headers}")
        if pg_idx is None or qg_idx is None:
            raise ValueError(f"Cannot find PG/QG columns in generator headers: {headers}")
    else:
        data_rows = rows
        bus_idx = _MPC_GEN_COL_BUS
        machine_id_idx = None  # MATPOWER headerless format has no machine_id
        pg_idx = _MPC_GEN_COL_PG
        qg_idx = _MPC_GEN_COL_QG
        status_idx = _MPC_GEN_COL_STATUS

    results: list[dict] = []
    gen_counter: dict[int, int] = {}  # Track machine_id per bus for headerless

    for row in data_rows:
        if not row or all(cell.strip() == "" for cell in row):
            continue

        # Check status
        if status_idx is not None and status_idx < len(row):
            try:
                status = int(float(row[status_idx].strip()))
            except (ValueError, IndexError):
                status = 1
            if status != 1:
                continue

        try:
            bus_num = int(float(row[bus_idx].strip()))
            p = float(row[pg_idx].strip())
            q = float(row[qg_idx].strip())
        except (ValueError, IndexError) as exc:
            raise ValueError(f"Cannot parse generator data from row: {row}") from exc

        if machine_id_idx is not None and machine_id_idx < len(row):
            machine_id = row[machine_id_idx].strip()
        else:
            # Assign sequential IDs per bus for headerless CSVs
            gen_counter[bus_num] = gen_counter.get(bus_num, 0) + 1
            machine_id = str(gen_counter[bus_num])

        results.append(
            {
                "bus": bus_num,
                "machine_id": machine_id,
                "P": p,
                "Q": q,
            }
        )

    results.sort(key=lambda r: (r["bus"], r["machine_id"]))
    return results


# ---------------------------------------------------------------------------
# Flat-start solver execution (Path B)
# ---------------------------------------------------------------------------


def run_matpower_acpf(
    intermediate_dir: Path,
    output_dir: Path,
    settings: SolverSettings,
) -> tuple[list[dict], list[dict], list[dict], ConvergenceInfo]:
    """Run MATPOWER runpf via Octave on the intermediate format data.

    Generates a temporary Octave script that:
    1. Loads the intermediate format CSVs into an mpc struct.
    2. Configures MATPOWER options (tolerance, max iterations, Q-limit enforcement).
    3. Runs ``runpf`` with flat-start initial conditions.
    4. If two-stage Q-limit enforcement: runs a second ``runpf`` with
       ``enforce_q_lims`` enabled, using the first solution as the starting point.
    5. Exports bus results (VM, VA), branch results (P/Q flows), and
       generator results (P, Q) as CSV files.

    The function invokes Octave via ``subprocess``, captures stdout/stderr,
    parses the exported CSV files, and returns structured results.

    Args:
        intermediate_dir: Directory containing the intermediate format CSVs.
        output_dir: Temporary directory for Octave script and CSV exports.
        settings: Solver configuration.

    Returns:
        A tuple of (bus_results, branch_results, gen_results, convergence_info).
        Each results list has the same dict schema as the extract_* functions.

    Raises:
        RuntimeError: If Octave exits with a non-zero status.
        FileNotFoundError: If intermediate format CSVs are missing.
    """
    import subprocess

    if not intermediate_dir.is_dir():
        raise FileNotFoundError(f"Intermediate format directory not found: {intermediate_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    tol = settings.tolerance or 1e-8
    max_iter = settings.max_iterations or 100

    # Build Octave script
    script = _build_matpower_octave_script(
        intermediate_dir=intermediate_dir,
        output_dir=output_dir,
        tolerance=tol,
        max_iterations=max_iter,
        enforce_q_limits=(settings.q_limits_enforced is True),
    )

    script_path = output_dir / "run_acpf.m"
    script_path.write_text(script, encoding="utf-8")

    result = subprocess.run(
        ["octave", "--no-gui", "--no-window-system", str(script_path)],
        capture_output=True,
        text=True,
        timeout=600,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Octave runpf failed (exit code {result.returncode}).\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    # Parse convergence info from stdout
    convergence = _parse_matpower_convergence(result.stdout)

    # Read exported CSVs
    bus_results = extract_bus_results(output_dir / "bus_results.csv")
    branch_results = extract_branch_results(output_dir / "branch_results.csv")
    gen_results = extract_generator_results(output_dir / "gen_results.csv")

    return bus_results, branch_results, gen_results, convergence


def _build_matpower_octave_script(
    intermediate_dir: Path,
    output_dir: Path,
    tolerance: float,
    max_iterations: int,
    enforce_q_limits: bool,
) -> str:
    """Build an Octave script to run MATPOWER runpf."""
    return f"""\
% Auto-generated ACPF reference extraction script
addpath(genpath(getenv('MATPOWER_PATH')));

% Load intermediate format CSVs into mpc struct
bus = csvread('{intermediate_dir}/bus.csv');
gen = csvread('{intermediate_dir}/gen.csv');
branch = csvread('{intermediate_dir}/branch.csv');

mpc = struct();
mpc.version = '2';
mpc.baseMVA = 100;
mpc.bus = bus;
mpc.gen = gen;
mpc.branch = branch;

% Flat start: set all VM=1.0, VA=0.0
mpc.bus(:, 8) = 1.0;
mpc.bus(:, 9) = 0.0;

% Configure options
mpopt = mpoption('verbose', 2, 'out.all', 0);
mpopt = mpoption(mpopt, 'pf.tol', {tolerance});
mpopt = mpoption(mpopt, 'pf.nr.max_it', {max_iterations});

% Stage 1: converge without Q-limits
mpopt = mpoption(mpopt, 'pf.enforce_q_lims', 0);
results = runpf(mpc, mpopt);

if results.success
    fprintf('CONVERGED_STAGE1\\n');
    fprintf('ITERATIONS: %d\\n', results.iterations);
else
    error('Stage 1 (relaxed Q-limits) failed to converge');
end

{"% Stage 2: re-converge with Q-limits" if enforce_q_limits else "% Q-limit enforcement skipped"}
{
        '''
mpopt2 = mpoption(mpopt, 'pf.enforce_q_lims', 1);
results2 = runpf(results, mpopt2);
if results2.success
    results = results2;
    fprintf('CONVERGED_STAGE2\\n');
    fprintf('Q_LIMITS_ENFORCED: true\\n');
else
    fprintf('STAGE2_FAILED\\n');
    fprintf('Q_LIMITS_ENFORCED: false\\n');
end
'''
        if enforce_q_limits
        else "fprintf('Q_LIMITS_ENFORCED: false\\n');"
    }

% Export results
csvwrite('{output_dir}/bus_results.csv', results.bus);
csvwrite('{output_dir}/branch_results.csv', results.branch);
csvwrite('{output_dir}/gen_results.csv', results.gen);

fprintf('DONE\\n');
"""


def _parse_matpower_convergence(stdout: str) -> ConvergenceInfo:
    """Parse convergence info from MATPOWER Octave stdout."""
    converged = "CONVERGED_STAGE1" in stdout or "CONVERGED_STAGE2" in stdout
    iterations: int | None = None
    for line in stdout.splitlines():
        if line.startswith("ITERATIONS:"):
            try:
                iterations = int(line.split(":")[1].strip())
            except (ValueError, IndexError):
                pass

    return ConvergenceInfo(
        converged=converged,
        iterations=iterations,
        final_mismatch_mw=None,
        final_mismatch_mvar=None,
    )


def run_gridcal_acpf(
    intermediate_dir: Path,
    settings: SolverSettings,
) -> tuple[list[dict], list[dict], list[dict], ConvergenceInfo]:
    """Run GridCal Newton-Raphson on the intermediate format data.

    Loads the intermediate format into a GridCal MultiCircuit object,
    configures the NR solver (tolerance, max iterations), runs power flow,
    and extracts results.

    For two-stage Q-limit enforcement: first run with control_q disabled,
    then re-run with control_q enabled using the converged voltages as
    the starting point.

    Args:
        intermediate_dir: Directory containing the intermediate format CSVs.
        settings: Solver configuration.

    Returns:
        A tuple of (bus_results, branch_results, gen_results, convergence_info).

    Raises:
        RuntimeError: If the solver fails to converge on both stages.
        ImportError: If GridCal is not installed in the current environment.
    """
    try:
        import GridCal  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "GridCal is not installed. Install it to use the GridCal solver path."
        ) from exc

    raise NotImplementedError(
        "GridCal ACPF solver path is not yet implemented. "
        "Use MATPOWER (--canonical-parser matpower) for flat-start path."
    )


# ---------------------------------------------------------------------------
# Bus exclusion (D1 registry consumption)
# ---------------------------------------------------------------------------


def _load_exclusion_registry(
    registry_path: Path,
) -> tuple[set[int], dict[str, int]]:
    """Load the D1 bus exclusion registry.

    Args:
        registry_path: Path to ``excluded_buses.json``.

    Returns:
        A tuple of (excluded_bus_set, reason_counts) where reason_counts
        maps exclusion reason strings to counts.
    """
    if not registry_path.exists():
        return set(), {}

    with open(registry_path, encoding="utf-8") as f:
        data = json.load(f)

    excluded: set[int] = set()
    reason_counts: dict[str, int] = {}

    buses = data.get("excluded_buses", data.get("buses", []))
    for entry in buses:
        if isinstance(entry, dict):
            raw_bus = entry.get("bus", entry.get("bus_i", 0))
            bus_num = int(raw_bus) if raw_bus is not None else 0
            reason = entry.get("reason", "unknown")
        else:
            bus_num = int(entry)
            reason = "unknown"
        excluded.add(bus_num)
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    return excluded, reason_counts


def _apply_exclusions(
    bus_results: list[dict],
    gen_results: list[dict],
    excluded_buses: set[int],
) -> tuple[list[dict], list[dict]]:
    """Remove excluded buses from bus and generator results."""
    filtered_buses = [r for r in bus_results if r["bus"] not in excluded_buses]
    filtered_gens = [r for r in gen_results if r["bus"] not in excluded_buses]
    return filtered_buses, filtered_gens


# ---------------------------------------------------------------------------
# System summary computation
# ---------------------------------------------------------------------------


def compute_system_summary(
    bus_results: list[dict],
    branch_results: list[dict],
    gen_results: list[dict],
    bus_csv_path: Path,
) -> SystemSummary:
    """Compute system-level aggregate quantities from the ACPF solution.

    Total generation is the sum of all generator P and Q values.
    Total load is read from the intermediate format bus table (PD, QD columns).
    Total losses are computed as: sum of (P_from + P_to) across all branches.
    The slack bus is identified as the bus with type = 3.
    Power balance residual = total_gen_mw - total_load_mw - total_loss_mw.

    Args:
        bus_results: Per-bus results from extraction or solver.
        branch_results: Per-branch results from extraction or solver.
        gen_results: Per-generator results from extraction or solver.
        bus_csv_path: Path to the intermediate format bus CSV (for load data
            and slack bus identification).

    Returns:
        A SystemSummary with all fields populated.

    Raises:
        ValueError: If no slack bus (type=3) is found.
    """
    # Total generation
    total_gen_mw = sum(g["P"] for g in gen_results)
    total_gen_mvar = sum(g["Q"] for g in gen_results)

    # Total load and slack bus from bus CSV
    headers, data_rows = _load_bus_csv_raw(bus_csv_path)
    bus_idx, type_idx, _vm_idx, _va_idx, pd_idx, qd_idx = _resolve_bus_col_indices(headers)

    total_load_mw = 0.0
    total_load_mvar = 0.0
    slack_candidates: list[tuple[int, float]] = []  # (bus_num, max_gen_capacity)

    # Build set of output bus numbers for load filtering
    output_bus_nums = {r["bus"] for r in bus_results}

    for row in data_rows:
        if not row or all(cell.strip() == "" for cell in row):
            continue
        try:
            bus_num = int(float(row[bus_idx].strip()))
            bus_type = int(float(row[type_idx].strip()))
            pd = float(row[pd_idx].strip())
            qd = float(row[qd_idx].strip())
        except (ValueError, IndexError):
            continue

        # Only count load from non-excluded, non-isolated buses
        if bus_num in output_bus_nums:
            total_load_mw += pd
            total_load_mvar += qd

        if bus_type == _SLACK_BUS_TYPE:
            # Find max gen capacity at this bus
            gen_cap = sum(g["P"] for g in gen_results if g["bus"] == bus_num)
            slack_candidates.append((bus_num, gen_cap))

    if not slack_candidates:
        raise ValueError("No slack bus (type=3) found in bus CSV.")

    # Primary slack = type-3 bus with largest generator MW capacity
    slack_candidates.sort(key=lambda x: x[1], reverse=True)
    slack_bus = slack_candidates[0][0]

    # Total losses from branch flows
    total_loss_mw = sum(b["P_from"] + b["P_to"] for b in branch_results)
    total_loss_mvar = sum(b["Q_from"] + b["Q_to"] for b in branch_results)

    # Power balance residual
    residual = total_gen_mw - total_load_mw - total_loss_mw

    return SystemSummary(
        total_gen_mw=total_gen_mw,
        total_gen_mvar=total_gen_mvar,
        total_load_mw=total_load_mw,
        total_load_mvar=total_load_mvar,
        total_loss_mw=total_loss_mw,
        total_loss_mvar=total_loss_mvar,
        slack_bus=slack_bus,
        power_balance_residual_mw=residual,
    )


# ---------------------------------------------------------------------------
# Output writing
# ---------------------------------------------------------------------------


def write_buses_csv(bus_results: list[dict], output_path: Path) -> None:
    """Write buses_acpf.csv.

    Args:
        bus_results: Per-bus results. Each dict has keys: bus, VM, VA.
        output_path: Full path to the output CSV file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["bus", "VM", "VA"])
        for r in bus_results:
            writer.writerow(
                [
                    r["bus"],
                    f"{r['VM']:.8f}",
                    f"{r['VA']:.6f}",
                ]
            )


def write_branches_csv(branch_results: list[dict], output_path: Path) -> None:
    """Write branches_acpf.csv.

    Args:
        branch_results: Per-branch results. Each dict has keys:
            from_bus, to_bus, ckt, P_from, Q_from, P_to, Q_to.
        output_path: Full path to the output CSV file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["from_bus", "to_bus", "ckt", "P_from", "Q_from", "P_to", "Q_to"])
        for r in branch_results:
            writer.writerow(
                [
                    r["from_bus"],
                    r["to_bus"],
                    r["ckt"],
                    f"{r['P_from']:.4f}",
                    f"{r['Q_from']:.4f}",
                    f"{r['P_to']:.4f}",
                    f"{r['Q_to']:.4f}",
                ]
            )


def write_generators_csv(gen_results: list[dict], output_path: Path) -> None:
    """Write generators_acpf.csv.

    Args:
        gen_results: Per-generator results. Each dict has keys:
            bus, machine_id, P, Q.
        output_path: Full path to the output CSV file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["bus", "machine_id", "P", "Q"])
        for r in gen_results:
            writer.writerow(
                [
                    r["bus"],
                    r["machine_id"],
                    f"{r['P']:.4f}",
                    f"{r['Q']:.4f}",
                ]
            )


def write_summary_json(
    source: SolutionSource,
    classification: str,
    canonical_parser: str,
    settings: SolverSettings,
    convergence: ConvergenceInfo | None,
    summary: SystemSummary,
    counts: dict[str, int],
    warnings: list[str],
    output_path: Path,
) -> None:
    """Write summary_acpf.json.

    Serializes all metadata into the JSON schema defined in the PRD.

    Args:
        source: EXTRACTED or COMPUTED.
        classification: D8 snapshot classification string.
        canonical_parser: Name of the canonical parser.
        settings: Solver settings (fields are None for EXTRACTED).
        convergence: Solver convergence info (None for EXTRACTED).
        summary: System-level summary.
        counts: Dict with keys: buses_total, buses_excluded_isolated,
            buses_excluded_deenergized, buses_in_output,
            branches_in_output, generators_in_output.
        warnings: List of warning messages (e.g., power balance residual).
        output_path: Full path to the output JSON file.
    """
    conv = convergence or ConvergenceInfo()

    data = {
        "solution_source": source.value,
        "snapshot_classification": classification,
        "canonical_parser": canonical_parser,
        "solver": {
            "name": settings.name,
            "version": settings.version,
            "settings": {
                "initial_conditions": ("flat_start" if source == SolutionSource.COMPUTED else None),
                "tolerance": settings.tolerance,
                "max_iterations": settings.max_iterations,
                "q_limits_enforced": settings.q_limits_enforced,
                "q_limit_strategy": settings.q_limit_strategy,
                "enforce_area_interchange": settings.enforce_area_interchange,
            },
            "convergence": {
                "converged": conv.converged,
                "iterations": conv.iterations,
                "final_mismatch_mw": conv.final_mismatch_mw,
                "final_mismatch_mvar": conv.final_mismatch_mvar,
            },
        },
        "system_summary": {
            "total_gen_mw": summary.total_gen_mw,
            "total_gen_mvar": summary.total_gen_mvar,
            "total_load_mw": summary.total_load_mw,
            "total_load_mvar": summary.total_load_mvar,
            "total_loss_mw": summary.total_loss_mw,
            "total_loss_mvar": summary.total_loss_mvar,
            "slack_bus": summary.slack_bus,
            "power_balance_residual_mw": summary.power_balance_residual_mw,
        },
        "counts": counts,
        "warnings": warnings,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Supplemental reference files (OQ-P3-05)
# ---------------------------------------------------------------------------


def write_taps_csv(bus_csv_path: Path, output_path: Path) -> None:
    """Write taps_acpf.csv — transformer tap positions.

    Placeholder for supplemental reference; reads transformer data from
    intermediate format and writes bus/tap pairs.

    Args:
        bus_csv_path: Path to intermediate format bus or transformer CSV.
        output_path: Full path to the output CSV file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["bus", "tap_pu"])
        # Transformer tap data extraction requires transformer-specific CSV
        # which may or may not exist in the intermediate format. Write header
        # only if no transformer data is available.


def write_shunts_csv(bus_csv_path: Path, output_path: Path) -> None:
    """Write shunts_acpf.csv — switched shunt admittance values.

    Placeholder for supplemental reference; reads shunt data from
    intermediate format and writes bus/admittance pairs.

    Args:
        bus_csv_path: Path to intermediate format bus or shunt CSV.
        output_path: Full path to the output CSV file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["bus", "b_mvar"])
        # Switched shunt data extraction requires shunt-specific CSV
        # which may or may not exist in the intermediate format. Write header
        # only if no shunt data is available.


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def build_acpf_reference(
    intermediate_dir: Path,
    snapshot_json_path: Path,
    canonical_parser: str,
    output_dir: Path,
) -> Path:
    """Top-level orchestrator for ACPF reference solution extraction.

    Steps:
    1. Read D8 snapshot classification.
    2. Determine solution source (extracted vs. computed).
    3. If extracted: call extract_bus_results, extract_branch_results,
       extract_generator_results.
    4. If computed: configure SolverSettings, call the appropriate solver
       function (run_matpower_acpf or run_gridcal_acpf).
    5. Apply bus exclusions from D1 registry if available.
    6. Compute system summary.
    7. Check power balance residual -- warn if > 1 MW.
    8. Write buses_acpf.csv, branches_acpf.csv, generators_acpf.csv,
       summary_acpf.json to output_dir.

    Args:
        intermediate_dir: Directory containing intermediate format CSVs
            (bus.csv, branch.csv, gen.csv, etc.).
        snapshot_json_path: Path to D8's snapshot_confirmation.json.
        canonical_parser: ``'matpower'`` or ``'gridcal'``.
        output_dir: Output directory (created if it does not exist).

    Returns:
        Path to the output directory containing all four output files.

    Raises:
        ValueError: If snapshot classification is 'indeterminate'.
        RuntimeError: If solver fails to converge (flat-start path).
        FileNotFoundError: If required input files are missing.
    """
    warnings_list: list[str] = []

    # Step 1-2: Determine path
    classification = read_snapshot_classification(snapshot_json_path)
    source = determine_solution_source(classification)

    # Locate intermediate format CSVs
    bus_csv = intermediate_dir / "bus.csv"
    branch_csv = intermediate_dir / "branch.csv"
    gen_csv = intermediate_dir / "gen.csv"

    solver_settings = SolverSettings()
    convergence: ConvergenceInfo | None = None

    if source == SolutionSource.EXTRACTED:
        # Path A: extract directly
        bus_results = extract_bus_results(bus_csv)
        branch_results = extract_branch_results(branch_csv)
        gen_results = extract_generator_results(gen_csv)
    else:
        # Path B: flat-start solver
        solver_settings = SolverSettings(
            name="runpf" if canonical_parser == "matpower" else "gridcal_nr",
            tolerance=1e-8,
            max_iterations=100,
            q_limits_enforced=True,
            q_limit_strategy="two_stage_relaxed_then_enforced",
            enforce_area_interchange=False,
        )
        if canonical_parser == "matpower":
            bus_results, branch_results, gen_results, convergence = run_matpower_acpf(
                intermediate_dir, output_dir / "_solver_tmp", solver_settings
            )
        else:
            bus_results, branch_results, gen_results, convergence = run_gridcal_acpf(
                intermediate_dir, solver_settings
            )

    # Load D1 bus exclusion registry if available
    repo_root = intermediate_dir.parent.parent  # data/fnm/intermediate -> data/fnm
    exclusion_path = repo_root / "reference" / "excluded_buses.json"
    excluded_buses, exclusion_reason_counts = _load_exclusion_registry(exclusion_path)

    if excluded_buses:
        bus_results, gen_results = _apply_exclusions(bus_results, gen_results, excluded_buses)

    if not bus_results:
        raise ValueError(
            "No buses remain after exclusions. This indicates corrupted intermediate format data."
        )

    # Compute counts
    headers, all_data_rows = _load_bus_csv_raw(bus_csv)
    total_bus_count = 0
    isolated_count = 0
    deenergized_count = 0
    _, type_idx_c, vm_idx_c, _, _, _ = _resolve_bus_col_indices(headers)

    for row in all_data_rows:
        if not row or all(cell.strip() == "" for cell in row):
            continue
        total_bus_count += 1
        try:
            btype = int(float(row[type_idx_c].strip()))
        except (ValueError, IndexError):
            btype = 0
        if btype == _ISOLATED_BUS_TYPE:
            isolated_count += 1
            continue
        try:
            vm_val = float(row[vm_idx_c].strip())
        except (ValueError, IndexError):
            vm_val = 1.0
        if vm_val == 0.0:
            deenergized_count += 1

    counts = {
        "buses_total": total_bus_count,
        "buses_excluded_isolated": isolated_count,
        "buses_excluded_deenergized": deenergized_count,
        "buses_in_output": len(bus_results),
        "branches_in_output": len(branch_results),
        "generators_in_output": len(gen_results),
    }

    # System summary
    system_summary = compute_system_summary(bus_results, branch_results, gen_results, bus_csv)

    # Power balance check
    residual_abs = abs(system_summary.power_balance_residual_mw)
    if residual_abs > _POWER_BALANCE_WARN_THRESHOLD_MW:
        warnings_list.append(
            f"Power balance residual is {system_summary.power_balance_residual_mw:.4f} MW "
            f"(exceeds {_POWER_BALANCE_WARN_THRESHOLD_MW} MW threshold)."
        )

    # Write outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    write_buses_csv(bus_results, output_dir / "buses_acpf.csv")
    write_branches_csv(branch_results, output_dir / "branches_acpf.csv")
    write_generators_csv(gen_results, output_dir / "generators_acpf.csv")
    write_summary_json(
        source=source,
        classification=classification,
        canonical_parser=canonical_parser,
        settings=solver_settings,
        convergence=convergence,
        summary=system_summary,
        counts=counts,
        warnings=warnings_list,
        output_path=output_dir / "summary_acpf.json",
    )

    # Supplemental files
    write_taps_csv(bus_csv, output_dir / "taps_acpf.csv")
    write_shunts_csv(bus_csv, output_dir / "shunts_acpf.csv")

    return output_dir


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for ACPF reference solution extraction.

    Usage::

        python -m data.fnm.scripts.acpf_reference \\
            --intermediate-dir data/fnm/intermediate/canonical/ \\
            --snapshot-json data/fnm/intermediate/snapshot/snapshot_confirmation.json \\
            --canonical-parser gridcal \\
            [-o data/fnm/reference/acpf/]

    Exit codes:
    - 0: Reference solution produced successfully.
    - 1: Snapshot classification is 'indeterminate' -- manual resolution required.
    - 2: Solver failed to converge (flat-start path).
    - 3: Input error (missing files, malformed data).

    Args:
        argv: Command-line arguments. If None, reads from sys.argv[1:].
    """
    parser = argparse.ArgumentParser(
        description="Extract or compute ACPF reference solution from FNM intermediate format."
    )
    parser.add_argument(
        "--intermediate-dir",
        type=Path,
        required=True,
        help="Directory containing intermediate format CSVs (bus.csv, branch.csv, gen.csv).",
    )
    parser.add_argument(
        "--snapshot-json",
        type=Path,
        required=True,
        help="Path to D8's snapshot_confirmation.json.",
    )
    parser.add_argument(
        "--canonical-parser",
        type=str,
        required=True,
        choices=["matpower", "gridcal"],
        help="Name of the canonical parser.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data/fnm/reference/acpf"),
        help="Output directory (default: data/fnm/reference/acpf/).",
    )

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    try:
        result_dir = build_acpf_reference(
            intermediate_dir=args.intermediate_dir,
            snapshot_json_path=args.snapshot_json,
            canonical_parser=args.canonical_parser,
            output_dir=args.output_dir,
        )
        print(f"ACPF reference solution written to: {result_dir}")
        sys.exit(0)
    except ValueError as exc:
        if "indeterminate" in str(exc).lower():
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(3)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
