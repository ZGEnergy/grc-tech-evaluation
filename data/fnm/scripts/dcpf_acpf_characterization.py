"""DCPF-vs-ACPF Characterization for FNM Annual S01.

Compares the DCPF reference solution (Phase 3 D3) against the ACPF reference
solution (Phase 3 D2) to characterize how well the DC power flow approximation
represents the full AC solution.  Quantifies per-bus angle deviations, per-branch
active power flow deviations, aggregate distribution statistics, and identifies
worst-case elements with probable physical causes for the largest discrepancies.

Output files:
- ``data/fnm/reference/dcpf_vs_acpf_characterization.json`` (machine-readable)
- ``data/fnm/reference/dcpf_vs_acpf_characterization.md`` (human-readable)

Uses only Python stdlib (no numpy/scipy).
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import statistics
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NEAR_ZERO_FLOW_THRESHOLD_MW: float = 1.0
"""Branches with |P_from_acpf| <= this value are excluded from percentage
deviation calculations. Standard practice for power flow comparisons."""

ANGLE_COMPLIANCE_THRESHOLDS_DEG: list[float] = [0.5, 1.0, 2.0, 3.0, 5.0, 10.0]
"""Thresholds (degrees) for cumulative angle deviation compliance fractions."""

FLOW_COMPLIANCE_THRESHOLDS_PCT: list[float] = [1.0, 2.0, 5.0, 10.0, 20.0, 50.0]
"""Thresholds (percent) for cumulative flow deviation compliance fractions."""

EXPECTED_ANGLE_COMPLIANCE_PCT: float = 95.0
"""Expected: >95% of buses within 3 degrees."""

EXPECTED_ANGLE_THRESHOLD_DEG: float = 3.0
"""Angle threshold for the expected-range check."""

EXPECTED_FLOW_COMPLIANCE_PCT: float = 90.0
"""Expected: >90% of branches within 10%."""

EXPECTED_FLOW_THRESHOLD_PCT: float = 10.0
"""Flow percentage threshold for the expected-range check."""

WORST_CASE_COUNT: int = 50
"""Number of worst-case buses and branches to include in the report."""


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------


class DeviationCause(Enum):
    """Probable cause categories for worst-case DC-vs-AC deviations."""

    PHASE_SHIFTER = "phase_shifter"
    HIGH_REACTANCE = "high_reactance"
    HEAVY_LOADING = "heavy_loading"
    LOW_VOLTAGE = "low_voltage"
    HIGH_VOLTAGE = "high_voltage"
    TRANSFORMER_TAP = "transformer_tap"
    SLACK_BUS_VICINITY = "slack_bus_vicinity"
    UNCATEGORIZED = "uncategorized"


@dataclass(frozen=True)
class BusDeviation:
    """Per-bus angle deviation record."""

    bus: int
    VA_acpf_deg: float
    VA_dcpf_deg: float
    delta_VA_deg: float
    abs_delta_VA_deg: float
    VM_acpf_pu: float
    base_kv: float
    area: int
    causes: list[DeviationCause] = field(default_factory=list)


@dataclass(frozen=True)
class BranchDeviation:
    """Per-branch flow deviation record."""

    from_bus: int
    to_bus: int
    ckt: str
    P_from_acpf_MW: float
    P_flow_dcpf_MW: float
    delta_P_MW: float
    abs_delta_P_MW: float
    delta_P_pct: float | None
    """None when |P_from_acpf| <= near-zero threshold."""
    abs_delta_P_pct: float | None
    x_pu: float
    tap_ratio: float
    shift_deg: float
    is_transformer: bool
    causes: list[DeviationCause] = field(default_factory=list)


@dataclass(frozen=True)
class AggregateStats:
    """Aggregate statistics for a deviation distribution."""

    count: int
    mean: float
    median: float
    std: float
    min: float
    max: float
    p05: float
    p95: float


@dataclass(frozen=True)
class ComplianceFractions:
    """Cumulative compliance fractions at multiple thresholds."""

    thresholds: list[float]
    """The threshold values (degrees or percent)."""
    fractions: list[float]
    """Fraction of elements within each threshold (0.0 to 1.0)."""


@dataclass(frozen=True)
class CharacterizationResult:
    """Complete characterization output, serializable to JSON and markdown."""

    bus_deviations: list[BusDeviation]
    branch_deviations: list[BranchDeviation]
    angle_stats_signed: AggregateStats
    angle_stats_absolute: AggregateStats
    angle_compliance: ComplianceFractions
    flow_mw_stats_signed: AggregateStats
    flow_mw_stats_absolute: AggregateStats
    flow_pct_stats_signed: AggregateStats
    flow_pct_stats_absolute: AggregateStats
    flow_pct_compliance: ComplianceFractions
    join_summary: dict[str, int]
    system_level: dict[str, float]
    expected_range_checks: dict[str, dict]
    worst_buses: list[BusDeviation]
    worst_branches: list[BranchDeviation]
    warnings: list[str]
    metadata: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_acpf_buses(acpf_buses_path: Path) -> list[dict]:
    """Load ACPF bus reference data from buses_acpf.csv.

    Args:
        acpf_buses_path: Path to ``buses_acpf.csv``.

    Returns:
        List of dicts with keys ``bus`` (int), ``VM`` (float), ``VA`` (float).

    Raises:
        FileNotFoundError: If the CSV does not exist.
        ValueError: If required columns are missing.
    """
    if not acpf_buses_path.exists():
        raise FileNotFoundError(f"ACPF bus CSV not found: {acpf_buses_path}")

    result: list[dict] = []
    with open(acpf_buses_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"ACPF bus CSV is empty: {acpf_buses_path}")
        fields = {fn.strip().lower() for fn in reader.fieldnames}
        if "bus" not in fields or "va" not in fields:
            raise ValueError(f"Required columns 'bus', 'VA' not found. Got: {reader.fieldnames}")
        for row in reader:
            result.append(
                {
                    "bus": int(float(row["bus"].strip())),
                    "VM": float(row["VM"].strip()) if "VM" in row else 1.0,
                    "VA": float(row["VA"].strip()),
                }
            )
    return result


def load_dcpf_buses(dcpf_buses_path: Path) -> list[dict]:
    """Load DCPF bus reference data from buses_dcpf.csv.

    Args:
        dcpf_buses_path: Path to ``buses_dcpf.csv``.

    Returns:
        List of dicts with keys ``bus`` (int), ``VA`` (float).

    Raises:
        FileNotFoundError: If the CSV does not exist.
        ValueError: If required columns are missing.
    """
    if not dcpf_buses_path.exists():
        raise FileNotFoundError(f"DCPF bus CSV not found: {dcpf_buses_path}")

    result: list[dict] = []
    with open(dcpf_buses_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"DCPF bus CSV is empty: {dcpf_buses_path}")
        fields = {fn.strip().lower() for fn in reader.fieldnames}
        if "bus" not in fields or "va" not in fields:
            raise ValueError(f"Required columns 'bus', 'VA' not found. Got: {reader.fieldnames}")
        for row in reader:
            result.append(
                {
                    "bus": int(float(row["bus"].strip())),
                    "VA": float(row["VA"].strip()),
                }
            )
    return result


def load_acpf_branches(acpf_branches_path: Path) -> list[dict]:
    """Load ACPF branch reference data from branches_acpf.csv.

    Args:
        acpf_branches_path: Path to ``branches_acpf.csv``.

    Returns:
        List of dicts with keys ``from_bus`` (int), ``to_bus`` (int),
        ``ckt`` (str), ``P_from`` (float), ``Q_from`` (float),
        ``P_to`` (float), ``Q_to`` (float).

    Raises:
        FileNotFoundError: If the CSV does not exist.
        ValueError: If required columns are missing.
    """
    if not acpf_branches_path.exists():
        raise FileNotFoundError(f"ACPF branch CSV not found: {acpf_branches_path}")

    result: list[dict] = []
    with open(acpf_branches_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"ACPF branch CSV is empty: {acpf_branches_path}")
        fields = {fn.strip().lower() for fn in reader.fieldnames}
        for req in ["from_bus", "to_bus", "ckt", "p_from"]:
            if req not in fields:
                raise ValueError(f"Required column '{req}' not found. Got: {reader.fieldnames}")
        for row in reader:
            result.append(
                {
                    "from_bus": int(float(row["from_bus"].strip())),
                    "to_bus": int(float(row["to_bus"].strip())),
                    "ckt": row["ckt"].strip(),
                    "P_from": float(row["P_from"].strip()),
                    "Q_from": float(row.get("Q_from", "0").strip()),
                    "P_to": float(row.get("P_to", "0").strip()),
                    "Q_to": float(row.get("Q_to", "0").strip()),
                }
            )
    return result


def load_dcpf_branches(dcpf_branches_path: Path) -> list[dict]:
    """Load DCPF branch reference data from branches_dcpf.csv.

    Args:
        dcpf_branches_path: Path to ``branches_dcpf.csv``.

    Returns:
        List of dicts with keys ``from_bus`` (int), ``to_bus`` (int),
        ``ckt`` (str), ``P_flow_MW`` (float).

    Raises:
        FileNotFoundError: If the CSV does not exist.
        ValueError: If required columns are missing.
    """
    if not dcpf_branches_path.exists():
        raise FileNotFoundError(f"DCPF branch CSV not found: {dcpf_branches_path}")

    result: list[dict] = []
    with open(dcpf_branches_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"DCPF branch CSV is empty: {dcpf_branches_path}")
        fields = {fn.strip().lower() for fn in reader.fieldnames}
        for req in ["from_bus", "to_bus", "ckt", "p_flow_mw"]:
            if req not in fields:
                raise ValueError(f"Required column '{req}' not found. Got: {reader.fieldnames}")
        for row in reader:
            result.append(
                {
                    "from_bus": int(float(row["from_bus"].strip())),
                    "to_bus": int(float(row["to_bus"].strip())),
                    "ckt": row["ckt"].strip(),
                    "P_flow_MW": float(row["P_flow_MW"].strip()),
                }
            )
    return result


def load_summary_json(summary_path: Path) -> dict:
    """Load a summary JSON file (ACPF or DCPF).

    Args:
        summary_path: Path to ``summary_acpf.json`` or ``summary_dcpf.json``.

    Returns:
        Parsed JSON as a dict.

    Raises:
        FileNotFoundError: If the JSON does not exist.
        json.JSONDecodeError: If the JSON is malformed.
    """
    if not summary_path.exists():
        raise FileNotFoundError(f"Summary JSON not found: {summary_path}")
    return json.loads(summary_path.read_text(encoding="utf-8"))


def load_intermediate_branches(intermediate_dir: Path) -> list[dict]:
    """Load branch/transformer data from the canonical parser's intermediate format.

    Used for cause annotation heuristics (reactance, tap ratio, shift angle,
    thermal rating). Auto-detects column names from MATPOWER and GridCal conventions.

    Args:
        intermediate_dir: Directory containing the intermediate format CSVs.

    Returns:
        List of dicts with keys: ``from_bus``, ``to_bus``, ``ckt``, ``x_pu``,
        ``tap_ratio``, ``shift_deg``, ``rate_a_mw`` (or None), ``is_transformer``.

    Raises:
        FileNotFoundError: If branch CSV does not exist in the directory.
    """
    # Try common filenames
    candidates = ["branch.csv", "branches.csv", "branch_data.csv"]
    branch_path: Path | None = None
    for name in candidates:
        p = intermediate_dir / name
        if p.exists():
            branch_path = p
            break

    if branch_path is None:
        raise FileNotFoundError(f"No branch CSV found in {intermediate_dir}. Tried: {candidates}")

    # Column name mappings (canonical -> variants)
    from_bus_names = ["f_bus", "from_bus", "i", "fbus"]
    to_bus_names = ["t_bus", "to_bus", "j", "tbus"]
    x_names = ["br_x", "x"]
    tap_names = ["tap", "windv1"]
    shift_names = ["shift", "ang1"]
    ckt_names = ["ckt", "circuit"]
    rate_a_names = ["rate_a", "ratea", "rating_a", "mva_rating"]

    result: list[dict] = []
    with open(branch_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return result

        lower_map = {fn.strip().lower(): fn.strip() for fn in reader.fieldnames}

        def _find(variants: list[str]) -> str | None:
            for v in variants:
                if v.lower() in lower_map:
                    return lower_map[v.lower()]
            return None

        from_col = _find(from_bus_names)
        to_col = _find(to_bus_names)
        x_col = _find(x_names)
        tap_col = _find(tap_names)
        shift_col = _find(shift_names)
        ckt_col = _find(ckt_names)
        rate_a_col = _find(rate_a_names)

        if from_col is None or to_col is None:
            raise ValueError(
                f"Required columns from_bus/to_bus not found. Got: {reader.fieldnames}"
            )

        for row in reader:
            tap_raw = float(row[tap_col].strip()) if tap_col and row.get(tap_col) else 0.0
            tap = tap_raw if tap_raw != 0.0 else 1.0
            shift = float(row[shift_col].strip()) if shift_col and row.get(shift_col) else 0.0
            x = float(row[x_col].strip()) if x_col and row.get(x_col) else 0.0

            rate_a: float | None = None
            if rate_a_col and row.get(rate_a_col):
                try:
                    val = float(row[rate_a_col].strip())
                    rate_a = val if val > 0 else None
                except (ValueError, TypeError):
                    pass

            is_transformer = tap != 1.0 or shift != 0.0

            result.append(
                {
                    "from_bus": int(float(row[from_col].strip())),
                    "to_bus": int(float(row[to_col].strip())),
                    "ckt": row[ckt_col].strip() if ckt_col and row.get(ckt_col) else "1",
                    "x_pu": x,
                    "tap_ratio": tap,
                    "shift_deg": shift,
                    "rate_a_mw": rate_a,
                    "is_transformer": is_transformer,
                }
            )
    return result


def load_intermediate_buses(intermediate_dir: Path) -> list[dict]:
    """Load bus data from the canonical parser's intermediate format.

    Used for cause annotation heuristics (base kV, area number) and for
    enriching worst-case bus records.

    Args:
        intermediate_dir: Directory containing the intermediate format CSVs.

    Returns:
        List of dicts with keys: ``bus`` (int), ``base_kv`` (float),
        ``area`` (int), ``bus_type`` (int).

    Raises:
        FileNotFoundError: If bus CSV does not exist in the directory.
    """
    candidates = ["bus.csv", "buses.csv", "bus_data.csv"]
    bus_path: Path | None = None
    for name in candidates:
        p = intermediate_dir / name
        if p.exists():
            bus_path = p
            break

    if bus_path is None:
        raise FileNotFoundError(f"No bus CSV found in {intermediate_dir}. Tried: {candidates}")

    bus_names = ["bus_i", "bus", "i", "number", "bus_number"]
    kv_names = ["base_kv", "baskv", "basekv", "vnom"]
    area_names = ["area"]
    type_names = ["type", "bus_type", "ide"]

    result: list[dict] = []
    with open(bus_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return result

        lower_map = {fn.strip().lower(): fn.strip() for fn in reader.fieldnames}

        def _find(variants: list[str]) -> str | None:
            for v in variants:
                if v.lower() in lower_map:
                    return lower_map[v.lower()]
            return None

        bus_col = _find(bus_names)
        kv_col = _find(kv_names)
        area_col = _find(area_names)
        type_col = _find(type_names)

        if bus_col is None:
            raise ValueError(f"Required column 'bus' not found. Got: {reader.fieldnames}")

        for row in reader:
            result.append(
                {
                    "bus": int(float(row[bus_col].strip())),
                    "base_kv": float(row[kv_col].strip()) if kv_col and row.get(kv_col) else 0.0,
                    "area": int(float(row[area_col].strip()))
                    if area_col and row.get(area_col)
                    else 0,
                    "bus_type": (
                        int(float(row[type_col].strip())) if type_col and row.get(type_col) else 1
                    ),
                }
            )
    return result


# ---------------------------------------------------------------------------
# Join operations
# ---------------------------------------------------------------------------


def join_buses(
    acpf_buses: list[dict],
    dcpf_buses: list[dict],
) -> tuple[list[dict], dict[str, int]]:
    """Inner-join ACPF and DCPF bus records on bus number.

    Args:
        acpf_buses: ACPF bus records (bus, VM, VA).
        dcpf_buses: DCPF bus records (bus, VA).

    Returns:
        A tuple of:
        - Matched records: list of dicts with keys ``bus``, ``VM_acpf``,
          ``VA_acpf``, ``VA_dcpf``.
        - Join summary: dict with keys ``buses_in_acpf``, ``buses_in_dcpf``,
          ``buses_matched``, ``buses_acpf_only``, ``buses_dcpf_only``.
    """
    acpf_map: dict[int, dict] = {b["bus"]: b for b in acpf_buses}
    dcpf_map: dict[int, dict] = {b["bus"]: b for b in dcpf_buses}

    acpf_keys = set(acpf_map.keys())
    dcpf_keys = set(dcpf_map.keys())
    matched_keys = acpf_keys & dcpf_keys

    matched: list[dict] = []
    for bus_num in sorted(matched_keys):
        acpf = acpf_map[bus_num]
        dcpf = dcpf_map[bus_num]
        matched.append(
            {
                "bus": bus_num,
                "VM_acpf": acpf.get("VM", 1.0),
                "VA_acpf": acpf["VA"],
                "VA_dcpf": dcpf["VA"],
            }
        )

    summary = {
        "buses_in_acpf": len(acpf_buses),
        "buses_in_dcpf": len(dcpf_buses),
        "buses_matched": len(matched),
        "buses_acpf_only": len(acpf_keys - dcpf_keys),
        "buses_dcpf_only": len(dcpf_keys - acpf_keys),
    }

    return matched, summary


def _normalize_branch_key(from_bus: int, to_bus: int, ckt: str) -> tuple[int, int, str, bool]:
    """Normalize a branch key so (min, max, ckt) is canonical.

    Returns:
        (normalized_from, normalized_to, ckt, was_swapped)
    """
    if from_bus <= to_bus:
        return from_bus, to_bus, ckt, False
    return to_bus, from_bus, ckt, True


def join_branches(
    acpf_branches: list[dict],
    dcpf_branches: list[dict],
) -> tuple[list[dict], dict[str, int]]:
    """Inner-join ACPF and DCPF branch records on (from_bus, to_bus, ckt).

    Normalizes branch keys to (min(from, to), max(from, to), ckt) before
    joining.  If from/to are swapped, the DCPF flow sign is negated.

    Args:
        acpf_branches: ACPF branch records.
        dcpf_branches: DCPF branch records.

    Returns:
        A tuple of:
        - Matched records: list of dicts with keys ``from_bus``, ``to_bus``,
          ``ckt``, ``P_from_acpf``, ``P_flow_dcpf``.
        - Join summary: dict with keys ``branches_in_acpf``, ``branches_in_dcpf``,
          ``branches_matched``, ``branches_acpf_only``, ``branches_dcpf_only``.
    """
    # Build ACPF lookup with normalized keys
    acpf_map: dict[tuple[int, int, str], dict] = {}
    for b in acpf_branches:
        nf, nt, nc, swapped = _normalize_branch_key(b["from_bus"], b["to_bus"], b["ckt"])
        # If swapped, we use P_to (negated) as the "from" direction perspective
        p_from = b["P_from"]
        acpf_map[(nf, nt, nc)] = {
            "from_bus": b["from_bus"],
            "to_bus": b["to_bus"],
            "ckt": b["ckt"],
            "P_from_acpf": p_from,
        }

    # Build DCPF lookup with normalized keys
    dcpf_map: dict[tuple[int, int, str], dict] = {}
    for b in dcpf_branches:
        nf, nt, nc, swapped = _normalize_branch_key(b["from_bus"], b["to_bus"], b["ckt"])
        p_flow = -b["P_flow_MW"] if swapped else b["P_flow_MW"]
        dcpf_map[(nf, nt, nc)] = {
            "from_bus": b["from_bus"],
            "to_bus": b["to_bus"],
            "ckt": b["ckt"],
            "P_flow_dcpf": p_flow,
        }

    acpf_keys = set(acpf_map.keys())
    dcpf_keys = set(dcpf_map.keys())
    matched_keys = acpf_keys & dcpf_keys

    matched: list[dict] = []
    for key in sorted(matched_keys):
        acpf = acpf_map[key]
        dcpf = dcpf_map[key]
        matched.append(
            {
                "from_bus": acpf["from_bus"],
                "to_bus": acpf["to_bus"],
                "ckt": acpf["ckt"],
                "P_from_acpf": acpf["P_from_acpf"],
                "P_flow_dcpf": dcpf["P_flow_dcpf"],
            }
        )

    summary = {
        "branches_in_acpf": len(acpf_branches),
        "branches_in_dcpf": len(dcpf_branches),
        "branches_matched": len(matched),
        "branches_acpf_only": len(acpf_keys - dcpf_keys),
        "branches_dcpf_only": len(dcpf_keys - acpf_keys),
    }

    return matched, summary


# ---------------------------------------------------------------------------
# Deviation computation
# ---------------------------------------------------------------------------


def compute_bus_deviations(
    matched_buses: list[dict],
    intermediate_buses: list[dict],
) -> list[BusDeviation]:
    """Compute per-bus angle deviation and enrich with intermediate format data.

    For each matched bus, computes:
    - delta_VA_deg = VA_dcpf - VA_acpf (signed)
    - abs_delta_VA_deg = |delta_VA_deg|

    Enriches with base_kv and area from the intermediate format bus table
    (joined on bus number). If a bus is not found in the intermediate data,
    base_kv defaults to 0.0 and area defaults to 0.

    Args:
        matched_buses: Output of ``join_buses`` (matched records).
        intermediate_buses: Output of ``load_intermediate_buses``.

    Returns:
        List of BusDeviation records, one per matched bus.
    """
    int_bus_map: dict[int, dict] = {b["bus"]: b for b in intermediate_buses}

    result: list[BusDeviation] = []
    for m in matched_buses:
        delta = m["VA_dcpf"] - m["VA_acpf"]
        int_data = int_bus_map.get(m["bus"], {})
        result.append(
            BusDeviation(
                bus=m["bus"],
                VA_acpf_deg=m["VA_acpf"],
                VA_dcpf_deg=m["VA_dcpf"],
                delta_VA_deg=delta,
                abs_delta_VA_deg=abs(delta),
                VM_acpf_pu=m.get("VM_acpf", 1.0),
                base_kv=int_data.get("base_kv", 0.0),
                area=int_data.get("area", 0),
            )
        )
    return result


def compute_branch_deviations(
    matched_branches: list[dict],
    intermediate_branches: list[dict],
) -> list[BranchDeviation]:
    """Compute per-branch flow deviation and enrich with intermediate format data.

    For each matched branch, computes:
    - delta_P_MW = P_flow_dcpf - P_from_acpf (signed)
    - abs_delta_P_MW = |delta_P_MW|
    - delta_P_pct = delta_P_MW / |P_from_acpf| * 100 (if |P_from_acpf| > threshold)
    - abs_delta_P_pct = |delta_P_pct| (if applicable, else None)

    Enriches with x_pu, tap_ratio, shift_deg, is_transformer from the
    intermediate format branch table (joined on from_bus, to_bus, ckt).

    Args:
        matched_branches: Output of ``join_branches`` (matched records).
        intermediate_branches: Output of ``load_intermediate_branches``.

    Returns:
        List of BranchDeviation records, one per matched branch.
    """
    # Build intermediate branch lookup with normalized keys
    int_br_map: dict[tuple[int, int, str], dict] = {}
    for b in intermediate_branches:
        nf, nt, nc, _ = _normalize_branch_key(b["from_bus"], b["to_bus"], b["ckt"])
        int_br_map[(nf, nt, nc)] = b

    result: list[BranchDeviation] = []
    for m in matched_branches:
        delta_mw = m["P_flow_dcpf"] - m["P_from_acpf"]
        abs_delta_mw = abs(delta_mw)

        abs_p_acpf = abs(m["P_from_acpf"])
        if abs_p_acpf > NEAR_ZERO_FLOW_THRESHOLD_MW:
            delta_pct = delta_mw / abs_p_acpf * 100.0
            abs_delta_pct: float | None = abs(delta_pct)
        else:
            delta_pct = None
            abs_delta_pct = None

        nf, nt, nc, _ = _normalize_branch_key(m["from_bus"], m["to_bus"], m["ckt"])
        int_data = int_br_map.get((nf, nt, nc), {})

        result.append(
            BranchDeviation(
                from_bus=m["from_bus"],
                to_bus=m["to_bus"],
                ckt=m["ckt"],
                P_from_acpf_MW=m["P_from_acpf"],
                P_flow_dcpf_MW=m["P_flow_dcpf"],
                delta_P_MW=delta_mw,
                abs_delta_P_MW=abs_delta_mw,
                delta_P_pct=delta_pct,
                abs_delta_P_pct=abs_delta_pct,
                x_pu=int_data.get("x_pu", 0.0),
                tap_ratio=int_data.get("tap_ratio", 1.0),
                shift_deg=int_data.get("shift_deg", 0.0),
                is_transformer=int_data.get("is_transformer", False),
            )
        )
    return result


# ---------------------------------------------------------------------------
# Aggregate statistics
# ---------------------------------------------------------------------------


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Compute the pth percentile using linear interpolation.

    Args:
        sorted_values: Sorted list of values.
        pct: Percentile to compute (0-100).

    Returns:
        The percentile value.
    """
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]

    # Use the 'linear interpolation' method (same as numpy default)
    k = (pct / 100.0) * (n - 1)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    d = k - f
    return sorted_values[int(f)] * (1 - d) + sorted_values[int(c)] * d


def compute_aggregate_stats(values: list[float]) -> AggregateStats:
    """Compute aggregate statistics for a list of numeric values.

    Args:
        values: Non-empty list of float values.

    Returns:
        AggregateStats with mean, median, std, min, max, p05, p95.

    Raises:
        ValueError: If values is empty.
    """
    if not values:
        raise ValueError("Cannot compute aggregate statistics for an empty list.")

    n = len(values)
    mean_val = statistics.mean(values)
    median_val = statistics.median(values)

    if n >= 2:
        std_val = statistics.stdev(values)
    else:
        std_val = 0.0

    sorted_vals = sorted(values)
    min_val = sorted_vals[0]
    max_val = sorted_vals[-1]
    p05 = _percentile(sorted_vals, 5.0)
    p95 = _percentile(sorted_vals, 95.0)

    return AggregateStats(
        count=n,
        mean=mean_val,
        median=median_val,
        std=std_val,
        min=min_val,
        max=max_val,
        p05=p05,
        p95=p95,
    )


def compute_compliance_fractions(
    values: list[float],
    thresholds: list[float],
) -> ComplianceFractions:
    """Compute the fraction of values at or below each threshold.

    Args:
        values: List of absolute (non-negative) deviation values.
        thresholds: Sorted list of threshold values.

    Returns:
        ComplianceFractions with fraction (0.0 to 1.0) at each threshold.
    """
    n = len(values)
    if n == 0:
        return ComplianceFractions(
            thresholds=list(thresholds),
            fractions=[0.0] * len(thresholds),
        )

    sorted_vals = sorted(values)
    fractions: list[float] = []
    for threshold in thresholds:
        count = sum(1 for v in sorted_vals if v <= threshold)
        fractions.append(count / n)

    return ComplianceFractions(
        thresholds=list(thresholds),
        fractions=fractions,
    )


# ---------------------------------------------------------------------------
# Cause annotation
# ---------------------------------------------------------------------------


def _build_bus_adjacency(intermediate_branches: list[dict]) -> dict[int, set[int]]:
    """Build an adjacency dict from intermediate branch data.

    Args:
        intermediate_branches: Intermediate format branch records.

    Returns:
        Dict mapping bus number to set of neighboring bus numbers.
    """
    adj: dict[int, set[int]] = {}
    for b in intermediate_branches:
        fb = b["from_bus"]
        tb = b["to_bus"]
        if fb not in adj:
            adj[fb] = set()
        if tb not in adj:
            adj[tb] = set()
        adj[fb].add(tb)
        adj[tb].add(fb)
    return adj


def _buses_within_n_hops(
    start: int,
    adjacency: dict[int, set[int]],
    max_hops: int,
) -> set[int]:
    """Find all buses within N topological hops of the start bus.

    Args:
        start: Starting bus number.
        adjacency: Adjacency dict.
        max_hops: Maximum number of hops.

    Returns:
        Set of bus numbers within max_hops (including the start bus).
    """
    visited: set[int] = {start}
    frontier: set[int] = {start}
    for _ in range(max_hops):
        next_frontier: set[int] = set()
        for bus in frontier:
            for neighbor in adjacency.get(bus, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.add(neighbor)
        frontier = next_frontier
        if not frontier:
            break
    return visited


def annotate_bus_causes(
    bus_deviations: list[BusDeviation],
    slack_bus: int,
    bus_adjacency: dict[int, set[int]],
) -> list[BusDeviation]:
    """Annotate each bus deviation with probable cause categories.

    Applies heuristics:
    - low_voltage: VM_acpf < 0.95
    - high_voltage: VM_acpf > 1.05
    - slack_bus_vicinity: bus is within 2 hops of the slack bus in bus_adjacency

    Args:
        bus_deviations: List of BusDeviation records (causes field empty).
        slack_bus: Slack bus number from the ACPF summary.
        bus_adjacency: Adjacency dict (bus -> set of neighbor buses) from
            the intermediate format branch table.

    Returns:
        New list of BusDeviation records with causes populated.
    """
    slack_vicinity = _buses_within_n_hops(slack_bus, bus_adjacency, 2)

    result: list[BusDeviation] = []
    for bd in bus_deviations:
        causes: list[DeviationCause] = []

        if bd.VM_acpf_pu < 0.95:
            causes.append(DeviationCause.LOW_VOLTAGE)
        if bd.VM_acpf_pu > 1.05:
            causes.append(DeviationCause.HIGH_VOLTAGE)
        if bd.bus in slack_vicinity:
            causes.append(DeviationCause.SLACK_BUS_VICINITY)

        if not causes:
            causes.append(DeviationCause.UNCATEGORIZED)

        result.append(
            BusDeviation(
                bus=bd.bus,
                VA_acpf_deg=bd.VA_acpf_deg,
                VA_dcpf_deg=bd.VA_dcpf_deg,
                delta_VA_deg=bd.delta_VA_deg,
                abs_delta_VA_deg=bd.abs_delta_VA_deg,
                VM_acpf_pu=bd.VM_acpf_pu,
                base_kv=bd.base_kv,
                area=bd.area,
                causes=causes,
            )
        )
    return result


def annotate_branch_causes(
    branch_deviations: list[BranchDeviation],
    acpf_buses: list[dict],
    intermediate_branches: list[dict],
) -> list[BranchDeviation]:
    """Annotate each branch deviation with probable cause categories.

    Applies heuristics (in priority order):
    - phase_shifter: shift_deg != 0
    - high_reactance: x_pu > 0.5
    - heavy_loading: |P_from_acpf| > 0.8 * rate_a (if rate_a available)
    - low_voltage: VM at either end-bus < 0.95
    - high_voltage: VM at either end-bus > 1.05
    - transformer_tap: is_transformer and tap_ratio != 1.0

    Args:
        branch_deviations: List of BranchDeviation records (causes field empty).
        acpf_buses: ACPF bus records (for VM lookup by bus number).
        intermediate_branches: Intermediate format branch data (for rate_a lookup).

    Returns:
        New list of BranchDeviation records with causes populated.
    """
    vm_map: dict[int, float] = {b["bus"]: b.get("VM", 1.0) for b in acpf_buses}

    # Build rate_a lookup with normalized keys
    rate_a_map: dict[tuple[int, int, str], float | None] = {}
    for b in intermediate_branches:
        nf, nt, nc, _ = _normalize_branch_key(b["from_bus"], b["to_bus"], b["ckt"])
        rate_a_map[(nf, nt, nc)] = b.get("rate_a_mw")

    result: list[BranchDeviation] = []
    for bd in branch_deviations:
        causes: list[DeviationCause] = []

        # Phase shifter
        if bd.shift_deg != 0.0:
            causes.append(DeviationCause.PHASE_SHIFTER)

        # High reactance
        if bd.x_pu > 0.5:
            causes.append(DeviationCause.HIGH_REACTANCE)

        # Heavy loading
        nf, nt, nc, _ = _normalize_branch_key(bd.from_bus, bd.to_bus, bd.ckt)
        rate_a = rate_a_map.get((nf, nt, nc))
        if rate_a is not None and rate_a > 0:
            if abs(bd.P_from_acpf_MW) > 0.8 * rate_a:
                causes.append(DeviationCause.HEAVY_LOADING)

        # Low/high voltage at either end-bus
        vm_from = vm_map.get(bd.from_bus, 1.0)
        vm_to = vm_map.get(bd.to_bus, 1.0)
        if vm_from < 0.95 or vm_to < 0.95:
            causes.append(DeviationCause.LOW_VOLTAGE)
        if vm_from > 1.05 or vm_to > 1.05:
            causes.append(DeviationCause.HIGH_VOLTAGE)

        # Transformer tap
        if bd.is_transformer and bd.tap_ratio != 1.0:
            causes.append(DeviationCause.TRANSFORMER_TAP)

        if not causes:
            causes.append(DeviationCause.UNCATEGORIZED)

        result.append(
            BranchDeviation(
                from_bus=bd.from_bus,
                to_bus=bd.to_bus,
                ckt=bd.ckt,
                P_from_acpf_MW=bd.P_from_acpf_MW,
                P_flow_dcpf_MW=bd.P_flow_dcpf_MW,
                delta_P_MW=bd.delta_P_MW,
                abs_delta_P_MW=bd.abs_delta_P_MW,
                delta_P_pct=bd.delta_P_pct,
                abs_delta_P_pct=bd.abs_delta_P_pct,
                x_pu=bd.x_pu,
                tap_ratio=bd.tap_ratio,
                shift_deg=bd.shift_deg,
                is_transformer=bd.is_transformer,
                causes=causes,
            )
        )
    return result


# ---------------------------------------------------------------------------
# Worst-case extraction
# ---------------------------------------------------------------------------


def extract_worst_buses(
    bus_deviations: list[BusDeviation],
    count: int = WORST_CASE_COUNT,
) -> list[BusDeviation]:
    """Return the top N buses by absolute angle deviation, descending.

    Args:
        bus_deviations: All bus deviations (with causes annotated).
        count: Number of worst-case buses to return.

    Returns:
        List of up to ``count`` BusDeviation records, sorted by
        abs_delta_VA_deg descending.
    """
    sorted_devs = sorted(bus_deviations, key=lambda d: d.abs_delta_VA_deg, reverse=True)
    return sorted_devs[:count]


def extract_worst_branches(
    branch_deviations: list[BranchDeviation],
    count: int = WORST_CASE_COUNT,
) -> list[BranchDeviation]:
    """Return the top N branches by absolute percentage flow deviation, descending.

    Only considers branches with non-null abs_delta_P_pct (i.e., those
    above the near-zero flow threshold).

    Args:
        branch_deviations: All branch deviations (with causes annotated).
        count: Number of worst-case branches to return.

    Returns:
        List of up to ``count`` BranchDeviation records, sorted by
        abs_delta_P_pct descending.
    """
    eligible = [bd for bd in branch_deviations if bd.abs_delta_P_pct is not None]
    sorted_devs = sorted(
        eligible,
        key=lambda d: d.abs_delta_P_pct if d.abs_delta_P_pct is not None else 0.0,
        reverse=True,
    )
    return sorted_devs[:count]


# ---------------------------------------------------------------------------
# Report writing
# ---------------------------------------------------------------------------


def _stats_to_dict(stats: AggregateStats) -> dict:
    """Convert AggregateStats to a JSON-serializable dict."""
    return {
        "mean": round(stats.mean, 6),
        "median": round(stats.median, 6),
        "std": round(stats.std, 6),
        "min": round(stats.min, 6),
        "max": round(stats.max, 6),
        "p05": round(stats.p05, 6),
        "p95": round(stats.p95, 6),
    }


def _compliance_to_dict(
    comp: ComplianceFractions,
    label_fmt: str,
) -> dict:
    """Convert ComplianceFractions to a JSON dict with threshold-based keys.

    Args:
        comp: Compliance fractions.
        label_fmt: Format string for keys, e.g. "pct_within_{}_deg".
            The ``{}`` is replaced with the threshold value formatted
            with underscores for decimals (e.g., 0.5 -> "0_5").

    Returns:
        Dict mapping threshold label to percentage (0-100).
    """
    result: dict[str, float] = {}
    for threshold, fraction in zip(comp.thresholds, comp.fractions):
        label = label_fmt.format(str(threshold).replace(".", "_"))
        result[label] = round(fraction * 100.0, 4)
    return result


def write_characterization_json(
    result: CharacterizationResult,
    output_path: Path,
) -> None:
    """Write the characterization report as JSON.

    Serializes the CharacterizationResult into the JSON schema defined
    in the Data Structures section.

    Args:
        result: Complete characterization result.
        output_path: Full path to the output JSON file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build angle deviation section
    angle_dev = {
        "unit": "degrees",
        "count": result.angle_stats_absolute.count,
        "signed": _stats_to_dict(result.angle_stats_signed),
        "absolute": _stats_to_dict(result.angle_stats_absolute),
        "compliance": _compliance_to_dict(result.angle_compliance, "pct_within_{}_deg"),
    }

    # Build flow deviation MW section
    flow_mw = {
        "unit": "MW",
        "count": result.flow_mw_stats_absolute.count,
        "signed": _stats_to_dict(result.flow_mw_stats_signed),
        "absolute": _stats_to_dict(result.flow_mw_stats_absolute),
    }

    # Count near-zero flow branches
    near_zero_count = sum(1 for bd in result.branch_deviations if bd.abs_delta_P_pct is None)

    # Build flow deviation pct section
    flow_pct = {
        "unit": "percent",
        "count": result.flow_pct_stats_absolute.count,
        "excluded_near_zero_flow": near_zero_count,
        "near_zero_flow_threshold_mw": NEAR_ZERO_FLOW_THRESHOLD_MW,
        "signed": _stats_to_dict(result.flow_pct_stats_signed),
        "absolute": _stats_to_dict(result.flow_pct_stats_absolute),
        "compliance": _compliance_to_dict(result.flow_pct_compliance, "pct_within_{}_pct"),
    }

    # Build worst buses
    worst_buses = []
    for bd in result.worst_buses:
        worst_buses.append(
            {
                "bus": bd.bus,
                "abs_delta_VA_deg": round(bd.abs_delta_VA_deg, 6),
                "VA_acpf_deg": round(bd.VA_acpf_deg, 6),
                "VA_dcpf_deg": round(bd.VA_dcpf_deg, 6),
                "VM_acpf_pu": round(bd.VM_acpf_pu, 6),
                "base_kv": round(bd.base_kv, 2),
                "area": bd.area,
                "primary_cause": bd.causes[0].value if bd.causes else "uncategorized",
                "all_causes": [c.value for c in bd.causes],
            }
        )

    # Build worst branches
    worst_branches = []
    for bd in result.worst_branches:
        worst_branches.append(
            {
                "from_bus": bd.from_bus,
                "to_bus": bd.to_bus,
                "ckt": bd.ckt,
                "abs_delta_P_pct": (
                    round(bd.abs_delta_P_pct, 6) if bd.abs_delta_P_pct is not None else None
                ),
                "abs_delta_P_MW": round(bd.abs_delta_P_MW, 6),
                "P_from_acpf_MW": round(bd.P_from_acpf_MW, 6),
                "P_flow_dcpf_MW": round(bd.P_flow_dcpf_MW, 6),
                "x_pu": round(bd.x_pu, 6),
                "tap_ratio": round(bd.tap_ratio, 6),
                "shift_deg": round(bd.shift_deg, 6),
                "is_transformer": bd.is_transformer,
                "primary_cause": bd.causes[0].value if bd.causes else "uncategorized",
                "all_causes": [c.value for c in bd.causes],
            }
        )

    data = {
        "metadata": result.metadata,
        "join_summary": result.join_summary,
        "system_level": {
            k: round(v, 6) if isinstance(v, float) else v for k, v in result.system_level.items()
        },
        "angle_deviation": angle_dev,
        "flow_deviation_mw": flow_mw,
        "flow_deviation_pct": flow_pct,
        "expected_range_checks": result.expected_range_checks,
        "worst_buses": worst_buses,
        "worst_branches": worst_branches,
        "warnings": result.warnings,
    }

    output_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_characterization_md(
    result: CharacterizationResult,
    output_path: Path,
) -> None:
    """Write the characterization report as human-readable markdown.

    Produces the markdown structure: Summary, System-Level Comparison,
    Angle Deviation Distribution, Flow Deviation Distribution,
    Expected Range Checks, Worst-Case Buses, Worst-Case Branches,
    Methodology Notes.

    Args:
        result: Complete characterization result.
        output_path: Full path to the output markdown file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# DCPF-vs-ACPF Characterization Report\n")

    # Summary
    lines.append("## Summary\n")
    js = result.join_summary
    lines.append(
        f"Compared {js.get('buses_matched', 0)} matched buses and "
        f"{js.get('branches_matched', 0)} matched branches. "
    )

    angle_check = result.expected_range_checks.get("angle_95pct_within_3deg", {})
    flow_check = result.expected_range_checks.get("flow_90pct_within_10pct", {})
    angle_met = angle_check.get("met", False)
    flow_met = flow_check.get("met", False)

    lines.append(
        f"Angle expected-range check (>95% within 3 deg): "
        f"{'PASSED' if angle_met else 'WARNING'}. "
        f"Flow expected-range check (>90% within 10%): "
        f"{'PASSED' if flow_met else 'WARNING'}.\n"
    )

    # System-Level Comparison
    lines.append("## System-Level Comparison\n")
    sl = result.system_level
    lines.append("| Metric | ACPF | DCPF |")
    lines.append("|--------|------|------|")
    lines.append(
        f"| Total Generation (MW) | {sl.get('acpf_total_gen_mw', 'N/A'):.2f} | "
        f"{sl.get('dcpf_total_gen_mw', 'N/A'):.2f} |"
    )
    lines.append(
        f"| Total Load (MW) | {sl.get('acpf_total_load_mw', 'N/A'):.2f} | "
        f"{sl.get('dcpf_total_load_mw', 'N/A'):.2f} |"
    )
    lines.append(
        f"| Total Losses (MW) | {sl.get('acpf_total_loss_mw', 'N/A'):.2f} | N/A (lossless) |"
    )
    lines.append(f"| Loss % of Generation | {sl.get('acpf_loss_pct_of_gen', 0):.2f}% | N/A |")
    lines.append("")

    # Angle Deviation Distribution
    lines.append("## Angle Deviation Distribution\n")
    lines.append("### Aggregate Statistics (absolute)\n")
    _append_stats_table(lines, result.angle_stats_absolute, "degrees")
    lines.append("### Compliance Fractions\n")
    _append_compliance_table(lines, result.angle_compliance, "deg")

    # Flow Deviation Distribution
    lines.append("## Flow Deviation Distribution\n")
    lines.append("### Aggregate Statistics - MW (absolute)\n")
    _append_stats_table(lines, result.flow_mw_stats_absolute, "MW")
    lines.append("### Aggregate Statistics - Percent (absolute)\n")
    _append_stats_table(lines, result.flow_pct_stats_absolute, "%")
    lines.append("### Compliance Fractions\n")
    _append_compliance_table(lines, result.flow_pct_compliance, "%")

    # Expected Range Checks
    lines.append("## Expected Range Checks\n")
    for name, check in result.expected_range_checks.items():
        status = "PASSED" if check.get("met", False) else "WARNING"
        actual = check.get("actual_pct", 0)
        lines.append(f"- **{name}**: {status} (actual: {actual:.2f}%)")
    lines.append("")

    # Worst-Case Buses
    lines.append("## Worst-Case Buses (Top 50 by angle deviation)\n")
    lines.append("| Bus | abs_dVA (deg) | VA_acpf | VA_dcpf | VM_acpf | kV | Cause |")
    lines.append("|-----|---------------|---------|---------|---------|-----|-------|")
    for bd in result.worst_buses:
        cause = bd.causes[0].value if bd.causes else "uncategorized"
        lines.append(
            f"| {bd.bus} | {bd.abs_delta_VA_deg:.4f} | {bd.VA_acpf_deg:.4f} | "
            f"{bd.VA_dcpf_deg:.4f} | {bd.VM_acpf_pu:.4f} | {bd.base_kv:.1f} | {cause} |"
        )
    lines.append("")

    # Worst-Case Branches
    lines.append("## Worst-Case Branches (Top 50 by percentage flow deviation)\n")
    lines.append("| From | To | Ckt | abs_dP% | abs_dP_MW | P_acpf | P_dcpf | Cause |")
    lines.append("|------|-----|-----|---------|-----------|--------|--------|-------|")
    for bd in result.worst_branches:
        cause = bd.causes[0].value if bd.causes else "uncategorized"
        pct_str = f"{bd.abs_delta_P_pct:.2f}" if bd.abs_delta_P_pct is not None else "N/A"
        lines.append(
            f"| {bd.from_bus} | {bd.to_bus} | {bd.ckt} | {pct_str} | "
            f"{bd.abs_delta_P_MW:.4f} | {bd.P_from_acpf_MW:.4f} | "
            f"{bd.P_flow_dcpf_MW:.4f} | {cause} |"
        )
    lines.append("")

    # Methodology Notes
    lines.append("## Methodology Notes\n")
    lines.append(
        "- **Join strategy**: Inner join on bus number (buses) and "
        "(from_bus, to_bus, ckt) normalized to (min, max, ckt) for branches.\n"
        "- **Near-zero flow exclusion**: Branches with |P_from_acpf| <= "
        f"{NEAR_ZERO_FLOW_THRESHOLD_MW} MW excluded from percentage metrics.\n"
        "- **Cause annotation**: Rule-based heuristics applied in priority order: "
        "phase_shifter, high_reactance, heavy_loading, low_voltage, high_voltage, "
        "transformer_tap, slack_bus_vicinity, uncategorized.\n"
    )

    output_path.write_text("\n".join(lines), encoding="utf-8")


def _append_stats_table(lines: list[str], stats: AggregateStats, unit: str) -> None:
    """Append a statistics table to the markdown lines."""
    lines.append(f"| Statistic | Value ({unit}) |")
    lines.append("|-----------|---------------|")
    lines.append(f"| Count | {stats.count} |")
    lines.append(f"| Mean | {stats.mean:.6f} |")
    lines.append(f"| Median | {stats.median:.6f} |")
    lines.append(f"| Std Dev | {stats.std:.6f} |")
    lines.append(f"| P05 | {stats.p05:.6f} |")
    lines.append(f"| P95 | {stats.p95:.6f} |")
    lines.append(f"| Max | {stats.max:.6f} |")
    lines.append("")


def _append_compliance_table(lines: list[str], comp: ComplianceFractions, unit: str) -> None:
    """Append a compliance fractions table to the markdown lines."""
    lines.append(f"| Threshold ({unit}) | % Within |")
    lines.append("|-------------------|----------|")
    for threshold, fraction in zip(comp.thresholds, comp.fractions):
        lines.append(f"| {threshold} | {fraction * 100:.2f}% |")
    lines.append("")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def build_characterization(
    acpf_dir: Path,
    dcpf_dir: Path,
    intermediate_dir: Path,
    output_dir: Path,
) -> Path:
    """Top-level orchestrator for DCPF-vs-ACPF characterization.

    Steps:
    1. Load ACPF and DCPF bus and branch CSVs.
    2. Load ACPF and DCPF summary JSONs.
    3. Load intermediate format bus and branch data for cause annotations.
    4. Join buses on bus number; join branches on (from_bus, to_bus, ckt).
    5. Compute per-bus angle deviations and per-branch flow deviations.
    6. Compute aggregate statistics and compliance fractions.
    7. Check expected-range thresholds; log warnings if not met.
    8. Annotate worst-case elements with probable causes.
    9. Extract top-50 worst buses and branches.
    10. Build CharacterizationResult.
    11. Write JSON and markdown reports to output_dir.

    Args:
        acpf_dir: Directory containing ACPF reference files
            (``buses_acpf.csv``, ``branches_acpf.csv``, ``summary_acpf.json``).
        dcpf_dir: Directory containing DCPF reference files
            (``buses_dcpf.csv``, ``branches_dcpf.csv``, ``summary_dcpf.json``).
        intermediate_dir: Directory containing intermediate format CSVs
            from the canonical parser.
        output_dir: Output directory for characterization report files.
            Created if it does not exist.

    Returns:
        Path to the output directory containing the JSON and markdown reports.

    Raises:
        FileNotFoundError: If any required input file is missing.
        ValueError: If join produces zero matched buses or branches.
    """
    # 1. Load data
    acpf_buses = load_acpf_buses(acpf_dir / "buses_acpf.csv")
    dcpf_buses = load_dcpf_buses(dcpf_dir / "buses_dcpf.csv")
    acpf_branches = load_acpf_branches(acpf_dir / "branches_acpf.csv")
    dcpf_branches = load_dcpf_branches(dcpf_dir / "branches_dcpf.csv")

    # 2. Load summaries
    acpf_summary = load_summary_json(acpf_dir / "summary_acpf.json")
    dcpf_summary = load_summary_json(dcpf_dir / "summary_dcpf.json")

    # 3. Load intermediate data (gracefully handle missing)
    try:
        intermediate_buses = load_intermediate_buses(intermediate_dir)
    except (FileNotFoundError, ValueError):
        logger.warning("Could not load intermediate bus data; using empty list.")
        intermediate_buses = []

    try:
        intermediate_branches = load_intermediate_branches(intermediate_dir)
    except (FileNotFoundError, ValueError):
        logger.warning("Could not load intermediate branch data; using empty list.")
        intermediate_branches = []

    # 4. Join
    matched_buses, bus_join_summary = join_buses(acpf_buses, dcpf_buses)
    matched_branches, branch_join_summary = join_branches(acpf_branches, dcpf_branches)

    if not matched_buses:
        raise ValueError("Join produced zero matched buses.")
    if not matched_branches:
        raise ValueError("Join produced zero matched branches.")

    # Check for all-zero DCPF angles
    all_dcpf_angles = [m["VA_dcpf"] for m in matched_buses]
    if all(a == 0.0 for a in all_dcpf_angles):
        raise ValueError("All DCPF angles are 0.0, indicating a solver failure or empty network.")

    # Log unmatched warnings
    warnings: list[str] = []
    total_acpf_buses = bus_join_summary["buses_in_acpf"]
    unmatched_buses = bus_join_summary["buses_acpf_only"] + bus_join_summary["buses_dcpf_only"]
    if total_acpf_buses > 0 and unmatched_buses / total_acpf_buses > 0.01:
        msg = (
            f"Unmatched bus count ({unmatched_buses}) exceeds 1% of ACPF buses "
            f"({total_acpf_buses}). ACPF-only: {bus_join_summary['buses_acpf_only']}, "
            f"DCPF-only: {bus_join_summary['buses_dcpf_only']}."
        )
        warnings.append(msg)
        logger.warning(msg)

    # Merge join summaries
    join_summary = {**bus_join_summary, **branch_join_summary}

    # 5. Compute deviations
    bus_devs = compute_bus_deviations(matched_buses, intermediate_buses)
    branch_devs = compute_branch_deviations(matched_branches, intermediate_branches)

    # 6. Aggregate statistics
    signed_angles = [bd.delta_VA_deg for bd in bus_devs]
    abs_angles = [bd.abs_delta_VA_deg for bd in bus_devs]
    angle_stats_signed = compute_aggregate_stats(signed_angles)
    angle_stats_absolute = compute_aggregate_stats(abs_angles)
    angle_compliance = compute_compliance_fractions(abs_angles, ANGLE_COMPLIANCE_THRESHOLDS_DEG)

    signed_mw = [bd.delta_P_MW for bd in branch_devs]
    abs_mw = [bd.abs_delta_P_MW for bd in branch_devs]
    flow_mw_stats_signed = compute_aggregate_stats(signed_mw)
    flow_mw_stats_absolute = compute_aggregate_stats(abs_mw)

    # Percentage stats only for non-near-zero branches
    signed_pct = [bd.delta_P_pct for bd in branch_devs if bd.delta_P_pct is not None]
    abs_pct = [bd.abs_delta_P_pct for bd in branch_devs if bd.abs_delta_P_pct is not None]

    if signed_pct:
        flow_pct_stats_signed = compute_aggregate_stats(signed_pct)
    else:
        flow_pct_stats_signed = AggregateStats(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    if abs_pct:
        flow_pct_stats_absolute = compute_aggregate_stats(abs_pct)
    else:
        flow_pct_stats_absolute = AggregateStats(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    flow_pct_compliance = compute_compliance_fractions(abs_pct, FLOW_COMPLIANCE_THRESHOLDS_PCT)

    # 7. Expected-range checks
    angle_3deg_compliance = (
        angle_compliance.fractions[ANGLE_COMPLIANCE_THRESHOLDS_DEG.index(3.0)] * 100.0
    )
    angle_check_met = angle_3deg_compliance >= EXPECTED_ANGLE_COMPLIANCE_PCT

    if abs_pct:
        flow_10pct_compliance = (
            flow_pct_compliance.fractions[FLOW_COMPLIANCE_THRESHOLDS_PCT.index(10.0)] * 100.0
        )
    else:
        flow_10pct_compliance = 0.0
    flow_check_met = flow_10pct_compliance >= EXPECTED_FLOW_COMPLIANCE_PCT

    expected_range_checks = {
        "angle_95pct_within_3deg": {
            "threshold_pct": EXPECTED_ANGLE_COMPLIANCE_PCT,
            "threshold_deg": EXPECTED_ANGLE_THRESHOLD_DEG,
            "actual_pct": round(angle_3deg_compliance, 4),
            "met": angle_check_met,
        },
        "flow_90pct_within_10pct": {
            "threshold_pct": EXPECTED_FLOW_COMPLIANCE_PCT,
            "threshold_flow_pct": EXPECTED_FLOW_THRESHOLD_PCT,
            "actual_pct": round(flow_10pct_compliance, 4),
            "met": flow_check_met,
        },
    }

    if not angle_check_met:
        msg = (
            f"Expected >95% of buses within 3 degrees, but only "
            f"{angle_3deg_compliance:.2f}% met the threshold."
        )
        warnings.append(msg)
        logger.warning(msg)

    if not flow_check_met:
        msg = (
            f"Expected >90% of branches within 10%, but only "
            f"{flow_10pct_compliance:.2f}% met the threshold."
        )
        warnings.append(msg)
        logger.warning(msg)

    # 8. Annotate causes
    bus_adjacency = _build_bus_adjacency(intermediate_branches)
    slack_bus = _extract_slack_bus(acpf_summary, dcpf_summary)
    bus_devs = annotate_bus_causes(bus_devs, slack_bus, bus_adjacency)
    branch_devs = annotate_branch_causes(branch_devs, acpf_buses, intermediate_branches)

    # 9. Extract worst-case
    worst_buses = extract_worst_buses(bus_devs)
    worst_branches = extract_worst_branches(branch_devs)

    # 10. System-level comparison
    system_level = _build_system_level(acpf_summary, dcpf_summary)

    # Build metadata
    metadata = {
        "acpf_summary_path": str(acpf_dir / "summary_acpf.json"),
        "dcpf_summary_path": str(dcpf_dir / "summary_dcpf.json"),
        "acpf_buses_path": str(acpf_dir / "buses_acpf.csv"),
        "dcpf_buses_path": str(dcpf_dir / "buses_dcpf.csv"),
        "acpf_branches_path": str(acpf_dir / "branches_acpf.csv"),
        "dcpf_branches_path": str(dcpf_dir / "branches_dcpf.csv"),
        "intermediate_dir": str(intermediate_dir),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # 10. Build result
    char_result = CharacterizationResult(
        bus_deviations=bus_devs,
        branch_deviations=branch_devs,
        angle_stats_signed=angle_stats_signed,
        angle_stats_absolute=angle_stats_absolute,
        angle_compliance=angle_compliance,
        flow_mw_stats_signed=flow_mw_stats_signed,
        flow_mw_stats_absolute=flow_mw_stats_absolute,
        flow_pct_stats_signed=flow_pct_stats_signed,
        flow_pct_stats_absolute=flow_pct_stats_absolute,
        flow_pct_compliance=flow_pct_compliance,
        join_summary=join_summary,
        system_level=system_level,
        expected_range_checks=expected_range_checks,
        worst_buses=worst_buses,
        worst_branches=worst_branches,
        warnings=warnings,
        metadata=metadata,
    )

    # 11. Write reports
    output_dir.mkdir(parents=True, exist_ok=True)
    write_characterization_json(char_result, output_dir / "dcpf_vs_acpf_characterization.json")
    write_characterization_md(char_result, output_dir / "dcpf_vs_acpf_characterization.md")

    logger.info("Characterization reports written to %s", output_dir)
    return output_dir


def _extract_slack_bus(acpf_summary: dict, dcpf_summary: dict) -> int:
    """Extract the slack bus number from the ACPF or DCPF summary.

    Args:
        acpf_summary: Parsed ACPF summary JSON.
        dcpf_summary: Parsed DCPF summary JSON.

    Returns:
        Slack bus number.
    """
    # Try ACPF summary first
    sys_summary = acpf_summary.get("system_summary", {})
    slack = sys_summary.get("slack_bus")
    if slack is not None:
        return int(slack)

    # Try DCPF summary
    settings = dcpf_summary.get("settings", {})
    slack = settings.get("slack_bus")
    if slack is not None:
        return int(slack)

    # Default to bus 1
    logger.warning("Could not determine slack bus from summaries; defaulting to bus 1.")
    return 1


def _build_system_level(acpf_summary: dict, dcpf_summary: dict) -> dict[str, float]:
    """Build system-level comparison dict from summaries.

    Args:
        acpf_summary: Parsed ACPF summary JSON.
        dcpf_summary: Parsed DCPF summary JSON.

    Returns:
        Dict with system-level comparison values.
    """
    acpf_sys = acpf_summary.get("system_summary", {})
    dcpf_power = dcpf_summary.get("power_summary", {})

    acpf_gen = float(acpf_sys.get("total_gen_mw", 0))
    acpf_load = float(acpf_sys.get("total_load_mw", 0))
    acpf_loss = float(acpf_sys.get("total_loss_mw", 0))
    dcpf_gen = float(dcpf_power.get("total_generation_mw", 0))
    dcpf_load = float(dcpf_power.get("total_load_mw", 0))

    acpf_slack = int(acpf_sys.get("slack_bus", 0))
    dcpf_slack = int(dcpf_summary.get("settings", {}).get("slack_bus", 0))

    loss_pct = (acpf_loss / acpf_gen * 100.0) if acpf_gen > 0 else 0.0

    return {
        "acpf_total_gen_mw": acpf_gen,
        "dcpf_total_gen_mw": dcpf_gen,
        "acpf_total_load_mw": acpf_load,
        "dcpf_total_load_mw": dcpf_load,
        "acpf_total_loss_mw": acpf_loss,
        "acpf_loss_pct_of_gen": loss_pct,
        "acpf_slack_bus": float(acpf_slack),
        "dcpf_slack_bus": float(dcpf_slack),
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for DCPF-vs-ACPF characterization.

    Usage::

        python -m data.fnm.scripts.dcpf_acpf_characterization \\
            --acpf-dir data/fnm/reference/acpf/ \\
            --dcpf-dir data/fnm/reference/dcpf/ \\
            --intermediate-dir data/fnm/intermediate/canonical/ \\
            [-o data/fnm/reference/]

    Exit codes:
    - 0: Characterization report produced successfully.
    - 1: Input error (missing files, zero matches after join).
    - 2: Unexpected computation error.

    Args:
        argv: Command-line arguments. If None, reads from sys.argv[1:].
    """
    parser = argparse.ArgumentParser(
        description="Compare DCPF and ACPF reference solutions to characterize "
        "DC approximation quality."
    )
    parser.add_argument(
        "--acpf-dir",
        type=Path,
        required=True,
        help="Directory containing ACPF reference files.",
    )
    parser.add_argument(
        "--dcpf-dir",
        type=Path,
        required=True,
        help="Directory containing DCPF reference files.",
    )
    parser.add_argument(
        "--intermediate-dir",
        type=Path,
        required=True,
        help="Directory containing intermediate format CSVs.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: data/fnm/reference/).",
    )

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    output_dir = args.output_dir or Path("data/fnm/reference")

    try:
        result_dir = build_characterization(
            acpf_dir=args.acpf_dir,
            dcpf_dir=args.dcpf_dir,
            intermediate_dir=args.intermediate_dir,
            output_dir=output_dir,
        )
        print(f"Characterization reports written to: {result_dir}")
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
