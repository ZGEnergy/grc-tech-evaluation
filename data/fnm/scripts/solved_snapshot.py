"""Solved-snapshot confirmation for FNM Annual S01 RAW file.

Analyzes parsed bus and generator CSV data to determine whether the FNM file
contains a converged AC power flow (ACPF) solution or flat-start initial
conditions. Classification is based on three statistical indicators: voltage
magnitude (VM) distribution, voltage angle (VA) spread, and generator reactive
power (Qg) population.

Produces both JSON (machine-readable) and markdown (human-readable) output files
containing the classification, supporting statistics, and Phase 3 implications.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants / Thresholds
# ---------------------------------------------------------------------------

FLOAT_TOLERANCE: float = 1e-10

# Voltage magnitude thresholds
VM_STD_SOLVED_THRESHOLD: float = 0.01
VM_PCT_EXACT_SOLVED_THRESHOLD: float = 50.0
VM_STD_FLAT_THRESHOLD: float = 0.001
VM_PCT_EXACT_FLAT_THRESHOLD: float = 95.0

# Voltage angle thresholds
VA_STD_SOLVED_THRESHOLD: float = 0.5
VA_PCT_EXACT_SOLVED_THRESHOLD: float = 50.0
VA_STD_FLAT_THRESHOLD: float = 0.01
VA_PCT_EXACT_FLAT_THRESHOLD: float = 95.0

# Generator Qg thresholds
QG_PCT_NONZERO_SOLVED_THRESHOLD: float = 50.0
QG_PCT_NONZERO_FLAT_THRESHOLD: float = 5.0

# MATPOWER bus matrix column indices (standard 13-column format, no header)
_MPC_BUS_COL_BUS_I: int = 0
_MPC_BUS_COL_TYPE: int = 1
_MPC_BUS_COL_VM: int = 7
_MPC_BUS_COL_VA: int = 8

# MATPOWER gen matrix column indices (no header)
_MPC_GEN_COL_BUS: int = 0
_MPC_GEN_COL_QG: int = 2

# PSS/E bus type for isolated buses
_ISOLATED_BUS_TYPE: int = 4


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SnapshotClassification(Enum):
    """Overall classification of the solved-snapshot analysis."""

    SOLVED = "solved"
    FLAT_START = "flat_start"
    INDETERMINATE = "indeterminate"


class IndicatorSignal(Enum):
    """Sub-classification for an individual indicator."""

    SOLVED_SIGNAL = "solved_signal"
    FLAT_SIGNAL = "flat_signal"
    AMBIGUOUS = "ambiguous"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DistributionStats:
    """Descriptive statistics for a distribution of values.

    Attributes:
        count: Number of values analyzed.
        mean: Arithmetic mean.
        std: Population standard deviation.
        min: Minimum value.
        max: Maximum value.
        pct_exact_reference: Percentage of values exactly equal to the
            reference value (within FLOAT_TOLERANCE).
    """

    count: int
    mean: float
    std: float
    min: float
    max: float
    pct_exact_reference: float


@dataclass(frozen=True)
class GeneratorQgStats:
    """Statistics for generator reactive power output.

    Attributes:
        total_generators: Total number of generators analyzed.
        generators_with_nonzero_qg: Count with Qg != 0 (beyond tolerance).
        pct_nonzero_qg: Percentage with non-zero Qg.
        mean_abs_qg: Mean of absolute Qg values.
        min_qg: Minimum Qg value.
        max_qg: Maximum Qg value.
    """

    total_generators: int
    generators_with_nonzero_qg: int
    pct_nonzero_qg: float
    mean_abs_qg: float
    min_qg: float
    max_qg: float


@dataclass(frozen=True)
class IndicatorResult:
    """Result of a single indicator classification.

    Attributes:
        name: Indicator name (e.g. "VM", "VA", "Qg").
        signal: The sub-classification for this indicator.
        rationale: Human-readable explanation of the classification.
    """

    name: str
    signal: IndicatorSignal
    rationale: str


@dataclass(frozen=True)
class ConfirmationMetadata:
    """Metadata about the confirmation analysis run.

    Attributes:
        bus_csv_path: Path to the bus CSV file analyzed.
        generator_csv_path: Path to the generator CSV file analyzed.
        canonical_parser: Name of the canonical parser that produced the CSVs.
        timestamp: ISO 8601 timestamp of the analysis.
        float_tolerance: Tolerance used for floating-point equality checks.
    """

    bus_csv_path: str = ""
    generator_csv_path: str = ""
    canonical_parser: str = ""
    timestamp: str = ""
    float_tolerance: float = FLOAT_TOLERANCE


@dataclass(frozen=True)
class SnapshotConfirmation:
    """Complete solved-snapshot confirmation result.

    Attributes:
        classification: Overall snapshot classification.
        vm_stats: Voltage magnitude distribution statistics.
        va_stats: Voltage angle distribution statistics.
        qg_stats: Generator reactive power statistics.
        vm_indicator: VM indicator classification result.
        va_indicator: VA indicator classification result.
        qg_indicator: Qg indicator classification result.
        phase3_implications: Text describing Phase 3 strategy implications.
        buses_analyzed: Number of non-isolated buses analyzed.
        buses_excluded_isolated: Number of isolated (IDE=4) buses excluded.
        metadata: Analysis metadata.
    """

    classification: SnapshotClassification
    vm_stats: DistributionStats
    va_stats: DistributionStats
    qg_stats: GeneratorQgStats
    vm_indicator: IndicatorResult
    va_indicator: IndicatorResult
    qg_indicator: IndicatorResult
    phase3_implications: str
    buses_analyzed: int
    buses_excluded_isolated: int
    metadata: ConfirmationMetadata


# ---------------------------------------------------------------------------
# CSV Detection Helpers
# ---------------------------------------------------------------------------


def _is_header_row(row: list[str]) -> bool:
    """Determine if a CSV row is a header (non-numeric first field).

    Args:
        row: A list of string values from a CSV row.

    Returns:
        True if the row appears to be a header rather than data.
    """
    if not row:
        return False
    try:
        float(row[0])
        return False
    except ValueError:
        return True


def _detect_column_index(headers: list[str], candidates: list[str]) -> int | None:
    """Find the index of the first matching header from a list of candidates.

    Args:
        headers: List of column header names (lowercased).
        candidates: Candidate column names to search for, in priority order.

    Returns:
        Column index if found, None otherwise.
    """
    lower_headers = [h.strip().lower() for h in headers]
    for candidate in candidates:
        if candidate.lower() in lower_headers:
            return lower_headers.index(candidate.lower())
    return None


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------


def load_bus_data(bus_csv_path: Path) -> tuple[list[float], list[float], int]:
    """Load parsed bus data and return VM, VA values excluding isolated buses.

    Supports both header-bearing CSVs (GridCal) and headerless CSVs (MATPOWER).
    Isolated buses (type/IDE = 4) are excluded from the returned lists.

    Args:
        bus_csv_path: Path to the bus CSV file.

    Returns:
        A tuple of (vm_values, va_values, isolated_count) where vm_values and
        va_values are lists of floats for non-isolated buses and isolated_count
        is the number of excluded isolated buses.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If the CSV has no usable data rows.
    """
    if not bus_csv_path.exists():
        raise FileNotFoundError(f"Bus CSV not found: {bus_csv_path}")

    vm_values: list[float] = []
    va_values: list[float] = []
    isolated_count: int = 0

    with open(bus_csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"Bus CSV is empty: {bus_csv_path}")

    # Detect header vs headerless
    first_row = rows[0]
    if _is_header_row(first_row):
        # Header-bearing CSV (e.g. GridCal)
        headers = first_row
        data_rows = rows[1:]
        type_idx = _detect_column_index(headers, ["type", "ide", "bus_type"])
        vm_idx = _detect_column_index(headers, ["vm", "vm_pu", "Vm"])
        va_idx = _detect_column_index(headers, ["va", "va_deg", "Va"])
        if vm_idx is None or va_idx is None:
            raise ValueError(
                f"Cannot find VM/VA columns in headers: {headers}. "
                "Expected columns named 'vm'/'va' or similar."
            )
    else:
        # Headerless CSV (MATPOWER format: 13-column bus matrix)
        data_rows = rows
        type_idx = _MPC_BUS_COL_TYPE
        vm_idx = _MPC_BUS_COL_VM
        va_idx = _MPC_BUS_COL_VA

    if not data_rows:
        raise ValueError(f"Bus CSV has no data rows: {bus_csv_path}")

    for row in data_rows:
        if not row or all(cell.strip() == "" for cell in row):
            continue

        # Check bus type for isolation
        if type_idx is not None and type_idx < len(row):
            try:
                bus_type = int(float(row[type_idx].strip()))
            except (ValueError, IndexError):
                bus_type = 0
            if bus_type == _ISOLATED_BUS_TYPE:
                isolated_count += 1
                continue

        try:
            vm = float(row[vm_idx].strip())
            va = float(row[va_idx].strip())
        except (ValueError, IndexError) as exc:
            raise ValueError(f"Cannot parse VM/VA from row: {row}") from exc

        vm_values.append(vm)
        va_values.append(va)

    if not vm_values:
        raise ValueError(f"No non-isolated bus data found in: {bus_csv_path}")

    return vm_values, va_values, isolated_count


def load_generator_data(gen_csv_path: Path, bus_csv_path: Path) -> list[float]:
    """Load parsed generator data and return Qg values.

    Excludes generators connected to isolated buses (type/IDE = 4) by
    cross-referencing with the bus CSV.

    Supports both header-bearing CSVs (GridCal) and headerless CSVs (MATPOWER).

    Args:
        gen_csv_path: Path to the generator CSV file.
        bus_csv_path: Path to the bus CSV file (for isolated bus filtering).

    Returns:
        List of Qg values for generators on non-isolated buses.

    Raises:
        FileNotFoundError: If either CSV file does not exist.
        ValueError: If the CSV has no usable data rows.
    """
    if not gen_csv_path.exists():
        raise FileNotFoundError(f"Generator CSV not found: {gen_csv_path}")

    # Build set of isolated bus IDs from bus CSV
    isolated_buses: set[int] = set()
    if bus_csv_path.exists():
        with open(bus_csv_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            bus_rows = list(reader)

        if bus_rows:
            first_row = bus_rows[0]
            if _is_header_row(first_row):
                headers = first_row
                bus_data = bus_rows[1:]
                bus_i_idx = _detect_column_index(headers, ["bus_i", "i", "bus_id", "bus"])
                type_idx = _detect_column_index(headers, ["type", "ide", "bus_type"])
            else:
                bus_data = bus_rows
                bus_i_idx = _MPC_BUS_COL_BUS_I
                type_idx = _MPC_BUS_COL_TYPE

            if bus_i_idx is not None and type_idx is not None:
                for row in bus_data:
                    if not row or all(c.strip() == "" for c in row):
                        continue
                    try:
                        bus_id = int(float(row[bus_i_idx].strip()))
                        bus_type = int(float(row[type_idx].strip()))
                    except (ValueError, IndexError):
                        continue
                    if bus_type == _ISOLATED_BUS_TYPE:
                        isolated_buses.add(bus_id)

    # Read generator CSV
    with open(gen_csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        gen_rows = list(reader)

    if not gen_rows:
        raise ValueError(f"Generator CSV is empty: {gen_csv_path}")

    first_row = gen_rows[0]
    if _is_header_row(first_row):
        headers = first_row
        data_rows = gen_rows[1:]
        qg_idx = _detect_column_index(headers, ["qg", "q", "Qg"])
        bus_idx = _detect_column_index(headers, ["bus", "bus_i", "i"])
    else:
        data_rows = gen_rows
        qg_idx = _MPC_GEN_COL_QG
        bus_idx = _MPC_GEN_COL_BUS

    if qg_idx is None:
        raise ValueError(f"Cannot find Qg column in generator CSV: {gen_csv_path}")

    qg_values: list[float] = []
    for row in data_rows:
        if not row or all(c.strip() == "" for c in row):
            continue

        # Filter out generators on isolated buses
        if isolated_buses and bus_idx is not None and bus_idx < len(row):
            try:
                gen_bus = int(float(row[bus_idx].strip()))
            except (ValueError, IndexError):
                gen_bus = -1
            if gen_bus in isolated_buses:
                continue

        try:
            qg = float(row[qg_idx].strip())
        except (ValueError, IndexError) as exc:
            raise ValueError(f"Cannot parse Qg from row: {row}") from exc
        qg_values.append(qg)

    if not qg_values:
        raise ValueError(f"No generator Qg data found in: {gen_csv_path}")

    return qg_values


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def compute_distribution_stats(values: list[float], reference_value: float) -> DistributionStats:
    """Compute descriptive statistics for a distribution of values.

    Args:
        values: List of numeric values to analyze.
        reference_value: Reference value for exact-match percentage
            (e.g. 1.0 for VM, 0.0 for VA).

    Returns:
        DistributionStats with computed metrics.

    Raises:
        ValueError: If values is empty.
    """
    if not values:
        raise ValueError("Cannot compute statistics on empty values list.")

    n = len(values)
    mean_val = statistics.mean(values)
    std_val = statistics.pstdev(values)
    min_val = min(values)
    max_val = max(values)

    exact_count = sum(1 for v in values if abs(v - reference_value) < FLOAT_TOLERANCE)
    pct_exact = (exact_count / n) * 100.0

    return DistributionStats(
        count=n,
        mean=mean_val,
        std=std_val,
        min=min_val,
        max=max_val,
        pct_exact_reference=pct_exact,
    )


def compute_qg_stats(qg_values: list[float]) -> GeneratorQgStats:
    """Compute generator reactive power statistics.

    Args:
        qg_values: List of Qg values.

    Returns:
        GeneratorQgStats with computed metrics.

    Raises:
        ValueError: If qg_values is empty.
    """
    if not qg_values:
        raise ValueError("Cannot compute Qg statistics on empty values list.")

    n = len(qg_values)
    nonzero_count = sum(1 for q in qg_values if abs(q) >= FLOAT_TOLERANCE)
    pct_nonzero = (nonzero_count / n) * 100.0
    mean_abs = statistics.mean(abs(q) for q in qg_values)
    min_qg = min(qg_values)
    max_qg = max(qg_values)

    return GeneratorQgStats(
        total_generators=n,
        generators_with_nonzero_qg=nonzero_count,
        pct_nonzero_qg=pct_nonzero,
        mean_abs_qg=mean_abs,
        min_qg=min_qg,
        max_qg=max_qg,
    )


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def classify_vm(stats: DistributionStats) -> IndicatorResult:
    """Classify the voltage magnitude indicator.

    Args:
        stats: VM distribution statistics.

    Returns:
        IndicatorResult with the VM sub-classification.
    """
    if (
        stats.std > VM_STD_SOLVED_THRESHOLD
        and stats.pct_exact_reference < VM_PCT_EXACT_SOLVED_THRESHOLD
    ):
        return IndicatorResult(
            name="VM",
            signal=IndicatorSignal.SOLVED_SIGNAL,
            rationale=(
                f"VM std={stats.std:.6f} > {VM_STD_SOLVED_THRESHOLD} and "
                f"{stats.pct_exact_reference:.1f}% exact 1.0 < "
                f"{VM_PCT_EXACT_SOLVED_THRESHOLD}%."
            ),
        )
    if (
        stats.std < VM_STD_FLAT_THRESHOLD
        and stats.pct_exact_reference > VM_PCT_EXACT_FLAT_THRESHOLD
    ):
        return IndicatorResult(
            name="VM",
            signal=IndicatorSignal.FLAT_SIGNAL,
            rationale=(
                f"VM std={stats.std:.6f} < {VM_STD_FLAT_THRESHOLD} and "
                f"{stats.pct_exact_reference:.1f}% exact 1.0 > "
                f"{VM_PCT_EXACT_FLAT_THRESHOLD}%."
            ),
        )
    return IndicatorResult(
        name="VM",
        signal=IndicatorSignal.AMBIGUOUS,
        rationale=(
            f"VM std={stats.std:.6f}, {stats.pct_exact_reference:.1f}% exact 1.0. "
            "Does not meet solved or flat-start criteria."
        ),
    )


def classify_va(stats: DistributionStats) -> IndicatorResult:
    """Classify the voltage angle indicator.

    Args:
        stats: VA distribution statistics.

    Returns:
        IndicatorResult with the VA sub-classification.
    """
    if (
        stats.std > VA_STD_SOLVED_THRESHOLD
        and stats.pct_exact_reference < VA_PCT_EXACT_SOLVED_THRESHOLD
    ):
        return IndicatorResult(
            name="VA",
            signal=IndicatorSignal.SOLVED_SIGNAL,
            rationale=(
                f"VA std={stats.std:.6f} > {VA_STD_SOLVED_THRESHOLD} and "
                f"{stats.pct_exact_reference:.1f}% exact 0.0 < "
                f"{VA_PCT_EXACT_SOLVED_THRESHOLD}%."
            ),
        )
    if (
        stats.std < VA_STD_FLAT_THRESHOLD
        and stats.pct_exact_reference > VA_PCT_EXACT_FLAT_THRESHOLD
    ):
        return IndicatorResult(
            name="VA",
            signal=IndicatorSignal.FLAT_SIGNAL,
            rationale=(
                f"VA std={stats.std:.6f} < {VA_STD_FLAT_THRESHOLD} and "
                f"{stats.pct_exact_reference:.1f}% exact 0.0 > "
                f"{VA_PCT_EXACT_FLAT_THRESHOLD}%."
            ),
        )
    return IndicatorResult(
        name="VA",
        signal=IndicatorSignal.AMBIGUOUS,
        rationale=(
            f"VA std={stats.std:.6f}, {stats.pct_exact_reference:.1f}% exact 0.0. "
            "Does not meet solved or flat-start criteria."
        ),
    )


def classify_qg(stats: GeneratorQgStats) -> IndicatorResult:
    """Classify the generator reactive power indicator.

    Args:
        stats: Generator Qg statistics.

    Returns:
        IndicatorResult with the Qg sub-classification.
    """
    if stats.pct_nonzero_qg > QG_PCT_NONZERO_SOLVED_THRESHOLD:
        return IndicatorResult(
            name="Qg",
            signal=IndicatorSignal.SOLVED_SIGNAL,
            rationale=(
                f"{stats.pct_nonzero_qg:.1f}% generators have non-zero Qg > "
                f"{QG_PCT_NONZERO_SOLVED_THRESHOLD}%."
            ),
        )
    if stats.pct_nonzero_qg < QG_PCT_NONZERO_FLAT_THRESHOLD:
        return IndicatorResult(
            name="Qg",
            signal=IndicatorSignal.FLAT_SIGNAL,
            rationale=(
                f"{stats.pct_nonzero_qg:.1f}% generators have non-zero Qg < "
                f"{QG_PCT_NONZERO_FLAT_THRESHOLD}%."
            ),
        )
    return IndicatorResult(
        name="Qg",
        signal=IndicatorSignal.AMBIGUOUS,
        rationale=(
            f"{stats.pct_nonzero_qg:.1f}% generators have non-zero Qg. "
            "Does not meet solved or flat-start criteria."
        ),
    )


def classify_overall(
    vm_result: IndicatorResult,
    va_result: IndicatorResult,
    qg_result: IndicatorResult,
) -> SnapshotClassification:
    """Determine overall snapshot classification from three indicator results.

    Decision table:
    - All three SOLVED_SIGNAL -> SOLVED
    - All three FLAT_SIGNAL -> FLAT_START
    - VM + VA both SOLVED_SIGNAL (any Qg) -> SOLVED
    - VM + VA both FLAT_SIGNAL (any Qg) -> FLAT_START
    - Otherwise -> INDETERMINATE

    Args:
        vm_result: VM indicator result.
        va_result: VA indicator result.
        qg_result: Qg indicator result.

    Returns:
        The overall SnapshotClassification.
    """
    vm_sig = vm_result.signal
    va_sig = va_result.signal
    qg_sig = qg_result.signal

    all_solved = (
        vm_sig == IndicatorSignal.SOLVED_SIGNAL
        and va_sig == IndicatorSignal.SOLVED_SIGNAL
        and qg_sig == IndicatorSignal.SOLVED_SIGNAL
    )
    all_flat = (
        vm_sig == IndicatorSignal.FLAT_SIGNAL
        and va_sig == IndicatorSignal.FLAT_SIGNAL
        and qg_sig == IndicatorSignal.FLAT_SIGNAL
    )
    vm_va_solved = (
        vm_sig == IndicatorSignal.SOLVED_SIGNAL and va_sig == IndicatorSignal.SOLVED_SIGNAL
    )
    vm_va_flat = vm_sig == IndicatorSignal.FLAT_SIGNAL and va_sig == IndicatorSignal.FLAT_SIGNAL

    if all_solved or vm_va_solved:
        return SnapshotClassification.SOLVED
    if all_flat or vm_va_flat:
        return SnapshotClassification.FLAT_START
    return SnapshotClassification.INDETERMINATE


# ---------------------------------------------------------------------------
# Phase 3 Implications
# ---------------------------------------------------------------------------


def derive_phase3_implications(
    classification: SnapshotClassification,
) -> str:
    """Derive Phase 3 strategy implications from the classification.

    Args:
        classification: The overall snapshot classification.

    Returns:
        A human-readable string describing Phase 3 implications.
    """
    if classification == SnapshotClassification.SOLVED:
        return (
            "The FNM RAW file contains a converged ACPF solution. Phase 3 can extract "
            "DCPF and ACPF reference solutions directly from the parsed bus and generator "
            "data without running a solver. This significantly simplifies the reference "
            "solution pipeline and eliminates solver-dependence for Phase 3 verification."
        )
    if classification == SnapshotClassification.FLAT_START:
        return (
            "The FNM RAW file contains flat-start initial conditions (VM=1.0, VA=0.0, "
            "Qg=0.0 everywhere). Phase 3 must first converge the network using a verified "
            "AC power flow solver before extracting reference solutions. This adds solver "
            "selection, convergence verification, and cross-validation steps to the Phase 3 "
            "pipeline."
        )
    return (
        "The FNM RAW file classification is indeterminate — the data does not clearly "
        "indicate either a converged solution or flat-start conditions. Manual inspection "
        "of the parsed data is recommended before proceeding with Phase 3 planning. "
        "Consider examining individual bus voltage profiles and generator dispatch patterns."
    )


# ---------------------------------------------------------------------------
# Build Confirmation
# ---------------------------------------------------------------------------


def build_confirmation(
    bus_csv_path: Path,
    gen_csv_path: Path,
    canonical_parser: str = "",
) -> SnapshotConfirmation:
    """Build a complete solved-snapshot confirmation from CSV files.

    Orchestrates data loading, statistics computation, classification, and
    metadata assembly into a single SnapshotConfirmation result.

    Args:
        bus_csv_path: Path to the canonical parser's bus CSV output.
        gen_csv_path: Path to the canonical parser's generator CSV output.
        canonical_parser: Name of the parser that produced the CSVs.

    Returns:
        A fully populated SnapshotConfirmation.
    """
    vm_values, va_values, isolated_count = load_bus_data(bus_csv_path)
    qg_values = load_generator_data(gen_csv_path, bus_csv_path)

    vm_stats = compute_distribution_stats(vm_values, reference_value=1.0)
    va_stats = compute_distribution_stats(va_values, reference_value=0.0)
    qg_stats = compute_qg_stats(qg_values)

    vm_indicator = classify_vm(vm_stats)
    va_indicator = classify_va(va_stats)
    qg_indicator = classify_qg(qg_stats)

    classification = classify_overall(vm_indicator, va_indicator, qg_indicator)
    phase3_text = derive_phase3_implications(classification)

    metadata = ConfirmationMetadata(
        bus_csv_path=str(bus_csv_path),
        generator_csv_path=str(gen_csv_path),
        canonical_parser=canonical_parser,
        timestamp=datetime.now(timezone.utc).isoformat(),
        float_tolerance=FLOAT_TOLERANCE,
    )

    return SnapshotConfirmation(
        classification=classification,
        vm_stats=vm_stats,
        va_stats=va_stats,
        qg_stats=qg_stats,
        vm_indicator=vm_indicator,
        va_indicator=va_indicator,
        qg_indicator=qg_indicator,
        phase3_implications=phase3_text,
        buses_analyzed=len(vm_values),
        buses_excluded_isolated=isolated_count,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def confirmation_to_dict(confirmation: SnapshotConfirmation) -> dict:
    """Convert a SnapshotConfirmation to a JSON-serializable dict.

    Enum values are converted to their string representations.

    Args:
        confirmation: The confirmation result to serialize.

    Returns:
        A dict suitable for json.dumps().
    """
    d = asdict(confirmation)

    # Convert enum values to strings
    d["classification"] = confirmation.classification.value
    d["vm_indicator"]["signal"] = confirmation.vm_indicator.signal.value
    d["va_indicator"]["signal"] = confirmation.va_indicator.signal.value
    d["qg_indicator"]["signal"] = confirmation.qg_indicator.signal.value

    return d


def confirmation_to_markdown(confirmation: SnapshotConfirmation) -> str:
    """Convert a SnapshotConfirmation to a human-readable markdown document.

    Args:
        confirmation: The confirmation result to render.

    Returns:
        A markdown-formatted string.
    """
    c = confirmation
    lines: list[str] = []

    lines.append("# Solved-Snapshot Confirmation Report")
    lines.append("")
    lines.append(f"**Classification:** `{c.classification.value}`")
    lines.append(f"**Timestamp:** {c.metadata.timestamp}")
    lines.append(f"**Canonical Parser:** {c.metadata.canonical_parser or 'N/A'}")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Buses analyzed: {c.buses_analyzed}")
    lines.append(f"- Buses excluded (isolated, type=4): {c.buses_excluded_isolated}")
    lines.append(f"- Generators analyzed: {c.qg_stats.total_generators}")
    lines.append(f"- Float tolerance: {c.metadata.float_tolerance}")
    lines.append("")

    lines.append("## Indicator Results")
    lines.append("")

    # VM
    lines.append("### Voltage Magnitude (VM)")
    lines.append("")
    lines.append(f"- **Signal:** `{c.vm_indicator.signal.value}`")
    lines.append(f"- **Rationale:** {c.vm_indicator.rationale}")
    lines.append(f"- Count: {c.vm_stats.count}")
    lines.append(f"- Mean: {c.vm_stats.mean:.6f} p.u.")
    lines.append(f"- Std: {c.vm_stats.std:.6f} p.u.")
    lines.append(f"- Min: {c.vm_stats.min:.6f} p.u.")
    lines.append(f"- Max: {c.vm_stats.max:.6f} p.u.")
    lines.append(f"- % Exact 1.0: {c.vm_stats.pct_exact_reference:.2f}%")
    lines.append("")

    # VA
    lines.append("### Voltage Angle (VA)")
    lines.append("")
    lines.append(f"- **Signal:** `{c.va_indicator.signal.value}`")
    lines.append(f"- **Rationale:** {c.va_indicator.rationale}")
    lines.append(f"- Count: {c.va_stats.count}")
    lines.append(f"- Mean: {c.va_stats.mean:.6f} deg")
    lines.append(f"- Std: {c.va_stats.std:.6f} deg")
    lines.append(f"- Min: {c.va_stats.min:.6f} deg")
    lines.append(f"- Max: {c.va_stats.max:.6f} deg")
    lines.append(f"- % Exact 0.0: {c.va_stats.pct_exact_reference:.2f}%")
    lines.append("")

    # Qg
    lines.append("### Generator Reactive Power (Qg)")
    lines.append("")
    lines.append(f"- **Signal:** `{c.qg_indicator.signal.value}`")
    lines.append(f"- **Rationale:** {c.qg_indicator.rationale}")
    lines.append(f"- Total generators: {c.qg_stats.total_generators}")
    lines.append(f"- Generators with non-zero Qg: {c.qg_stats.generators_with_nonzero_qg}")
    lines.append(f"- % Non-zero Qg: {c.qg_stats.pct_nonzero_qg:.2f}%")
    lines.append(f"- Mean |Qg|: {c.qg_stats.mean_abs_qg:.4f} MVAr")
    lines.append(f"- Qg range: [{c.qg_stats.min_qg:.4f}, {c.qg_stats.max_qg:.4f}] MVAr")
    lines.append("")

    lines.append("## Overall Classification")
    lines.append("")
    lines.append("| Indicator | Signal |")
    lines.append("|-----------|--------|")
    lines.append(f"| VM | `{c.vm_indicator.signal.value}` |")
    lines.append(f"| VA | `{c.va_indicator.signal.value}` |")
    lines.append(f"| Qg | `{c.qg_indicator.signal.value}` |")
    lines.append(f"| **Overall** | **`{c.classification.value}`** |")
    lines.append("")

    lines.append("## Phase 3 Implications")
    lines.append("")
    lines.append(c.phase3_implications)
    lines.append("")

    lines.append("## Input Files")
    lines.append("")
    lines.append(f"- Bus CSV: `{c.metadata.bus_csv_path}`")
    lines.append(f"- Generator CSV: `{c.metadata.generator_csv_path}`")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for solved-snapshot confirmation.

    Parses command-line arguments, runs the analysis, and writes JSON and
    markdown output files.

    Args:
        argv: Command-line arguments. Defaults to sys.argv[1:].
    """
    parser = argparse.ArgumentParser(
        description="Analyze FNM parsed data to determine solved vs flat-start status."
    )
    parser.add_argument(
        "--bus-csv",
        type=Path,
        required=True,
        help="Path to the canonical parser's bus CSV output.",
    )
    parser.add_argument(
        "--gen-csv",
        type=Path,
        required=True,
        help="Path to the canonical parser's generator CSV output.",
    )
    parser.add_argument(
        "--parser",
        type=str,
        default="",
        help="Name of the canonical parser (e.g. 'MATPOWER', 'GRIDCAL').",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Directory for output files (default: current directory).",
    )

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    confirmation = build_confirmation(
        bus_csv_path=args.bus_csv,
        gen_csv_path=args.gen_csv,
        canonical_parser=args.parser,
    )

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write JSON report
    json_path = output_dir / "solved_snapshot_report.json"
    report_dict = confirmation_to_dict(confirmation)
    json_path.write_text(json.dumps(report_dict, indent=2) + "\n", encoding="utf-8")

    # Write markdown report
    md_path = output_dir / "solved_snapshot_report.md"
    md_text = confirmation_to_markdown(confirmation)
    md_path.write_text(md_text, encoding="utf-8")

    print(f"Classification: {confirmation.classification.value}")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")


if __name__ == "__main__":
    main()
