"""TINY (case39) Snapshot Cleanup & Generator Classification.

Applies Phase 1 D3 cleanup rules to the IEEE 39-bus New England test case
and produces a hardcoded fuel-type classification table mapping all 10
generators to their documented types and corresponding RTS-GMLC technology
classes.

Output artifacts:
  - data/timeseries/case39/case39.m              (cleaned MATPOWER case)
  - data/timeseries/case39/gen_classification.csv (fuel & RTS-GMLC mapping)
  - data/timeseries/case39/cleanup_manifest.json  (modification audit trail)
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from scripts.reconcile_bus_gen import parse_matpower_case
from scripts.snapshot_cleanup import (
    CASE39_FUEL_MAP,
    HYDRO_RESERVOIR_PMIN_FRACTION,
    HYDRO_THRESHOLD_MW,
    CleanupNetworkId,
    FuelCategory,
    FuelClassificationSource,
    apply_bus_cleanup,
    apply_generator_cleanup,
    build_cleanup_manifest,
    build_network_manifest,
    classify_generators,
    compute_bus_modifications,
    write_cleanup_manifest,
    write_matpower_case,
)

__version__ = "0.1.0"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class RtsGmlcClass(StrEnum):
    """RTS-GMLC technology class assignments for case39 generators.

    Each case39 generator is mapped to the nearest RTS-GMLC technology
    class based on fuel type and capacity band. These classes determine
    which RTS-GMLC parameter templates are used in Deliverable 2
    (Generator Temporal Parameter Assignment).
    """

    HYDRO_RESERVOIR = "Hydro"
    NUCLEAR = "Nuclear"
    COAL_STEAM = "Coal/Steam"
    GAS_CC = "Gas/CC"
    GAS_CC_FLEXIBLE = "Gas/CC (flexible)"


@dataclass(frozen=True)
class Case39GenClassification:
    """Classification record for a single case39 generator.

    Combines fuel category information from Phase 1 D3's FuelCategory
    enum with the RTS-GMLC technology class mapping specific to case39.
    One record per generator, in gen-index order.
    """

    gen_index: int  # 0-based index into mpc.gen matrix
    gen_number: int  # 1-based generator number (gen_index + 1)
    bus_id: int  # bus number the generator is connected to
    fuel_category: str  # from Phase 1 D3 FuelCategory enum value
    rts_gmlc_class: RtsGmlcClass
    pmax_mw: float  # Pmax from the original .m file
    pmin_mw: float  # Pmin after cleanup (260 for hydro, 0 for others)
    classification_source: str  # "case39_header_map" for all case39 gens
    rationale: str  # human-readable explanation of the classification


@dataclass(frozen=True)
class Case39CleanupResult:
    """Complete result of cleaning case39 and classifying its generators.

    Bundles the three output artifacts: cleaned .m file path,
    gen_classification.csv path, and cleanup manifest JSON path,
    plus the in-memory classification table for downstream consumption.
    """

    cleaned_m_file: str  # relative path to cleaned .m file
    gen_classification_csv: str  # relative path to gen_classification.csv
    cleanup_manifest_json: str  # relative path to cleanup_manifest.json
    classifications: list[Case39GenClassification]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Mapping from gen_index to (bus_id, rts_gmlc_class, rationale).
# Fuel category comes from CASE39_FUEL_MAP in snapshot_cleanup.py.
_CASE39_RTS_GMLC_MAP: dict[int, tuple[int, RtsGmlcClass, str]] = {
    0: (30, RtsGmlcClass.HYDRO_RESERVOIR, "Pmax >= 30 MW threshold; large reservoir unit"),
    1: (31, RtsGmlcClass.NUCLEAR, "Baseload nuclear"),
    2: (32, RtsGmlcClass.NUCLEAR, "Baseload nuclear"),
    3: (33, RtsGmlcClass.COAL_STEAM, "Large fossil, coal-class per fleet diversity split"),
    4: (34, RtsGmlcClass.COAL_STEAM, "Large fossil, coal-class per fleet diversity split"),
    5: (35, RtsGmlcClass.NUCLEAR, "Baseload nuclear"),
    6: (36, RtsGmlcClass.GAS_CC, "Mid-size fossil, CC-class for fleet flexibility"),
    7: (37, RtsGmlcClass.NUCLEAR, "Baseload nuclear"),
    8: (38, RtsGmlcClass.NUCLEAR, "Baseload nuclear"),
    9: (39, RtsGmlcClass.GAS_CC_FLEXIBLE, "External equiv., flexible dispatch for UC purposes"),
}

# Expected Pmax values from case39.m for each gen_index.
_CASE39_PMAX: dict[int, float] = {
    0: 1040.0,
    1: 646.0,
    2: 725.0,
    3: 652.0,
    4: 508.0,
    5: 687.0,
    6: 580.0,
    7: 564.0,
    8: 865.0,
    9: 1100.0,
}

_CASE39_GEN_COUNT = 10


def _compute_post_cleanup_pmin(gen_index: int, pmax: float) -> float:
    """Compute the post-cleanup Pmin for a case39 generator.

    Only the hydro unit (gen 0, bus 30) gets a nonzero Pmin:
    25% of Pmax = 260 MW. All others remain at 0.
    """
    fuel = CASE39_FUEL_MAP[gen_index]
    if fuel == FuelCategory.HYDRO and pmax >= HYDRO_THRESHOLD_MW:
        return HYDRO_RESERVOIR_PMIN_FRACTION * pmax
    return 0.0


CASE39_CLASSIFICATION_TABLE: list[Case39GenClassification] = [
    Case39GenClassification(
        gen_index=i,
        gen_number=i + 1,
        bus_id=_CASE39_RTS_GMLC_MAP[i][0],
        fuel_category=CASE39_FUEL_MAP[i].value,
        rts_gmlc_class=_CASE39_RTS_GMLC_MAP[i][1],
        pmax_mw=_CASE39_PMAX[i],
        pmin_mw=_compute_post_cleanup_pmin(i, _CASE39_PMAX[i]),
        classification_source=FuelClassificationSource.CASE39_HEADER_MAP.value,
        rationale=_CASE39_RTS_GMLC_MAP[i][2],
    )
    for i in range(_CASE39_GEN_COUNT)
]
"""Hardcoded classification for all 10 case39 generators.

Each entry maps a generator (by 0-based index) to its fuel category,
RTS-GMLC technology class, post-cleanup Pmin, and a rationale string.
The fuel categories are consistent with Phase 1 D3's CASE39_FUEL_MAP.
The RTS-GMLC class assignments are specific to this deliverable and
determine which parameter templates are used in Phase 2b D2.

Gen 0 (bus 30): Hydro reservoir, Pmin = 260 MW (25% of 1040 MW)
Gens 1,2,5,7,8 (buses 31,32,35,37,38): Nuclear, Pmin = 0 MW
Gens 3,4 (buses 33,34): Coal/Steam, Pmin = 0 MW
Gen 6 (bus 36): Gas/CC, Pmin = 0 MW
Gen 9 (bus 39): Gas/CC (flexible), Pmin = 0 MW
"""


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def build_case39_classification_table(
    gen_data: list[tuple[int, float, float]],
) -> list[Case39GenClassification]:
    """Build the full classification table for case39 generators.

    Combines the hardcoded fuel-type mapping (from Phase 1 D3's
    CASE39_FUEL_MAP) with the RTS-GMLC technology class assignments
    and post-cleanup Pmin values. The gen_data parameter provides
    the actual bus ID and Pmax for each generator from the parsed
    .m file, which are used to populate the classification records
    and verify consistency with the hardcoded mapping.

    Args:
        gen_data: List of (bus_id, pmax_mw, pmin_mw_post_cleanup)
            tuples, one per generator, in gen-index order. The
            pmin_mw_post_cleanup value is the Pmin after applying
            Phase 1 cleanup rules (260 MW for hydro, 0 for others).

    Returns:
        A list of Case39GenClassification, one per generator,
        in gen-index order.

    Raises:
        ValueError: If len(gen_data) != 10 (case39 has exactly
            10 generators).
        ValueError: If any bus_id in gen_data does not match the
            expected bus for that gen_index per CASE39_FUEL_MAP.
    """
    if len(gen_data) != _CASE39_GEN_COUNT:
        msg = f"case39 has exactly {_CASE39_GEN_COUNT} generators, but got {len(gen_data)}"
        raise ValueError(msg)

    classifications: list[Case39GenClassification] = []
    for i, (bus_id, pmax_mw, pmin_mw) in enumerate(gen_data):
        expected_bus = _CASE39_RTS_GMLC_MAP[i][0]
        if bus_id != expected_bus:
            msg = f"Gen {i} expected bus {expected_bus} but got {bus_id}"
            raise ValueError(msg)

        classifications.append(
            Case39GenClassification(
                gen_index=i,
                gen_number=i + 1,
                bus_id=bus_id,
                fuel_category=CASE39_FUEL_MAP[i].value,
                rts_gmlc_class=_CASE39_RTS_GMLC_MAP[i][1],
                pmax_mw=pmax_mw,
                pmin_mw=pmin_mw,
                classification_source=FuelClassificationSource.CASE39_HEADER_MAP.value,
                rationale=_CASE39_RTS_GMLC_MAP[i][2],
            )
        )

    return classifications


def write_gen_classification_csv(
    classifications: list[Case39GenClassification],
    dest_path: Path,
) -> None:
    """Write the generator classification table to CSV.

    Produces a CSV file with columns: gen_index, gen_number, bus_id,
    fuel_category, rts_gmlc_class, pmax_mw, pmin_mw,
    classification_source, rationale. One row per generator, ordered
    by gen_index. Uses csv.writer with quoting for the rationale field.

    The output file includes a header row and uses UTF-8 encoding.

    Args:
        classifications: The classification table from
            build_case39_classification_table.
        dest_path: File path to write the CSV output. Parent directory
            is created if it does not exist.

    Raises:
        PermissionError: If dest_path is not writable.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "gen_index",
        "gen_number",
        "bus_id",
        "fuel_category",
        "rts_gmlc_class",
        "pmax_mw",
        "pmin_mw",
        "classification_source",
        "rationale",
    ]

    with open(dest_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, quoting=csv.QUOTE_NONNUMERIC)
        writer.writeheader()
        for cls in classifications:
            writer.writerow(
                {
                    "gen_index": cls.gen_index,
                    "gen_number": cls.gen_number,
                    "bus_id": cls.bus_id,
                    "fuel_category": cls.fuel_category,
                    "rts_gmlc_class": cls.rts_gmlc_class.value,
                    "pmax_mw": cls.pmax_mw,
                    "pmin_mw": cls.pmin_mw,
                    "classification_source": cls.classification_source,
                    "rationale": cls.rationale,
                }
            )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def clean_and_classify_case39(
    networks_dir: Path,
    output_dir: Path,
) -> Case39CleanupResult:
    """Run the full cleanup and classification pipeline for case39.

    This is the primary entry point. It:
    1. Parses case39.m from networks_dir using Phase 1 D3's parser.
    2. Classifies generators using Phase 1 D3's classify_generators
       (which uses CASE39_FUEL_MAP for case39).
    3. Applies generator cleanup rules via apply_generator_cleanup
       (hydro Pmin = 260 MW, all Pg/Qg = 0).
    4. Applies bus cleanup rules via apply_bus_cleanup
       (all Vm = 1.0, all Va = 0).
    5. Writes the cleaned .m file to output_dir/case39/case39.m via
       write_matpower_case.
    6. Builds the case39 classification table with RTS-GMLC class
       assignments via build_case39_classification_table.
    7. Writes gen_classification.csv to output_dir/case39/ via
       write_gen_classification_csv.
    8. Builds and writes the cleanup manifest JSON to
       output_dir/case39/cleanup_manifest.json.

    Args:
        networks_dir: Path to the data/networks/ directory containing
            the original case39.m file.
        output_dir: Base directory for output. Files are written to
            output_dir/case39/.

    Returns:
        A Case39CleanupResult with paths to all output files and
        the in-memory classification table.

    Raises:
        FileNotFoundError: If case39.m is not found in networks_dir.
    """
    network_id = CleanupNetworkId.TINY
    source_path = networks_dir / "case39.m"

    if not source_path.exists():
        msg = f"case39.m not found in {networks_dir}"
        raise FileNotFoundError(msg)

    # 1. Parse the case
    case_data = parse_matpower_case(source_path)

    # Read raw text for bus Vm/Va extraction
    m_file_text = source_path.read_text()

    # 2. Classify generators (Phase 1 D3)
    d3_classifications = classify_generators(case_data, network_id)

    # 3. Apply generator cleanup
    cleaned_generators, gen_modifications = apply_generator_cleanup(case_data, d3_classifications)

    # 4. Apply bus cleanup
    cleaned_buses, _ = apply_bus_cleanup(case_data)

    # Compute bus modifications from raw text
    bus_modifications = compute_bus_modifications(case_data, m_file_text)

    # 5. Write cleaned .m file
    dest_dir = output_dir / "case39"
    cleaned_m_path = dest_dir / "case39.m"
    write_matpower_case(source_path, cleaned_m_path, cleaned_buses, cleaned_generators)

    # 6. Build case39 classification table with RTS-GMLC classes
    gen_data: list[tuple[int, float, float]] = [
        (g.gen_bus, g.pmax, g.pmin) for g in cleaned_generators
    ]
    classifications = build_case39_classification_table(gen_data)

    # 7. Write gen_classification.csv
    csv_path = dest_dir / "gen_classification.csv"
    write_gen_classification_csv(classifications, csv_path)

    # 8. Build and write cleanup manifest
    network_manifest = build_network_manifest(
        network_id=network_id,
        source_path=source_path,
        dest_path=cleaned_m_path,
        case_data=case_data,
        classifications=d3_classifications,
        gen_modifications=gen_modifications,
        bus_modifications=bus_modifications,
    )
    cleanup_manifest = build_cleanup_manifest([network_manifest], script_version=__version__)
    manifest_path = dest_dir / "cleanup_manifest.json"
    write_cleanup_manifest(cleanup_manifest, manifest_path)

    return Case39CleanupResult(
        cleaned_m_file=str(cleaned_m_path.relative_to(output_dir.parent)),
        gen_classification_csv=str(csv_path.relative_to(output_dir.parent)),
        cleanup_manifest_json=str(manifest_path.relative_to(output_dir.parent)),
        classifications=classifications,
    )


def main(
    networks_dir: Path | None = None,
    output_dir: Path | None = None,
) -> Case39CleanupResult:
    """Entry point: clean case39 and produce all output artifacts.

    Default paths resolve relative to the repository root:
    - networks_dir: data/networks/
    - output_dir: data/timeseries/

    Args:
        networks_dir: Directory containing the original case39.m.
            Defaults to <repo_root>/data/networks/.
        output_dir: Base directory for cleaned output files.
            Defaults to <repo_root>/data/timeseries/.

    Returns:
        A Case39CleanupResult with paths and classification data.
    """
    repo_root = Path(__file__).resolve().parent.parent

    if networks_dir is None:
        networks_dir = repo_root / "networks"
    if output_dir is None:
        output_dir = repo_root / "timeseries"

    return clean_and_classify_case39(networks_dir, output_dir)


if __name__ == "__main__":
    main()
