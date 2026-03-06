"""Bus/Generator Reconciliation between MATPOWER .m files and ACTIVSg companion CSVs.

Verifies version alignment between MATPOWER .m case files and ACTIVSg companion
time series CSVs by comparing bus counts, bus ID sets, generator-bus mappings,
bus type classifications, and generator fuel types. Produces a structured JSON
reconciliation report consumed by downstream deliverables.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import IntEnum, StrEnum
from pathlib import Path

__version__ = "0.1.0"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Network-to-file mapping
# ---------------------------------------------------------------------------

NETWORK_M_FILES: dict[str, str] = {
    "ACTIVSg2000": "case_ACTIVSg2000.m",
    "ACTIVSg10k": "case_ACTIVSg10k.m",
    "case39": "case39.m",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class ReconciliationNetworkId(StrEnum):
    """Identifiers for all three networks in the reconciliation scope."""

    ACTIVSG2000 = "ACTIVSg2000"
    ACTIVSG10K = "ACTIVSg10k"
    TINY = "case39"


class BusType(IntEnum):
    """MATPOWER bus type codes."""

    PQ = 1
    PV = 2
    REF = 3
    ISOLATED = 4


class CheckStatus(StrEnum):
    """Result status for a single reconciliation check."""

    PASS = "pass"
    FAIL = "fail"
    NOT_APPLICABLE = "n/a"


class ReconciliationVerdict(StrEnum):
    """Overall reconciliation verdict for a network."""

    ALIGNED = "aligned"
    MISMATCHED = "mismatched"
    NOT_APPLICABLE = "n/a"


@dataclass(frozen=True)
class MatpowerBusRecord:
    """Parsed bus record from a MATPOWER .m file."""

    bus_id: int
    bus_type: BusType
    pd: float  # real power demand (MW)
    qd: float  # reactive power demand (MVAr)
    base_kv: float


@dataclass(frozen=True)
class MatpowerGenRecord:
    """Parsed generator record from a MATPOWER .m file."""

    gen_bus: int  # bus number the generator is connected to
    pg: float  # real power output (MW)
    qg: float  # reactive power output (MVAr)
    pmax: float  # maximum real power output (MW)
    pmin: float  # minimum real power output (MW)
    fuel_type: str | None  # from genfuel, None if genfuel absent


@dataclass(frozen=True)
class MatpowerCaseData:
    """Structural data extracted from a MATPOWER .m file."""

    file_name: str
    file_path: str  # relative to repo root
    buses: list[MatpowerBusRecord]
    generators: list[MatpowerGenRecord]
    base_mva: float
    has_genfuel: bool


@dataclass(frozen=True)
class CompanionBusInfo:
    """Bus ID sets extracted from companion CSV files."""

    load_bus_ids: set[int]
    wind_bus_ids: set[int]
    solar_bus_ids: set[int]
    all_bus_ids: set[int]  # union of the above


@dataclass(frozen=True)
class CheckResult:
    """Result of a single reconciliation check."""

    check_name: str
    status: CheckStatus
    description: str
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class NetworkReconciliation:
    """Complete reconciliation result for one network."""

    network_id: ReconciliationNetworkId
    m_file_path: str  # relative to repo root
    verdict: ReconciliationVerdict
    checks: list[CheckResult]
    replacement_recommended: bool
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReconciliationReport:
    """Top-level reconciliation report covering all networks."""

    networks: list[NetworkReconciliation]
    script_version: str
    generated_at: str  # ISO 8601
    d1_manifest_path: str  # path to D1 download manifest consumed


# ---------------------------------------------------------------------------
# MATPOWER .m file parsing
# ---------------------------------------------------------------------------

_BLOCK_RE = re.compile(
    r"mpc\.(\w+)\s*=\s*\[([^\]]*)\]",
    re.DOTALL,
)

_GENFUEL_RE = re.compile(
    r"mpc\.genfuel\s*=\s*\{([^}]*)\}",
    re.DOTALL,
)

_BASEMVA_RE = re.compile(
    r"mpc\.baseMVA\s*=\s*([\d.]+)\s*;",
)


def _extract_matrix_block(text: str, field_name: str) -> str:
    """Extract the content between [ ] for mpc.<field_name>."""
    pattern = re.compile(
        rf"mpc\.{re.escape(field_name)}\s*=\s*\[([^\]]*)\]",
        re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        msg = f"Could not locate mpc.{field_name} block"
        raise ValueError(msg)
    return match.group(1)


def _parse_numeric_rows(block_text: str) -> list[list[float]]:
    """Parse semicolon-delimited rows of numeric values from a MATPOWER matrix block."""
    rows: list[list[float]] = []
    for line in block_text.split(";"):
        line = line.strip()
        # Remove trailing comments
        if "%" in line:
            line = line[: line.index("%")]
        line = line.strip()
        if not line:
            continue
        values = line.split()
        try:
            rows.append([float(v) for v in values])
        except ValueError:
            continue
    return rows


def parse_matpower_buses(m_file_path: Path) -> list[MatpowerBusRecord]:
    """Parse the mpc.bus matrix from a MATPOWER .m file.

    Reads the .m file as text, locates the mpc.bus assignment block,
    and extracts each row as a MatpowerBusRecord. Handles both standard
    MATPOWER case format version 2 column layouts (bus_i, type, Pd, Qd,
    Gs, Bs, area, Vm, Va, baseKV, ...) and extended layouts with
    additional LMP columns.

    Args:
        m_file_path: Path to the MATPOWER .m file.

    Returns:
        List of MatpowerBusRecord, one per bus in the case.

    Raises:
        FileNotFoundError: If m_file_path does not exist.
        ValueError: If the mpc.bus block cannot be located or parsed.
    """
    text = m_file_path.read_text()
    block = _extract_matrix_block(text, "bus")
    rows = _parse_numeric_rows(block)

    buses: list[MatpowerBusRecord] = []
    for row in rows:
        if len(row) < 10:
            msg = f"Bus row has {len(row)} columns, expected at least 10"
            raise ValueError(msg)
        buses.append(
            MatpowerBusRecord(
                bus_id=int(row[0]),
                bus_type=BusType(int(row[1])),
                pd=row[2],
                qd=row[3],
                base_kv=row[9],
            )
        )
    return buses


def parse_matpower_generators(
    m_file_path: Path,
) -> list[MatpowerGenRecord]:
    """Parse the mpc.gen matrix and optional mpc.genfuel from a .m file.

    Extracts generator rows from the mpc.gen block (columns: bus, Pg, Qg,
    Qmax, Qmin, Vg, mBase, status, Pmax, Pmin, ...) and, if present,
    matches each generator to its fuel type from the mpc.genfuel cell
    array. The genfuel array must have the same length as the gen matrix;
    if lengths differ, a warning is logged and fuel_type is set to None
    for all generators.

    Args:
        m_file_path: Path to the MATPOWER .m file.

    Returns:
        List of MatpowerGenRecord, one per generator in the case.

    Raises:
        FileNotFoundError: If m_file_path does not exist.
        ValueError: If the mpc.gen block cannot be located or parsed.
    """
    text = m_file_path.read_text()
    block = _extract_matrix_block(text, "gen")
    rows = _parse_numeric_rows(block)

    # Parse genfuel if present
    fuel_types: list[str | None] = [None] * len(rows)
    genfuel_match = _GENFUEL_RE.search(text)
    if genfuel_match:
        genfuel_text = genfuel_match.group(1)
        # Extract quoted strings from the cell array
        fuels = re.findall(r"'([^']*)'", genfuel_text)
        if len(fuels) == len(rows):
            fuel_types = [f.strip() for f in fuels]
        else:
            logger.warning(
                "genfuel length (%d) differs from gen rows (%d); setting all fuel_type to None",
                len(fuels),
                len(rows),
            )

    generators: list[MatpowerGenRecord] = []
    for i, row in enumerate(rows):
        if len(row) < 10:
            msg = f"Gen row has {len(row)} columns, expected at least 10"
            raise ValueError(msg)
        generators.append(
            MatpowerGenRecord(
                gen_bus=int(row[0]),
                pg=row[1],
                qg=row[2],
                pmax=row[8],
                pmin=row[9],
                fuel_type=fuel_types[i],
            )
        )
    return generators


def parse_matpower_case(m_file_path: Path) -> MatpowerCaseData:
    """Parse all structural data from a MATPOWER .m file.

    Combines parse_matpower_buses and parse_matpower_generators into a
    single MatpowerCaseData, also extracting baseMVA and detecting
    whether the genfuel field is present.

    Args:
        m_file_path: Path to the MATPOWER .m file.

    Returns:
        A MatpowerCaseData with buses, generators, and metadata.

    Raises:
        FileNotFoundError: If m_file_path does not exist.
        ValueError: If required MATPOWER blocks cannot be parsed.
    """
    text = m_file_path.read_text()

    # Extract baseMVA
    basemva_match = _BASEMVA_RE.search(text)
    base_mva = float(basemva_match.group(1)) if basemva_match else 100.0

    buses = parse_matpower_buses(m_file_path)
    generators = parse_matpower_generators(m_file_path)

    has_genfuel = _GENFUEL_RE.search(text) is not None

    return MatpowerCaseData(
        file_name=m_file_path.name,
        file_path=str(m_file_path),
        buses=buses,
        generators=generators,
        base_mva=base_mva,
        has_genfuel=has_genfuel,
    )


# ---------------------------------------------------------------------------
# Companion data extraction
# ---------------------------------------------------------------------------


def extract_companion_bus_ids(
    manifest_path: Path,
    network_id: ReconciliationNetworkId,
) -> CompanionBusInfo:
    """Extract bus ID sets from the D1 download manifest for a network.

    Reads the D1 download manifest JSON, locates the inventory for the
    specified network, and extracts bus IDs from each file's bus_ids
    field grouped by series type (load, wind, solar). Returns the
    union as all_bus_ids.

    Args:
        manifest_path: Path to the D1 download_manifest.json file.
        network_id: Which network to extract bus IDs for.

    Returns:
        A CompanionBusInfo with bus ID sets per series type.

    Raises:
        FileNotFoundError: If manifest_path does not exist.
        KeyError: If the specified network_id is not found in the manifest.
        ValueError: If no bus IDs can be extracted for the network.
    """
    with open(manifest_path) as fh:
        manifest_data = json.load(fh)

    # Find the network inventory in the manifest
    network_inv = None
    for net in manifest_data["networks"]:
        if net["network_id"] == network_id.value:
            network_inv = net
            break

    if network_inv is None:
        msg = f"Network {network_id.value} not found in manifest"
        raise KeyError(msg)

    load_ids: set[int] = set()
    wind_ids: set[int] = set()
    solar_ids: set[int] = set()

    for file_entry in network_inv["files"]:
        bus_ids = set(file_entry.get("bus_ids", []))
        series_type = file_entry.get("series_type", "other")

        if series_type == "load":
            load_ids |= bus_ids
        elif series_type == "wind":
            wind_ids |= bus_ids
        elif series_type == "solar":
            solar_ids |= bus_ids

    all_ids = load_ids | wind_ids | solar_ids

    if not all_ids:
        msg = f"No bus IDs found for network {network_id.value} in manifest"
        raise ValueError(msg)

    return CompanionBusInfo(
        load_bus_ids=load_ids,
        wind_bus_ids=wind_ids,
        solar_bus_ids=solar_ids,
        all_bus_ids=all_ids,
    )


# ---------------------------------------------------------------------------
# Reconciliation checks
# ---------------------------------------------------------------------------


def check_bus_count(
    case_data: MatpowerCaseData,
    companion: CompanionBusInfo,
) -> CheckResult:
    """Compare the total bus count between the .m file and companion data.

    Checks whether all companion bus IDs are a subset of .m file bus IDs.

    Args:
        case_data: Parsed MATPOWER case data.
        companion: Bus IDs extracted from companion CSVs.

    Returns:
        A CheckResult with status PASS if all companion bus IDs are a
        subset of .m file bus IDs, FAIL otherwise.
    """
    m_bus_ids = {b.bus_id for b in case_data.buses}
    companion_ids = companion.all_bus_ids
    is_subset = companion_ids <= m_bus_ids
    overlap = companion_ids & m_bus_ids

    return CheckResult(
        check_name="bus_count",
        status=CheckStatus.PASS if is_subset else CheckStatus.FAIL,
        description=(
            f".m file has {len(m_bus_ids)} buses, companion data references "
            f"{len(companion_ids)} unique bus IDs, overlap: {len(overlap)}"
        ),
        details={
            "m_bus_count": len(m_bus_ids),
            "companion_bus_count": len(companion_ids),
            "overlap_count": len(overlap),
        },
    )


def check_bus_id_sets(
    case_data: MatpowerCaseData,
    companion: CompanionBusInfo,
) -> CheckResult:
    """Compare bus ID sets between the .m file and companion CSVs.

    Identifies bus IDs in companion CSVs but not in the .m file (version
    mismatch indicator) and bus IDs in the .m file but not in companion
    CSVs (expected for non-load buses).

    Args:
        case_data: Parsed MATPOWER case data.
        companion: Bus IDs extracted from companion CSVs.

    Returns:
        A CheckResult with status PASS if every companion bus ID exists
        in the .m file, FAIL if any companion bus ID is missing.
    """
    m_bus_ids = {b.bus_id for b in case_data.buses}
    companion_ids = companion.all_bus_ids

    missing_from_m = companion_ids - m_bus_ids
    only_in_m = m_bus_ids - companion_ids
    intersection = m_bus_ids & companion_ids

    status = CheckStatus.PASS if not missing_from_m else CheckStatus.FAIL

    return CheckResult(
        check_name="bus_id_sets",
        status=status,
        description=(
            f"Intersection: {len(intersection)}, "
            f"in companion but not .m: {len(missing_from_m)}, "
            f"in .m but not companion: {len(only_in_m)}"
        ),
        details={
            "missing_from_m": sorted(missing_from_m),
            "only_in_m_count": len(only_in_m),
            "intersection_count": len(intersection),
        },
    )


def check_generator_bus_coverage(
    case_data: MatpowerCaseData,
    companion: CompanionBusInfo,
) -> CheckResult:
    """Verify generator bus assignments against companion bus IDs.

    For each generator in the .m file, checks whether its bus assignment
    (gen_bus) exists in the .m file's bus table.

    Args:
        case_data: Parsed MATPOWER case data.
        companion: Bus IDs extracted from companion CSVs.

    Returns:
        A CheckResult with status PASS if all generator buses are valid,
        FAIL if any generator references a non-existent bus.
    """
    m_bus_ids = {b.bus_id for b in case_data.buses}
    invalid_gen_buses: list[int] = []

    for gen in case_data.generators:
        if gen.gen_bus not in m_bus_ids:
            invalid_gen_buses.append(gen.gen_bus)

    # Check renewable consistency if genfuel is available
    renewable_mismatches: list[dict[str, object]] = []
    if case_data.has_genfuel:
        for gen in case_data.generators:
            if gen.gen_bus in companion.wind_bus_ids and gen.fuel_type:
                if gen.fuel_type.lower() != "wind":
                    renewable_mismatches.append(
                        {
                            "gen_bus": gen.gen_bus,
                            "fuel_type": gen.fuel_type,
                            "expected": "wind",
                        }
                    )
            if gen.gen_bus in companion.solar_bus_ids and gen.fuel_type:
                if gen.fuel_type.lower() != "solar":
                    renewable_mismatches.append(
                        {
                            "gen_bus": gen.gen_bus,
                            "fuel_type": gen.fuel_type,
                            "expected": "solar",
                        }
                    )

    status = CheckStatus.PASS if not invalid_gen_buses else CheckStatus.FAIL

    return CheckResult(
        check_name="generator_bus_coverage",
        status=status,
        description=(
            f"{len(case_data.generators)} generators, "
            f"{len(invalid_gen_buses)} reference non-existent buses"
        ),
        details={
            "total_generators": len(case_data.generators),
            "invalid_gen_buses": sorted(set(invalid_gen_buses)),
            "renewable_mismatches": renewable_mismatches,
        },
    )


def check_bus_types(
    case_data: MatpowerCaseData,
) -> CheckResult:
    """Validate bus type consistency within the .m file.

    Checks: (a) exactly one reference bus (type 3) exists, (b) every
    PV bus (type 2) has at least one generator assigned to it,
    (c) no isolated buses (type 4) exist.

    Args:
        case_data: Parsed MATPOWER case data.

    Returns:
        A CheckResult with status PASS if all bus type invariants hold,
        FAIL if any invariant is violated.
    """
    ref_buses = [b for b in case_data.buses if b.bus_type == BusType.REF]
    pv_buses = [b for b in case_data.buses if b.bus_type == BusType.PV]
    isolated_buses = [b for b in case_data.buses if b.bus_type == BusType.ISOLATED]

    gen_bus_ids = {g.gen_bus for g in case_data.generators}
    pv_without_gen = [b.bus_id for b in pv_buses if b.bus_id not in gen_bus_ids]

    issues: list[str] = []
    if len(ref_buses) != 1:
        issues.append(f"Expected 1 REF bus, found {len(ref_buses)}")
    if pv_without_gen:
        issues.append(f"{len(pv_without_gen)} PV bus(es) without generators: {pv_without_gen[:10]}")
    if isolated_buses:
        issues.append(
            f"{len(isolated_buses)} isolated bus(es) found: "
            f"{[b.bus_id for b in isolated_buses[:10]]}"
        )

    status = CheckStatus.PASS if not issues else CheckStatus.FAIL

    return CheckResult(
        check_name="bus_types",
        status=status,
        description="; ".join(issues) if issues else "All bus type invariants hold",
        details={
            "ref_bus_count": len(ref_buses),
            "pv_bus_count": len(pv_buses),
            "pq_bus_count": len([b for b in case_data.buses if b.bus_type == BusType.PQ]),
            "isolated_bus_count": len(isolated_buses),
            "pv_without_generators": pv_without_gen,
        },
    )


def check_generator_fuel_types(
    case_data: MatpowerCaseData,
    companion: CompanionBusInfo,
) -> CheckResult:
    """Reconcile generator fuel types between .m file and companion data.

    If the .m file has a genfuel field, checks that generators on buses
    with wind companion time series have fuel_type 'wind', and generators
    on buses with solar companion time series have fuel_type 'solar'.

    If genfuel is absent, the check status is NOT_APPLICABLE.

    Args:
        case_data: Parsed MATPOWER case data.
        companion: Bus IDs extracted from companion CSVs.

    Returns:
        A CheckResult with status PASS if fuel types are consistent,
        FAIL if mismatches exist, NOT_APPLICABLE if genfuel is absent.
    """
    if not case_data.has_genfuel:
        return CheckResult(
            check_name="generator_fuel_types",
            status=CheckStatus.NOT_APPLICABLE,
            description=(
                "genfuel field absent; fuel type classification will rely "
                "on companion data or heuristics"
            ),
        )

    mismatches: list[dict[str, object]] = []

    for gen in case_data.generators:
        if gen.gen_bus in companion.wind_bus_ids and gen.fuel_type:
            if gen.fuel_type.lower() != "wind":
                mismatches.append(
                    {
                        "gen_bus": gen.gen_bus,
                        "fuel_type": gen.fuel_type,
                        "expected": "wind",
                    }
                )
        if gen.gen_bus in companion.solar_bus_ids and gen.fuel_type:
            if gen.fuel_type.lower() != "solar":
                mismatches.append(
                    {
                        "gen_bus": gen.gen_bus,
                        "fuel_type": gen.fuel_type,
                        "expected": "solar",
                    }
                )

    status = CheckStatus.PASS if not mismatches else CheckStatus.FAIL

    return CheckResult(
        check_name="generator_fuel_types",
        status=status,
        description=(
            f"{len(mismatches)} fuel type mismatch(es) detected"
            if mismatches
            else "All generator fuel types consistent with companion data"
        ),
        details={
            "mismatches": mismatches,
        },
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def reconcile_network(
    m_file_path: Path,
    manifest_path: Path,
    network_id: ReconciliationNetworkId,
) -> NetworkReconciliation:
    """Run all reconciliation checks for a single network.

    For case39 (TINY), returns NOT_APPLICABLE with no checks since it has
    no ACTIVSg companion data.

    Args:
        m_file_path: Path to the MATPOWER .m file.
        manifest_path: Path to the D1 download_manifest.json.
        network_id: Which network is being reconciled.

    Returns:
        A NetworkReconciliation with all check results and verdict.
    """
    if network_id == ReconciliationNetworkId.TINY:
        return NetworkReconciliation(
            network_id=network_id,
            m_file_path=str(m_file_path),
            verdict=ReconciliationVerdict.NOT_APPLICABLE,
            checks=[],
            replacement_recommended=False,
            notes=["case39 has no ACTIVSg companion data; reconciliation not applicable"],
        )

    case_data = parse_matpower_case(m_file_path)
    companion = extract_companion_bus_ids(manifest_path, network_id)

    checks = [
        check_bus_count(case_data, companion),
        check_bus_id_sets(case_data, companion),
        check_generator_bus_coverage(case_data, companion),
        check_bus_types(case_data),
        check_generator_fuel_types(case_data, companion),
    ]

    any_fail = any(c.status == CheckStatus.FAIL for c in checks)
    verdict = ReconciliationVerdict.MISMATCHED if any_fail else ReconciliationVerdict.ALIGNED

    return NetworkReconciliation(
        network_id=network_id,
        m_file_path=str(m_file_path),
        verdict=verdict,
        checks=checks,
        replacement_recommended=any_fail,
    )


def build_reconciliation_report(
    networks_dir: Path,
    manifest_path: Path,
    *,
    script_version: str = "0.1.0",
) -> ReconciliationReport:
    """Build the complete reconciliation report for all networks.

    Iterates over all three networks (ACTIVSg2000, ACTIVSg10k, case39),
    runs reconcile_network for each, and assembles the top-level
    ReconciliationReport.

    Args:
        networks_dir: Path to the data/networks/ directory containing .m files.
        manifest_path: Path to the D1 download_manifest.json.
        script_version: Version string for the reconciliation script.

    Returns:
        A ReconciliationReport covering all three networks.
    """
    results: list[NetworkReconciliation] = []

    for nid in ReconciliationNetworkId:
        m_file_name = NETWORK_M_FILES[nid.value]
        m_file_path = networks_dir / m_file_name
        result = reconcile_network(m_file_path, manifest_path, nid)
        results.append(result)

    return ReconciliationReport(
        networks=results,
        script_version=script_version,
        generated_at=datetime.now(timezone.utc).isoformat(),
        d1_manifest_path=str(manifest_path),
    )


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def _serialize_value(obj: object) -> object:
    """Convert non-JSON-serializable types for JSON output."""
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, StrEnum | IntEnum):
        return obj.value
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _report_to_dict(report: ReconciliationReport) -> dict:
    """Convert a ReconciliationReport to a JSON-serializable dict."""
    data = asdict(report)
    return data


def write_reconciliation_report(
    report: ReconciliationReport,
    dest_path: Path,
) -> None:
    """Serialize a ReconciliationReport to a human-readable JSON file.

    Writes indented JSON with snake_case keys matching the dataclass
    field names. Sets in CheckResult details are converted to sorted
    lists for JSON serialization.

    Args:
        report: The reconciliation report to serialize.
        dest_path: File path to write the JSON output.

    Raises:
        PermissionError: If dest_path is not writable.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    data = _report_to_dict(report)
    with open(dest_path, "w") as fh:
        json.dump(data, fh, indent=2, default=_serialize_value)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(
    networks_dir: Path | None = None,
    manifest_path: Path | None = None,
    output_path: Path | None = None,
) -> ReconciliationReport:
    """Entry point: reconcile all networks and write the report.

    Args:
        networks_dir: Directory containing .m files. Defaults to
            <repo_root>/data/networks/.
        manifest_path: Path to D1 download manifest. Defaults to
            <repo_root>/data/timeseries/download_manifest.json.
        output_path: Where to write the reconciliation report JSON.
            Defaults to <repo_root>/data/timeseries/reconciliation_report.json.

    Returns:
        The complete ReconciliationReport.
    """
    repo_root = Path(__file__).resolve().parent.parent

    if networks_dir is None:
        networks_dir = repo_root / "networks"
    if manifest_path is None:
        manifest_path = repo_root / "timeseries" / "download_manifest.json"
    if output_path is None:
        output_path = repo_root / "timeseries" / "reconciliation_report.json"

    report = build_reconciliation_report(networks_dir, manifest_path, script_version=__version__)
    write_reconciliation_report(report, output_path)

    # Summary
    for net in report.networks:
        logger.info(
            "Network %s: verdict=%s, replacement_recommended=%s",
            net.network_id,
            net.verdict,
            net.replacement_recommended,
        )

    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
