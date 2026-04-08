"""Reference Solution Validation Report for FNM Annual S01.

Performs internal consistency checks on the ACPF and DCPF reference solutions
produced by Phase 3 D2 and D3, generating a structured validation report that
documents whether the reference data is self-consistent.  This is a self-check,
not a gate -- findings are documented in full but do not block downstream
consumption of the reference solutions.

Output directory: ``data/fnm/reference/``

Output files:
- ``validation_report.json`` -- machine-readable structured report
- ``validation_report.md``   -- human-readable summary
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ZERO_IMPEDANCE_REPLACEMENT: float = 0.0001
"""Reactance (p.u.) assigned to zero-impedance branches in D3."""

_REPORT_VERSION: str = "1.0"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class CheckStatus(Enum):
    """Outcome of a single validation check."""

    PASS = "pass"
    """All elements within tolerance."""

    FAIL = "fail"
    """One or more elements exceeded tolerance."""

    SKIP = "skip"
    """Check could not be performed (missing input data)."""


@dataclass(frozen=True)
class CheckResult:
    """Result of a single validation check."""

    check_id: str
    """Unique identifier: 'acpf_power_balance', 'acpf_kcl', etc."""

    check_name: str
    """Human-readable name: 'ACPF System Power Balance', etc."""

    status: CheckStatus
    """Pass, fail, or skip."""

    metric_value: float | None
    """Primary numeric metric (e.g., max residual, max mismatch).
    None if status is SKIP."""

    metric_unit: str
    """Unit of the metric: 'MW', 'MVA', 'pu', 'degrees'."""

    tolerance: float
    """The tolerance threshold applied."""

    tolerance_unit: str
    """Unit of the tolerance (same as metric_unit in most cases)."""

    total_elements: int
    """Number of elements checked (buses, branches, generators)."""

    passing_elements: int
    """Number of elements within tolerance."""

    failing_elements: int
    """Number of elements exceeding tolerance."""

    detail: list[dict] | None = None
    """Per-element detail for failing elements."""

    notes: list[str] = field(default_factory=list)
    """Informational notes."""

    skip_reason: str | None = None
    """Reason the check was skipped, if status is SKIP."""


@dataclass(frozen=True)
class ReportSummary:
    """Aggregate statistics for the validation report."""

    total_checks: int
    """Total number of checks performed (7)."""

    passed: int
    """Number of checks with status PASS."""

    failed: int
    """Number of checks with status FAIL."""

    skipped: int
    """Number of checks with status SKIP."""

    acpf_bus_count: int
    """Number of buses in the ACPF reference."""

    acpf_branch_count: int
    """Number of branches in the ACPF reference."""

    acpf_generator_count: int
    """Number of generators in the ACPF reference."""

    dcpf_bus_count: int
    """Number of buses in the DCPF reference."""

    dcpf_branch_count: int
    """Number of branches in the DCPF reference."""


@dataclass(frozen=True)
class ValidationReport:
    """Complete validation report for ACPF and DCPF reference solutions."""

    acpf_checks: list[CheckResult]
    """Results for ACPF checks A through D."""

    dcpf_checks: list[CheckResult]
    """Results for DCPF checks A through C."""

    all_passed: bool
    """True if every check has status PASS (no FAIL or SKIP)."""

    summary: ReportSummary
    """Aggregate statistics across all checks."""

    timestamp: str
    """ISO 8601 timestamp of report generation."""


# ---------------------------------------------------------------------------
# CSV / JSON helpers
# ---------------------------------------------------------------------------


def _read_csv_dicts(csv_path: Path) -> list[dict[str, str]]:
    """Read a CSV file with headers and return a list of dicts (raw strings)."""
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _read_json(json_path: Path) -> dict:
    """Read a JSON file and return the parsed dict."""
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def _detect_column(headers: list[str], candidates: list[str]) -> str | None:
    """Find the first matching header (case-insensitive) from candidates."""
    lower_map = {h.strip().lower(): h for h in headers}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_acpf_buses(acpf_dir: Path) -> list[dict]:
    """Load buses_acpf.csv from the ACPF reference directory.

    Returns:
        List of dicts with keys: bus (int), VM (float), VA (float).

    Raises:
        FileNotFoundError: If buses_acpf.csv does not exist.
    """
    raw = _read_csv_dicts(acpf_dir / "buses_acpf.csv")
    return [
        {
            "bus": int(float(r["bus"])),
            "VM": float(r["VM"]),
            "VA": float(r["VA"]),
        }
        for r in raw
    ]


def load_acpf_branches(acpf_dir: Path) -> list[dict]:
    """Load branches_acpf.csv from the ACPF reference directory.

    Returns:
        List of dicts with keys: from_bus (int), to_bus (int), ckt (str),
        P_from (float), Q_from (float), P_to (float), Q_to (float).

    Raises:
        FileNotFoundError: If branches_acpf.csv does not exist.
    """
    raw = _read_csv_dicts(acpf_dir / "branches_acpf.csv")
    return [
        {
            "from_bus": int(float(r["from_bus"])),
            "to_bus": int(float(r["to_bus"])),
            "ckt": r["ckt"].strip(),
            "P_from": float(r["P_from"]),
            "Q_from": float(r["Q_from"]),
            "P_to": float(r["P_to"]),
            "Q_to": float(r["Q_to"]),
        }
        for r in raw
    ]


def load_acpf_generators(acpf_dir: Path) -> list[dict]:
    """Load generators_acpf.csv from the ACPF reference directory.

    Returns:
        List of dicts with keys: bus (int), machine_id (str),
        P (float), Q (float).

    Raises:
        FileNotFoundError: If generators_acpf.csv does not exist.
    """
    raw = _read_csv_dicts(acpf_dir / "generators_acpf.csv")
    return [
        {
            "bus": int(float(r["bus"])),
            "machine_id": r["machine_id"].strip(),
            "P": float(r["P"]),
            "Q": float(r["Q"]),
        }
        for r in raw
    ]


def load_acpf_summary(acpf_dir: Path) -> dict:
    """Load summary_acpf.json from the ACPF reference directory.

    Returns:
        Parsed JSON as a dict.

    Raises:
        FileNotFoundError: If summary_acpf.json does not exist.
    """
    return _read_json(acpf_dir / "summary_acpf.json")


def load_dcpf_buses(dcpf_dir: Path) -> list[dict]:
    """Load buses_dcpf.csv from the DCPF reference directory.

    Returns:
        List of dicts with keys: bus (int), VA (float).

    Raises:
        FileNotFoundError: If buses_dcpf.csv does not exist.
    """
    raw = _read_csv_dicts(dcpf_dir / "buses_dcpf.csv")
    return [
        {
            "bus": int(float(r["bus"])),
            "VA": float(r["VA"]),
        }
        for r in raw
    ]


def load_dcpf_branches(dcpf_dir: Path) -> list[dict]:
    """Load branches_dcpf.csv from the DCPF reference directory.

    Returns:
        List of dicts with keys: from_bus (int), to_bus (int),
        ckt (str), P_flow_MW (float).

    Raises:
        FileNotFoundError: If branches_dcpf.csv does not exist.
    """
    raw = _read_csv_dicts(dcpf_dir / "branches_dcpf.csv")
    return [
        {
            "from_bus": int(float(r["from_bus"])),
            "to_bus": int(float(r["to_bus"])),
            "ckt": r["ckt"].strip(),
            "P_flow_MW": float(r["P_flow_MW"]),
        }
        for r in raw
    ]


def load_dcpf_summary(dcpf_dir: Path) -> dict:
    """Load summary_dcpf.json from the DCPF reference directory.

    Returns:
        Parsed JSON as a dict.

    Raises:
        FileNotFoundError: If summary_dcpf.json does not exist.
    """
    return _read_json(dcpf_dir / "summary_dcpf.json")


def load_intermediate_generators(intermediate_dir: Path) -> list[dict]:
    """Load the generator table from the canonical parser's intermediate format.

    Extracts generator limits (PT, PB, QT, QB) for the generator-limit check.
    Auto-detects column names from MATPOWER and PSS/E conventions.

    Returns:
        List of dicts with keys: bus (int), machine_id (str), status (int),
        PG (float), QG (float), PT (float), PB (float), QT (float), QB (float).

    Raises:
        FileNotFoundError: If the generator CSV does not exist.
        ValueError: If limit columns (PT, PB, QT, QB) cannot be identified.
    """
    # Try multiple possible filenames
    gen_path: Path | None = None
    for name in ("generator.csv", "gen.csv", "Generator.csv"):
        candidate = intermediate_dir / name
        if candidate.exists():
            gen_path = candidate
            break
    if gen_path is None:
        raise FileNotFoundError(
            f"Generator CSV not found in {intermediate_dir}. "
            f"Tried: generator.csv, gen.csv, Generator.csv"
        )

    raw = _read_csv_dicts(gen_path)
    if not raw:
        raise ValueError(f"Generator CSV is empty: {gen_path}")

    headers = list(raw[0].keys())

    # Detect columns
    bus_col = _detect_column(headers, ["gen_bus", "bus", "bus_number", "i"])
    status_col = _detect_column(headers, ["stat", "gen_status", "status"])
    id_col = _detect_column(headers, ["id", "machine_id", "mach_id"])
    pg_col = _detect_column(headers, ["pg"])
    qg_col = _detect_column(headers, ["qg"])
    pt_col = _detect_column(headers, ["pt", "pmax"])
    pb_col = _detect_column(headers, ["pb", "pmin"])
    qt_col = _detect_column(headers, ["qt", "qmax"])
    qb_col = _detect_column(headers, ["qb", "qmin"])

    if bus_col is None:
        raise ValueError(f"Cannot find bus column in generator CSV headers: {headers}")

    missing_limits = []
    for name, col in [("PT", pt_col), ("PB", pb_col), ("QT", qt_col), ("QB", qb_col)]:
        if col is None:
            missing_limits.append(name)
    if missing_limits:
        raise ValueError(
            f"Generator limit columns not found: {missing_limits}. Available headers: {headers}"
        )

    result: list[dict] = []
    for r in raw:
        result.append(
            {
                "bus": int(float(r[bus_col])),
                "machine_id": r[id_col].strip() if id_col else "1",
                "status": int(float(r[status_col])) if status_col else 1,
                "PG": float(r[pg_col]) if pg_col else 0.0,
                "QG": float(r[qg_col]) if qg_col else 0.0,
                "PT": float(r[pt_col]),  # type: ignore[arg-type]
                "PB": float(r[pb_col]),  # type: ignore[arg-type]
                "QT": float(r[qt_col]),  # type: ignore[arg-type]
                "QB": float(r[qb_col]),  # type: ignore[arg-type]
            }
        )
    return result


def load_intermediate_branches(intermediate_dir: Path) -> list[dict]:
    """Load the branch table from the canonical parser's intermediate format.

    Extracts reactance (X), tap ratio, phase shift angle, and status for the
    DCPF flow-angle consistency check.

    Returns:
        List of dicts with keys: from_bus (int), to_bus (int), ckt (str),
        x_pu (float), tap_ratio (float), shift_deg (float), status (int).

    Raises:
        FileNotFoundError: If the branch CSV does not exist.
        ValueError: If required columns cannot be identified.
    """
    branch_path: Path | None = None
    for name in ("branch.csv", "Branch.csv"):
        candidate = intermediate_dir / name
        if candidate.exists():
            branch_path = candidate
            break
    if branch_path is None:
        raise FileNotFoundError(
            f"Branch CSV not found in {intermediate_dir}. Tried: branch.csv, Branch.csv"
        )

    raw = _read_csv_dicts(branch_path)
    if not raw:
        raise ValueError(f"Branch CSV is empty: {branch_path}")

    headers = list(raw[0].keys())

    f_bus_col = _detect_column(headers, ["f_bus", "from_bus", "i", "fbus"])
    t_bus_col = _detect_column(headers, ["t_bus", "to_bus", "j", "tbus"])
    x_col = _detect_column(headers, ["br_x", "x"])
    tap_col = _detect_column(headers, ["tap", "windv1"])
    shift_col = _detect_column(headers, ["shift", "ang1"])
    status_col = _detect_column(headers, ["br_status", "status", "st"])
    ckt_col = _detect_column(headers, ["ckt", "circuit"])

    for label, col in [("from_bus", f_bus_col), ("to_bus", t_bus_col), ("x", x_col)]:
        if col is None:
            raise ValueError(f"Required branch column '{label}' not found. Available: {headers}")

    result: list[dict] = []
    for r in raw:
        tap_raw = float(r[tap_col]) if tap_col else 1.0
        # MATPOWER convention: tap=0 means nominal (1.0)
        tap = tap_raw if tap_raw != 0.0 else 1.0

        result.append(
            {
                "from_bus": int(float(r[f_bus_col])),  # type: ignore[arg-type]
                "to_bus": int(float(r[t_bus_col])),  # type: ignore[arg-type]
                "ckt": r[ckt_col].strip() if ckt_col else "1",
                "x_pu": float(r[x_col]),  # type: ignore[arg-type]
                "tap_ratio": tap,
                "shift_deg": float(r[shift_col]) if shift_col else 0.0,
                "status": int(float(r[status_col])) if status_col else 1,
            }
        )
    return result


def load_intermediate_buses(intermediate_dir: Path) -> list[dict]:
    """Load the bus table from the canonical parser's intermediate format.

    Extracts bus load (PD, QD) and bus type for the KCL check.

    Returns:
        List of dicts with keys: bus (int), bus_type (int),
        PD (float), QD (float).

    Raises:
        FileNotFoundError: If the bus CSV does not exist.
    """
    bus_path: Path | None = None
    for name in ("bus.csv", "Bus.csv"):
        candidate = intermediate_dir / name
        if candidate.exists():
            bus_path = candidate
            break
    if bus_path is None:
        raise FileNotFoundError(f"Bus CSV not found in {intermediate_dir}. Tried: bus.csv, Bus.csv")

    raw = _read_csv_dicts(bus_path)
    if not raw:
        raise ValueError(f"Bus CSV is empty: {bus_path}")

    headers = list(raw[0].keys())

    bus_col = _detect_column(headers, ["bus_i", "bus", "bus_number", "number", "i"])
    type_col = _detect_column(headers, ["bus_type", "type", "ide"])
    pd_col = _detect_column(headers, ["pd", "pl"])
    qd_col = _detect_column(headers, ["qd", "ql"])

    if bus_col is None:
        raise ValueError(f"Cannot find bus number column in headers: {headers}")

    result: list[dict] = []
    for r in raw:
        result.append(
            {
                "bus": int(float(r[bus_col])),
                "bus_type": int(float(r[type_col])) if type_col else 1,
                "PD": float(r[pd_col]) if pd_col else 0.0,
                "QD": float(r[qd_col]) if qd_col else 0.0,
            }
        )
    return result


def load_excluded_buses(reference_dir: Path) -> set[int]:
    """Load excluded bus numbers from the D1 bus exclusion registry.

    Reads ``excluded_buses.csv`` and returns the set of bus numbers to skip
    in per-bus checks.

    Returns:
        Set of excluded bus numbers.

    Raises:
        FileNotFoundError: If the exclusion CSV does not exist.
    """
    csv_path = reference_dir / "excluded_buses.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Exclusion registry not found: {csv_path}")

    raw = _read_csv_dicts(csv_path)
    return {int(float(r["bus_number"])) for r in raw}


# ---------------------------------------------------------------------------
# ACPF checks
# ---------------------------------------------------------------------------


def check_acpf_power_balance(summary: dict) -> CheckResult:
    """ACPF Check A: System power balance.

    Computes |total_gen_mw - total_load_mw - total_loss_mw| and checks
    that the residual is within 1 MW.

    Args:
        summary: Parsed summary_acpf.json.

    Returns:
        CheckResult with check_id='acpf_power_balance'.
    """
    sys_summary = summary.get("system_summary", summary)
    total_gen = sys_summary["total_gen_mw"]
    total_load = sys_summary["total_load_mw"]
    total_loss = sys_summary["total_loss_mw"]

    residual = abs(total_gen - total_load - total_loss)
    tolerance = 1.0
    passed = residual < tolerance

    return CheckResult(
        check_id="acpf_power_balance",
        check_name="ACPF System Power Balance",
        status=CheckStatus.PASS if passed else CheckStatus.FAIL,
        metric_value=residual,
        metric_unit="MW",
        tolerance=tolerance,
        tolerance_unit="MW",
        total_elements=1,
        passing_elements=1 if passed else 0,
        failing_elements=0 if passed else 1,
    )


def check_acpf_kcl(
    acpf_buses: list[dict],
    acpf_branches: list[dict],
    acpf_generators: list[dict],
    intermediate_buses: list[dict],
    excluded_buses: set[int],
) -> CheckResult:
    """ACPF Check B: Per-bus Kirchhoff's Current Law.

    For each non-excluded bus, computes:
    - dP = sum(generator P at bus) - PD - sum(branch P flows leaving bus)
    - dQ = sum(generator Q at bus) - QD - sum(branch Q flows leaving bus)
    - mismatch = sqrt(dP^2 + dQ^2) in MVA

    Args:
        acpf_buses: Loaded buses_acpf.csv records.
        acpf_branches: Loaded branches_acpf.csv records.
        acpf_generators: Loaded generators_acpf.csv records.
        intermediate_buses: Intermediate format bus table (for PD, QD).
        excluded_buses: Set of bus numbers to skip.

    Returns:
        CheckResult with check_id='acpf_kcl'.
    """
    tolerance = 0.1  # MVA

    # Build load lookup from intermediate buses
    load_p: dict[int, float] = {}
    load_q: dict[int, float] = {}
    for b in intermediate_buses:
        bus_num = b["bus"]
        load_p[bus_num] = b["PD"]
        load_q[bus_num] = b["QD"]

    # Collect all bus numbers from ACPF output
    all_bus_nums = {b["bus"] for b in acpf_buses}

    # Active (non-excluded) buses
    active_buses = all_bus_nums - excluded_buses

    # Aggregate generator injections per bus
    gen_p: dict[int, float] = {}
    gen_q: dict[int, float] = {}
    for g in acpf_generators:
        bus = g["bus"]
        gen_p[bus] = gen_p.get(bus, 0.0) + g["P"]
        gen_q[bus] = gen_q.get(bus, 0.0) + g["Q"]

    # Aggregate branch flows leaving each bus
    # P_from is power injected into the branch from the from-bus side (leaving from-bus)
    # P_to is power injected into the branch from the to-bus side (leaving to-bus)
    branch_p: dict[int, float] = {}
    branch_q: dict[int, float] = {}
    for br in acpf_branches:
        fb = br["from_bus"]
        tb = br["to_bus"]
        branch_p[fb] = branch_p.get(fb, 0.0) + br["P_from"]
        branch_q[fb] = branch_q.get(fb, 0.0) + br["Q_from"]
        branch_p[tb] = branch_p.get(tb, 0.0) + br["P_to"]
        branch_q[tb] = branch_q.get(tb, 0.0) + br["Q_to"]

    # Compute per-bus mismatch
    detail: list[dict] = []
    max_mismatch = 0.0
    failing_count = 0

    for bus_num in sorted(active_buses):
        dp = gen_p.get(bus_num, 0.0) - load_p.get(bus_num, 0.0) - branch_p.get(bus_num, 0.0)
        dq = gen_q.get(bus_num, 0.0) - load_q.get(bus_num, 0.0) - branch_q.get(bus_num, 0.0)
        mismatch = math.sqrt(dp * dp + dq * dq)

        if mismatch > max_mismatch:
            max_mismatch = mismatch

        if mismatch > tolerance:
            failing_count += 1
            detail.append(
                {
                    "bus": bus_num,
                    "dP_mw": round(dp, 6),
                    "dQ_mvar": round(dq, 6),
                    "mismatch_mva": round(mismatch, 6),
                }
            )

    total = len(active_buses)
    passed = failing_count == 0

    notes: list[str] = []
    if not excluded_buses:
        notes.append("No bus exclusion registry available; all buses checked.")

    return CheckResult(
        check_id="acpf_kcl",
        check_name="ACPF Per-Bus KCL",
        status=CheckStatus.PASS if passed else CheckStatus.FAIL,
        metric_value=round(max_mismatch, 6),
        metric_unit="MVA",
        tolerance=tolerance,
        tolerance_unit="MVA",
        total_elements=total,
        passing_elements=total - failing_count,
        failing_elements=failing_count,
        detail=detail if detail else None,
        notes=notes,
    )


def check_acpf_vm_plausibility(
    acpf_buses: list[dict],
    excluded_buses: set[int],
) -> CheckResult:
    """ACPF Check C: Voltage magnitude plausibility.

    For each non-excluded bus, checks 0.8 < VM < 1.2 (per-unit).

    Args:
        acpf_buses: Loaded buses_acpf.csv records.
        excluded_buses: Set of bus numbers to skip.

    Returns:
        CheckResult with check_id='acpf_vm_plausibility'.
    """
    vm_low = 0.8
    vm_high = 1.2

    detail: list[dict] = []
    total = 0
    failing_count = 0

    for b in acpf_buses:
        bus_num = b["bus"]
        if bus_num in excluded_buses:
            continue
        total += 1
        vm = b["VM"]
        if vm <= vm_low or vm >= vm_high:
            failing_count += 1
            detail.append({"bus": bus_num, "VM": vm})

    passed = failing_count == 0

    return CheckResult(
        check_id="acpf_vm_plausibility",
        check_name="ACPF Voltage Magnitude Plausibility",
        status=CheckStatus.PASS if passed else CheckStatus.FAIL,
        metric_value=float(failing_count),
        metric_unit="buses",
        tolerance=0.0,
        tolerance_unit="(range: 0.8 < VM < 1.2 pu)",
        total_elements=total,
        passing_elements=total - failing_count,
        failing_elements=failing_count,
        detail=detail if detail else None,
    )


def check_acpf_generator_limits(
    acpf_generators: list[dict],
    intermediate_generators: list[dict],
    acpf_summary: dict,
) -> CheckResult:
    """ACPF Check D: Generator output within limits.

    For each in-service generator, checks:
    - PB - 0.1 <= P <= PT + 0.1 (MW tolerance)
    - QB - 0.1 <= Q <= QT + 0.1 (MVAr tolerance)

    The slack bus generator is exempt from the P-limit check.

    Args:
        acpf_generators: Loaded generators_acpf.csv records.
        intermediate_generators: Intermediate format generator table (for limits).
        acpf_summary: Parsed summary_acpf.json (for slack bus identification).

    Returns:
        CheckResult with check_id='acpf_generator_limits'.
    """
    tol = 0.1  # MW / MVAr

    # Identify slack bus
    sys_summary = acpf_summary.get("system_summary", acpf_summary)
    slack_bus = sys_summary.get("slack_bus")

    # Build lookup for intermediate generator limits by (bus, machine_id)
    limits_map: dict[tuple[int, str], dict] = {}
    for g in intermediate_generators:
        key = (g["bus"], str(g["machine_id"]))
        limits_map[key] = g

    detail: list[dict] = []
    total = 0
    failing_count = 0
    notes: list[str] = []

    if slack_bus is not None:
        notes.append(f"Slack bus generator (bus {slack_bus}) exempt from P-limit check.")

    for gen in acpf_generators:
        bus = gen["bus"]
        mid = str(gen["machine_id"])
        key = (bus, mid)

        lim = limits_map.get(key)
        if lim is None:
            continue  # No limit data available for this generator

        # Only check in-service generators
        if lim.get("status", 1) == 0:
            continue

        total += 1
        p_val = gen["P"]
        q_val = gen["Q"]
        pt = lim["PT"]
        pb = lim["PB"]
        qt = lim["QT"]
        qb = lim["QB"]

        violations: list[str] = []

        # P-limit check (exempt for slack bus generator)
        is_slack = slack_bus is not None and bus == slack_bus
        if not is_slack:
            if p_val > pt + tol:
                violations.append("P_above_PT")
            if p_val < pb - tol:
                violations.append("P_below_PB")

        # Q-limit check (always applied)
        if q_val > qt + tol:
            violations.append("Q_above_QT")
        if q_val < qb - tol:
            violations.append("Q_below_QB")

        if violations:
            failing_count += 1
            detail.append(
                {
                    "bus": bus,
                    "machine_id": mid,
                    "P": p_val,
                    "Q": q_val,
                    "PT": pt,
                    "PB": pb,
                    "QT": qt,
                    "QB": qb,
                    "violation_type": violations,
                }
            )

    passed = failing_count == 0

    return CheckResult(
        check_id="acpf_generator_limits",
        check_name="ACPF Generator Output Within Limits",
        status=CheckStatus.PASS if passed else CheckStatus.FAIL,
        metric_value=float(failing_count),
        metric_unit="generators",
        tolerance=tol,
        tolerance_unit="MW/MVAr",
        total_elements=total,
        passing_elements=total - failing_count,
        failing_elements=failing_count,
        detail=detail if detail else None,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# DCPF checks
# ---------------------------------------------------------------------------


def check_dcpf_power_balance(summary: dict) -> CheckResult:
    """DCPF Check A: Power balance (lossless).

    Computes |total_gen_mw - total_load_mw - slack_injection_mw| and checks
    that the residual is within 0.1 MW.

    Args:
        summary: Parsed summary_dcpf.json.

    Returns:
        CheckResult with check_id='dcpf_power_balance'.
    """
    power_summary = summary.get("power_summary", summary)
    total_gen = power_summary["total_generation_mw"]
    total_load = power_summary["total_load_mw"]
    slack_inj = power_summary["slack_injection_mw"]

    residual = abs(total_gen - total_load - slack_inj)
    tolerance = 0.1
    passed = residual < tolerance

    return CheckResult(
        check_id="dcpf_power_balance",
        check_name="DCPF Power Balance (Lossless)",
        status=CheckStatus.PASS if passed else CheckStatus.FAIL,
        metric_value=residual,
        metric_unit="MW",
        tolerance=tolerance,
        tolerance_unit="MW",
        total_elements=1,
        passing_elements=1 if passed else 0,
        failing_elements=0 if passed else 1,
    )


def check_dcpf_flow_angle_consistency(
    dcpf_buses: list[dict],
    dcpf_branches: list[dict],
    intermediate_branches: list[dict],
    dcpf_summary: dict,
) -> CheckResult:
    """DCPF Check B: Flow-angle consistency.

    For each in-service branch, recomputes expected flow from bus angles
    and branch reactance, comparing to the stored flow.

    Args:
        dcpf_buses: Loaded buses_dcpf.csv records.
        dcpf_branches: Loaded branches_dcpf.csv records.
        intermediate_branches: Intermediate format branch table.
        dcpf_summary: Parsed summary_dcpf.json (for baseMVA).

    Returns:
        CheckResult with check_id='dcpf_flow_angle_consistency'.
    """
    tolerance = 0.1  # MW

    # Get baseMVA
    base_mva = dcpf_summary.get("base_mva", 100.0)

    # Build angle lookup from DCPF buses
    angle_map: dict[int, float] = {b["bus"]: b["VA"] for b in dcpf_buses}

    # Build intermediate branch lookup by (from_bus, to_bus, ckt)
    int_branch_map: dict[tuple[int, int, str], dict] = {}
    for br in intermediate_branches:
        key = (br["from_bus"], br["to_bus"], br["ckt"])
        int_branch_map[key] = br

    detail: list[dict] = []
    max_deviation = 0.0
    total = 0
    failing_count = 0
    zero_impedance_count = 0
    notes: list[str] = []

    for br in dcpf_branches:
        fb = br["from_bus"]
        tb = br["to_bus"]
        ckt = br["ckt"]
        p_stored = br["P_flow_MW"]

        key = (fb, tb, ckt)
        int_br = int_branch_map.get(key)
        if int_br is None:
            continue

        # Skip out-of-service branches
        if int_br.get("status", 1) == 0:
            continue

        # Get angles
        va_from = angle_map.get(fb)
        va_to = angle_map.get(tb)
        if va_from is None or va_to is None:
            continue

        total += 1

        # Get reactance (apply zero-impedance replacement)
        x_pu = int_br["x_pu"]
        if x_pu == 0.0 or abs(x_pu) < 1e-12:
            x_pu = ZERO_IMPEDANCE_REPLACEMENT
            zero_impedance_count += 1

        # Convert angles from degrees to radians
        va_from_rad = va_from * math.pi / 180.0
        va_to_rad = va_to * math.pi / 180.0

        # Compute expected flow based on branch type
        tap = int_br.get("tap_ratio", 1.0)
        shift_deg = int_br.get("shift_deg", 0.0)
        shift_rad = shift_deg * math.pi / 180.0

        if abs(shift_deg) > 1e-10:
            # Phase shifter
            p_expected = (va_from_rad - va_to_rad - shift_rad) / x_pu * base_mva
        elif abs(tap - 1.0) > 1e-10:
            # Transformer with off-nominal tap
            p_expected = (va_from_rad - va_to_rad) / (x_pu * tap) * base_mva
        else:
            # Simple branch
            p_expected = (va_from_rad - va_to_rad) / x_pu * base_mva

        deviation = abs(p_stored - p_expected)
        if deviation > max_deviation:
            max_deviation = deviation

        if deviation > tolerance:
            failing_count += 1
            detail.append(
                {
                    "from_bus": fb,
                    "to_bus": tb,
                    "ckt": ckt,
                    "P_stored_mw": round(p_stored, 6),
                    "P_recomputed_mw": round(p_expected, 6),
                    "deviation_mw": round(deviation, 6),
                    "x_pu": x_pu,
                }
            )

    if zero_impedance_count > 0:
        notes.append(
            f"{zero_impedance_count} zero-impedance branch(es) used replacement "
            f"reactance X={ZERO_IMPEDANCE_REPLACEMENT} p.u."
        )

    passed = failing_count == 0

    return CheckResult(
        check_id="dcpf_flow_angle_consistency",
        check_name="DCPF Flow-Angle Consistency",
        status=CheckStatus.PASS if passed else CheckStatus.FAIL,
        metric_value=round(max_deviation, 6),
        metric_unit="MW",
        tolerance=tolerance,
        tolerance_unit="MW",
        total_elements=total,
        passing_elements=total - failing_count,
        failing_elements=failing_count,
        detail=detail if detail else None,
        notes=notes,
    )


def check_dcpf_slack_angle(
    dcpf_buses: list[dict],
    dcpf_summary: dict,
) -> CheckResult:
    """DCPF Check C: Slack bus angle is zero.

    Verifies that the slack bus angle in buses_dcpf.csv is exactly 0.0 degrees.

    Args:
        dcpf_buses: Loaded buses_dcpf.csv records.
        dcpf_summary: Parsed summary_dcpf.json (for slack bus number).

    Returns:
        CheckResult with check_id='dcpf_slack_angle'.
    """
    settings = dcpf_summary.get("settings", {})
    slack_bus = settings.get("slack_bus", dcpf_summary.get("slack_bus"))

    # Fallback: look in power_summary
    if slack_bus is None:
        power_summary = dcpf_summary.get("power_summary", {})
        slack_bus = power_summary.get("slack_bus")

    if slack_bus is None:
        return CheckResult(
            check_id="dcpf_slack_angle",
            check_name="DCPF Slack Angle Reference",
            status=CheckStatus.FAIL,
            metric_value=None,
            metric_unit="degrees",
            tolerance=0.0,
            tolerance_unit="degrees",
            total_elements=1,
            passing_elements=0,
            failing_elements=1,
            notes=["Slack bus number not found in summary_dcpf.json."],
        )

    slack_bus = int(slack_bus)

    # Find the slack bus in the DCPF bus data
    slack_angle: float | None = None
    for b in dcpf_buses:
        if b["bus"] == slack_bus:
            slack_angle = b["VA"]
            break

    if slack_angle is None:
        return CheckResult(
            check_id="dcpf_slack_angle",
            check_name="DCPF Slack Angle Reference",
            status=CheckStatus.FAIL,
            metric_value=None,
            metric_unit="degrees",
            tolerance=0.0,
            tolerance_unit="degrees",
            total_elements=1,
            passing_elements=0,
            failing_elements=1,
            notes=[f"Slack bus {slack_bus} from summary_dcpf.json not found in buses_dcpf.csv."],
        )

    passed = slack_angle == 0.0

    return CheckResult(
        check_id="dcpf_slack_angle",
        check_name="DCPF Slack Angle Reference",
        status=CheckStatus.PASS if passed else CheckStatus.FAIL,
        metric_value=abs(slack_angle),
        metric_unit="degrees",
        tolerance=0.0,
        tolerance_unit="degrees",
        total_elements=1,
        passing_elements=1 if passed else 0,
        failing_elements=0 if passed else 1,
    )


# ---------------------------------------------------------------------------
# Report assembly and output
# ---------------------------------------------------------------------------


def _make_skip_result(check_id: str, check_name: str, reason: str) -> CheckResult:
    """Create a SKIP CheckResult."""
    return CheckResult(
        check_id=check_id,
        check_name=check_name,
        status=CheckStatus.SKIP,
        metric_value=None,
        metric_unit="",
        tolerance=0.0,
        tolerance_unit="",
        total_elements=0,
        passing_elements=0,
        failing_elements=0,
        skip_reason=reason,
    )


def build_validation_report(
    acpf_checks: list[CheckResult],
    dcpf_checks: list[CheckResult],
    *,
    acpf_bus_count: int = 0,
    acpf_branch_count: int = 0,
    acpf_generator_count: int = 0,
    dcpf_bus_count: int = 0,
    dcpf_branch_count: int = 0,
) -> ValidationReport:
    """Assemble individual check results into a complete validation report.

    Args:
        acpf_checks: Results from the four ACPF checks.
        dcpf_checks: Results from the three DCPF checks.
        acpf_bus_count: Number of ACPF buses loaded.
        acpf_branch_count: Number of ACPF branches loaded.
        acpf_generator_count: Number of ACPF generators loaded.
        dcpf_bus_count: Number of DCPF buses loaded.
        dcpf_branch_count: Number of DCPF branches loaded.

    Returns:
        A ValidationReport with all fields populated.
    """
    all_checks = acpf_checks + dcpf_checks
    passed = sum(1 for c in all_checks if c.status == CheckStatus.PASS)
    failed = sum(1 for c in all_checks if c.status == CheckStatus.FAIL)
    skipped = sum(1 for c in all_checks if c.status == CheckStatus.SKIP)

    summary = ReportSummary(
        total_checks=len(all_checks),
        passed=passed,
        failed=failed,
        skipped=skipped,
        acpf_bus_count=acpf_bus_count,
        acpf_branch_count=acpf_branch_count,
        acpf_generator_count=acpf_generator_count,
        dcpf_bus_count=dcpf_bus_count,
        dcpf_branch_count=dcpf_branch_count,
    )

    return ValidationReport(
        acpf_checks=acpf_checks,
        dcpf_checks=dcpf_checks,
        all_passed=(failed == 0 and skipped == 0),
        summary=summary,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _check_result_to_dict(cr: CheckResult) -> dict:
    """Serialize a CheckResult to a JSON-compatible dict."""
    return {
        "check_id": cr.check_id,
        "check_name": cr.check_name,
        "status": cr.status.value,
        "metric_value": cr.metric_value,
        "metric_unit": cr.metric_unit,
        "tolerance": cr.tolerance,
        "tolerance_unit": cr.tolerance_unit,
        "total_elements": cr.total_elements,
        "passing_elements": cr.passing_elements,
        "failing_elements": cr.failing_elements,
        "detail": cr.detail,
        "notes": cr.notes,
        "skip_reason": cr.skip_reason,
    }


def write_report_json(report: ValidationReport, output_path: Path) -> None:
    """Write the validation report as JSON.

    Args:
        report: The assembled validation report.
        output_path: Full path to the output JSON file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "report_version": _REPORT_VERSION,
        "timestamp": report.timestamp,
        "summary": {
            "total_checks": report.summary.total_checks,
            "passed": report.summary.passed,
            "failed": report.summary.failed,
            "skipped": report.summary.skipped,
            "all_passed": report.all_passed,
            "acpf_bus_count": report.summary.acpf_bus_count,
            "acpf_branch_count": report.summary.acpf_branch_count,
            "acpf_generator_count": report.summary.acpf_generator_count,
            "dcpf_bus_count": report.summary.dcpf_bus_count,
            "dcpf_branch_count": report.summary.dcpf_branch_count,
        },
        "checks": [_check_result_to_dict(c) for c in report.acpf_checks + report.dcpf_checks],
    }

    output_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_report_markdown(report: ValidationReport, output_path: Path) -> None:
    """Write the validation report as human-readable markdown.

    Args:
        report: The assembled validation report.
        output_path: Full path to the output markdown file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    status_label = "ALL PASSED" if report.all_passed else "ISSUES FOUND"
    lines.append("# Reference Solution Validation Report")
    lines.append("")
    lines.append(f"**Status:** {status_label}")
    lines.append(f"**Timestamp:** {report.timestamp}")
    lines.append(
        f"**Summary:** {report.summary.passed} passed, "
        f"{report.summary.failed} failed, "
        f"{report.summary.skipped} skipped "
        f"(of {report.summary.total_checks} total)"
    )
    lines.append("")

    # Summary table
    lines.append("## Check Summary")
    lines.append("")
    lines.append("| # | Check | Status | Metric | Tolerance |")
    lines.append("|---|-------|--------|--------|-----------|")

    all_checks = report.acpf_checks + report.dcpf_checks
    for i, c in enumerate(all_checks, 1):
        status_str = c.status.value.upper()
        if c.metric_value is not None:
            metric_str = f"{c.metric_value:.4f} {c.metric_unit}"
        else:
            metric_str = "N/A"
        tol_str = f"{c.tolerance} {c.tolerance_unit}" if c.tolerance > 0 else c.tolerance_unit
        lines.append(f"| {i} | {c.check_name} | {status_str} | {metric_str} | {tol_str} |")

    lines.append("")

    # Detail sections for non-passing checks
    for c in all_checks:
        if c.status == CheckStatus.PASS:
            continue

        lines.append(f"## {c.check_name}")
        lines.append("")

        if c.status == CheckStatus.SKIP:
            lines.append(f"**Skipped:** {c.skip_reason}")
            lines.append("")
            continue

        if c.notes:
            for note in c.notes:
                lines.append(f"> {note}")
            lines.append("")

        if c.detail:
            # Limit to top 10 in markdown
            shown = c.detail[:10]
            remaining = len(c.detail) - len(shown)

            if c.check_id == "acpf_kcl":
                lines.append("| Bus | dP (MW) | dQ (MVAr) | Mismatch (MVA) |")
                lines.append("|-----|---------|-----------|----------------|")
                for d in shown:
                    lines.append(
                        f"| {d['bus']} | {d['dP_mw']:.4f} | "
                        f"{d['dQ_mvar']:.4f} | {d['mismatch_mva']:.4f} |"
                    )
            elif c.check_id == "acpf_generator_limits":
                lines.append("| Bus | ID | P | Q | PT | PB | QT | QB | Violation |")
                lines.append("|-----|----|----|----|----|----|----|----|----|")
                for d in shown:
                    vtype = (
                        ", ".join(d["violation_type"])
                        if isinstance(d["violation_type"], list)
                        else d["violation_type"]
                    )
                    lines.append(
                        f"| {d['bus']} | {d['machine_id']} | "
                        f"{d['P']:.2f} | {d['Q']:.2f} | "
                        f"{d['PT']:.2f} | {d['PB']:.2f} | "
                        f"{d['QT']:.2f} | {d['QB']:.2f} | {vtype} |"
                    )
            elif c.check_id == "dcpf_flow_angle_consistency":
                lines.append("| From | To | Ckt | Stored (MW) | Recomputed (MW) | Deviation (MW) |")
                lines.append("|------|-----|-----|-------------|-----------------|")
                for d in shown:
                    lines.append(
                        f"| {d['from_bus']} | {d['to_bus']} | {d['ckt']} | "
                        f"{d['P_stored_mw']:.4f} | {d['P_recomputed_mw']:.4f} | "
                        f"{d['deviation_mw']:.4f} |"
                    )
            elif c.check_id == "acpf_vm_plausibility":
                lines.append("| Bus | VM (p.u.) |")
                lines.append("|-----|-----------|")
                for d in shown:
                    lines.append(f"| {d['bus']} | {d['VM']:.6f} |")
            else:
                # Generic detail rendering
                for d in shown:
                    lines.append(f"- {d}")

            if remaining > 0:
                lines.append(f"\n*... and {remaining} more (total: {len(c.detail)})*")

        lines.append("")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_validation(
    acpf_dir: Path,
    dcpf_dir: Path,
    intermediate_dir: Path,
    reference_dir: Path,
    output_dir: Path,
) -> ValidationReport:
    """Top-level orchestrator for reference solution validation.

    Steps:
    1. Load all input data (ACPF, DCPF, intermediate format, exclusion registry).
       If a dataset is missing, mark its checks as SKIP with the reason.
    2. Run ACPF checks A-D (if ACPF data loaded successfully).
    3. Run DCPF checks A-C (if DCPF data loaded successfully).
    4. Assemble the ValidationReport.
    5. Write validation_report.json and validation_report.md to output_dir.
    6. Return the report for programmatic consumption.

    Args:
        acpf_dir: Directory containing ACPF reference files.
        dcpf_dir: Directory containing DCPF reference files.
        intermediate_dir: Directory containing canonical parser CSV output.
        reference_dir: Directory containing the bus exclusion registry.
        output_dir: Directory for output files.

    Returns:
        The assembled ValidationReport.
    """
    # --- Load excluded buses (optional) ---
    try:
        excluded_buses = load_excluded_buses(reference_dir)
    except FileNotFoundError:
        excluded_buses = set()

    # --- ACPF data loading ---
    acpf_buses: list[dict] = []
    acpf_branches: list[dict] = []
    acpf_generators: list[dict] = []
    acpf_summary: dict | None = None
    acpf_ok = True
    acpf_skip_reason = ""

    try:
        acpf_buses = load_acpf_buses(acpf_dir)
        acpf_branches = load_acpf_branches(acpf_dir)
        acpf_generators = load_acpf_generators(acpf_dir)
        acpf_summary = load_acpf_summary(acpf_dir)
    except FileNotFoundError as e:
        acpf_ok = False
        acpf_skip_reason = str(e)

    # --- Intermediate data loading ---
    intermediate_buses: list[dict] = []
    intermediate_generators: list[dict] = []
    intermediate_branches: list[dict] = []
    intermediate_ok = True
    intermediate_skip_reason = ""

    try:
        intermediate_buses = load_intermediate_buses(intermediate_dir)
    except (FileNotFoundError, ValueError) as e:
        intermediate_ok = False
        intermediate_skip_reason = str(e)

    try:
        intermediate_generators = load_intermediate_generators(intermediate_dir)
    except (FileNotFoundError, ValueError):
        # Generator limits not available -- generator-limit check will skip
        intermediate_generators = []

    try:
        intermediate_branches = load_intermediate_branches(intermediate_dir)
    except (FileNotFoundError, ValueError):
        intermediate_branches = []

    # --- DCPF data loading ---
    dcpf_buses: list[dict] = []
    dcpf_branches: list[dict] = []
    dcpf_summary: dict | None = None
    dcpf_ok = True
    dcpf_skip_reason = ""

    try:
        dcpf_buses = load_dcpf_buses(dcpf_dir)
        dcpf_branches = load_dcpf_branches(dcpf_dir)
        dcpf_summary = load_dcpf_summary(dcpf_dir)
    except FileNotFoundError as e:
        dcpf_ok = False
        dcpf_skip_reason = str(e)

    # --- Run ACPF checks ---
    acpf_checks: list[CheckResult] = []

    if acpf_ok and acpf_summary is not None:
        acpf_checks.append(check_acpf_power_balance(acpf_summary))
    else:
        acpf_checks.append(
            _make_skip_result(
                "acpf_power_balance",
                "ACPF System Power Balance",
                acpf_skip_reason or "ACPF data not available",
            )
        )

    if acpf_ok and intermediate_ok:
        acpf_checks.append(
            check_acpf_kcl(
                acpf_buses,
                acpf_branches,
                acpf_generators,
                intermediate_buses,
                excluded_buses,
            )
        )
    else:
        reason = acpf_skip_reason or intermediate_skip_reason or "Required data not available"
        acpf_checks.append(_make_skip_result("acpf_kcl", "ACPF Per-Bus KCL", reason))

    if acpf_ok:
        acpf_checks.append(check_acpf_vm_plausibility(acpf_buses, excluded_buses))
    else:
        acpf_checks.append(
            _make_skip_result(
                "acpf_vm_plausibility",
                "ACPF Voltage Magnitude Plausibility",
                acpf_skip_reason or "ACPF data not available",
            )
        )

    if acpf_ok and intermediate_generators and acpf_summary is not None:
        acpf_checks.append(
            check_acpf_generator_limits(
                acpf_generators,
                intermediate_generators,
                acpf_summary,
            )
        )
    else:
        reason = acpf_skip_reason or "Generator limit columns not available in intermediate format"
        acpf_checks.append(
            _make_skip_result(
                "acpf_generator_limits",
                "ACPF Generator Output Within Limits",
                reason,
            )
        )

    # --- Run DCPF checks ---
    dcpf_checks: list[CheckResult] = []

    if dcpf_ok and dcpf_summary is not None:
        dcpf_checks.append(check_dcpf_power_balance(dcpf_summary))
    else:
        dcpf_checks.append(
            _make_skip_result(
                "dcpf_power_balance",
                "DCPF Power Balance (Lossless)",
                dcpf_skip_reason or "DCPF data not available",
            )
        )

    if dcpf_ok and intermediate_branches and dcpf_summary is not None:
        dcpf_checks.append(
            check_dcpf_flow_angle_consistency(
                dcpf_buses,
                dcpf_branches,
                intermediate_branches,
                dcpf_summary,
            )
        )
    else:
        reason = dcpf_skip_reason or "Branch reactance data not available"
        dcpf_checks.append(
            _make_skip_result(
                "dcpf_flow_angle_consistency",
                "DCPF Flow-Angle Consistency",
                reason,
            )
        )

    if dcpf_ok and dcpf_summary is not None:
        dcpf_checks.append(check_dcpf_slack_angle(dcpf_buses, dcpf_summary))
    else:
        dcpf_checks.append(
            _make_skip_result(
                "dcpf_slack_angle",
                "DCPF Slack Angle Reference",
                dcpf_skip_reason or "DCPF data not available",
            )
        )

    # --- Assemble report ---
    report = build_validation_report(
        acpf_checks,
        dcpf_checks,
        acpf_bus_count=len(acpf_buses),
        acpf_branch_count=len(acpf_branches),
        acpf_generator_count=len(acpf_generators),
        dcpf_bus_count=len(dcpf_buses),
        dcpf_branch_count=len(dcpf_branches),
    )

    # --- Write outputs ---
    output_dir.mkdir(parents=True, exist_ok=True)
    write_report_json(report, output_dir / "validation_report.json")
    write_report_markdown(report, output_dir / "validation_report.md")

    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for reference solution validation.

    Usage::

        python -m data.fnm.scripts.validation_report \\
            --acpf-dir data/fnm/reference/acpf/ \\
            --dcpf-dir data/fnm/reference/dcpf/ \\
            --intermediate-dir data/fnm/intermediate/canonical/ \\
            --reference-dir data/fnm/reference/ \\
            [-o data/fnm/reference/]

    Exit codes:
    - 0: Report generated successfully (regardless of check outcomes).
    - 1: Missing required input files that prevent any checks from running.
    - 2: Malformed input data (e.g., unparseable CSV or JSON).

    Args:
        argv: Command-line arguments. If None, reads from sys.argv[1:].
    """
    parser = argparse.ArgumentParser(
        description="Validate ACPF and DCPF reference solutions for internal consistency."
    )
    parser.add_argument(
        "--acpf-dir",
        type=Path,
        required=True,
        help="Directory containing ACPF reference files (buses_acpf.csv, etc.)",
    )
    parser.add_argument(
        "--dcpf-dir",
        type=Path,
        required=True,
        help="Directory containing DCPF reference files (buses_dcpf.csv, etc.)",
    )
    parser.add_argument(
        "--intermediate-dir",
        type=Path,
        required=True,
        help="Directory containing canonical parser CSV output.",
    )
    parser.add_argument(
        "--reference-dir",
        type=Path,
        required=True,
        help="Directory containing the bus exclusion registry.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (defaults to --reference-dir).",
    )

    args = parser.parse_args(argv)
    output_dir = args.output_dir or args.reference_dir

    try:
        report = run_validation(
            acpf_dir=args.acpf_dir,
            dcpf_dir=args.dcpf_dir,
            intermediate_dir=args.intermediate_dir,
            reference_dir=args.reference_dir,
            output_dir=output_dir,
        )
    except ValueError as exc:
        print(f"ERROR: Malformed input data: {exc}", file=sys.stderr)
        sys.exit(2)

    # Print summary
    print(f"Validation report written to {output_dir}")
    print(
        f"  {report.summary.passed} passed, "
        f"{report.summary.failed} failed, "
        f"{report.summary.skipped} skipped"
    )
    if not report.all_passed:
        sys.exit(0)  # Self-check, not a gate -- always exit 0


if __name__ == "__main__":
    main()
