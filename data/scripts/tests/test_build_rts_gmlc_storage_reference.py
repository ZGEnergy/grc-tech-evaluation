"""Tests for the RTS-GMLC Storage Parameter Reference Table builder.

All tests use synthetic fixture data -- no network access or real RTS-GMLC
files are required. Tests are fully self-contained.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

from scripts.build_rts_gmlc_storage_reference import (
    DEFAULT_CYCLIC_SOC,
    DEFAULT_INIT_SOC,
    DEFAULT_MAX_SOC,
    DEFAULT_MIN_SOC,
    DEFAULT_NON_SPINNING_ELIGIBLE,
    DEFAULT_SPINNING_ELIGIBLE,
    STORAGE_PARAMETER_METADATA,
    ParameterScaleType,
    RtsGmlcStorageUnit,
    StorageProvenance,
    StorageReferenceResult,
    build_storage_param_row,
    build_storage_reference,
    decompose_roundtrip_efficiency,
    join_storage_sources,
    parse_storage_csv,
    parse_storage_from_gen_csv,
    write_storage_reference_csv,
)

# ---------------------------------------------------------------------------
# Fixtures: synthetic CSV content
# ---------------------------------------------------------------------------

# Minimal gen.csv header and a storage row matching 313_STORAGE_1.
# Includes a few non-storage rows to test filtering.
_GEN_CSV_HEADER = (
    "GEN UID,Bus ID,Unit Type,Fuel,Category,PMax MW,PMin MW,"
    "Ramp Rate MW/Min,Min Up Time Hr,Min Down Time Hr,"
    "Start Time Cold Hr,Start Time Warm Hr,Start Time Hot Hr,"
    "Start Heat Cold MBTU,Start Heat Warm MBTU,Start Heat Hot MBTU,"
    "Non Fuel Start Cost $,Non Fuel Shutdown Cost $,"
    "Fuel Price $/MMBTU,HR_avg_0,Storage Roundtrip Efficiency"
)

_GEN_CSV_STORAGE_ROW = (
    "313_STORAGE_1,313,STORAGE,Storage,Storage,50,0,50,0,0,0,0,0,0,0,0,0,0,0,0,85"
)

_GEN_CSV_THERMAL_ROW = "101_CT_1,101,CT,NG,Gas,55,8,8.0,1,1,1,1,1,10,7,3,100,50,3.5,10000,0"

_GEN_CSV_WIND_ROW = "303_WIND_1,303,WIND,Wind,Wind,148,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0"

_GEN_CSV_SOLAR_ROW = "310_PV_1,310,PV,Solar,Solar,51.6,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0"

# Minimal storage.csv with head and tail rows for 313_STORAGE_1.
_STORAGE_CSV_HEADER = "GEN UID,Storage,Max Volume GWh,Initial Volume GWh,Inflow Limit GWh"

_STORAGE_CSV_HEAD_ROW = "313_STORAGE_1,head,0.15,0.075,0.05"
_STORAGE_CSV_TAIL_ROW = "313_STORAGE_1,tail,0.15,0.075,0.05"


def _write_gen_csv(
    path: Path,
    rows: list[str] | None = None,
) -> Path:
    """Write a synthetic gen.csv to the given path."""
    if rows is None:
        rows = [_GEN_CSV_STORAGE_ROW, _GEN_CSV_THERMAL_ROW, _GEN_CSV_WIND_ROW, _GEN_CSV_SOLAR_ROW]
    content = _GEN_CSV_HEADER + "\n" + "\n".join(rows) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _write_storage_csv(
    path: Path,
    rows: list[str] | None = None,
) -> Path:
    """Write a synthetic storage.csv to the given path."""
    if rows is None:
        rows = [_STORAGE_CSV_HEAD_ROW, _STORAGE_CSV_TAIL_ROW]
    content = _STORAGE_CSV_HEADER + "\n" + "\n".join(rows) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _make_storage_unit(
    gen_uid: str = "313_STORAGE_1",
    bus_id: int = 313,
    unit_type: str = "STORAGE",
    category: str = "Storage",
    pmax_mw: float = 50.0,
    pmin_mw: float = 0.0,
    ramp_rate_mw_per_min: float = 50.0,
    roundtrip_efficiency_pct: float = 85.0,
    max_volume_gwh: float = 0.15,
    initial_volume_gwh: float = 0.075,
    inflow_limit_gwh: float = 0.05,
) -> RtsGmlcStorageUnit:
    """Create a synthetic RtsGmlcStorageUnit with sensible defaults."""
    return RtsGmlcStorageUnit(
        gen_uid=gen_uid,
        bus_id=bus_id,
        unit_type=unit_type,
        category=category,
        pmax_mw=pmax_mw,
        pmin_mw=pmin_mw,
        ramp_rate_mw_per_min=ramp_rate_mw_per_min,
        roundtrip_efficiency_pct=roundtrip_efficiency_pct,
        max_volume_gwh=max_volume_gwh,
        initial_volume_gwh=initial_volume_gwh,
        inflow_limit_gwh=inflow_limit_gwh,
    )


def _make_provenance() -> StorageProvenance:
    """Create a synthetic StorageProvenance for testing."""
    return StorageProvenance(
        repo_url="https://github.com/GridMod/RTS-GMLC",
        commit_hash="v3.2",
        gen_csv_path="RTS_Data/SourceData/gen.csv",
        storage_csv_path="RTS_Data/SourceData/storage.csv",
        download_timestamp="2025-01-01T00:00:00+00:00",
        script_version="0.1.0",
        num_storage_units_parsed=1,
        num_rows_produced=1,
    )


# ---------------------------------------------------------------------------
# Test 1: parse_storage_from_gen_csv finds the storage unit
# ---------------------------------------------------------------------------


def test_parse_storage_from_gen_csv_finds_storage_unit(tmp_path: Path) -> None:
    """Verify parse_storage_from_gen_csv returns exactly one RtsGmlcStorageUnit
    with gen_uid == '313_STORAGE_1', pmax_mw == 50.0, ramp_rate_mw_per_min == 50.0,
    and roundtrip_efficiency_pct == 85.0.
    """
    gen_csv = _write_gen_csv(tmp_path / "gen.csv")
    units = parse_storage_from_gen_csv(gen_csv)

    assert len(units) == 1
    unit = units[0]
    assert unit.gen_uid == "313_STORAGE_1"
    assert unit.pmax_mw == 50.0
    assert unit.ramp_rate_mw_per_min == 50.0
    assert unit.roundtrip_efficiency_pct == 85.0


# ---------------------------------------------------------------------------
# Test 2: parse_storage_from_gen_csv ignores non-storage
# ---------------------------------------------------------------------------


def test_parse_storage_from_gen_csv_ignores_non_storage(tmp_path: Path) -> None:
    """Given gen.csv with storage, thermal, wind, and solar rows, verify that
    parse_storage_from_gen_csv returns only the storage row (length == 1).
    """
    gen_csv = _write_gen_csv(tmp_path / "gen.csv")
    units = parse_storage_from_gen_csv(gen_csv)

    assert len(units) == 1
    assert units[0].category == "Storage"
    # Ensure no thermal, wind, or solar units are included.
    for unit in units:
        assert unit.unit_type not in ("CT", "CC", "STEAM", "WIND", "PV", "RTPV")


# ---------------------------------------------------------------------------
# Test 3: parse_storage_csv returns head storage
# ---------------------------------------------------------------------------


def test_parse_storage_csv_returns_head_storage(tmp_path: Path) -> None:
    """Verify parse_storage_csv returns an entry for '313_STORAGE_1' with
    max_volume_gwh == 0.15 and initial_volume_gwh == 0.075, taken from
    the head-position row.
    """
    storage_csv = _write_storage_csv(tmp_path / "storage.csv")
    result = parse_storage_csv(storage_csv)

    assert "313_STORAGE_1" in result
    params = result["313_STORAGE_1"]
    assert params["max_volume_gwh"] == 0.15
    assert params["initial_volume_gwh"] == 0.075


# ---------------------------------------------------------------------------
# Test 4: join_storage_sources populates energy fields
# ---------------------------------------------------------------------------


def test_join_storage_sources_populates_energy_fields() -> None:
    """Given a partial RtsGmlcStorageUnit (energy fields at 0.0) and a matching
    storage_params dict, verify join_storage_sources produces a unit with
    max_volume_gwh == 0.15 and initial_volume_gwh == 0.075.
    """
    partial_unit = _make_storage_unit(
        max_volume_gwh=0.0,
        initial_volume_gwh=0.0,
        inflow_limit_gwh=0.0,
    )
    storage_params = {
        "313_STORAGE_1": {
            "max_volume_gwh": 0.15,
            "initial_volume_gwh": 0.075,
            "inflow_limit_gwh": 0.05,
        }
    }

    joined = join_storage_sources([partial_unit], storage_params)
    assert len(joined) == 1
    assert joined[0].max_volume_gwh == 0.15
    assert joined[0].initial_volume_gwh == 0.075


# ---------------------------------------------------------------------------
# Test 5: join_storage_sources raises on empty gen_units
# ---------------------------------------------------------------------------


def test_join_storage_sources_raises_on_empty_gen_units() -> None:
    """Verify join_storage_sources raises ValueError when gen_units is empty."""
    with pytest.raises(ValueError, match="No storage units found"):
        join_storage_sources([], {})


# ---------------------------------------------------------------------------
# Test 6: decompose_roundtrip_efficiency symmetric split
# ---------------------------------------------------------------------------


def test_decompose_roundtrip_efficiency_symmetric_split() -> None:
    """Verify decompose_roundtrip_efficiency(0.85) returns two values whose
    product equals 0.85 (within 1e-10), and that both are equal.
    """
    charge_eff, discharge_eff = decompose_roundtrip_efficiency(0.85)

    # Both components must be equal (symmetric split).
    assert charge_eff == discharge_eff

    # Product must equal the original round-trip efficiency.
    assert abs(charge_eff * discharge_eff - 0.85) < 1e-10

    # Each should be approximately 0.9220.
    assert abs(charge_eff - 0.9220) < 0.001


# ---------------------------------------------------------------------------
# Test 7: decompose_roundtrip_efficiency rejects invalid
# ---------------------------------------------------------------------------


def test_decompose_roundtrip_efficiency_rejects_invalid() -> None:
    """Verify decompose_roundtrip_efficiency raises ValueError for invalid inputs."""
    with pytest.raises(ValueError):
        decompose_roundtrip_efficiency(0.0)

    with pytest.raises(ValueError):
        decompose_roundtrip_efficiency(1.5)

    with pytest.raises(ValueError):
        decompose_roundtrip_efficiency(-0.1)


# ---------------------------------------------------------------------------
# Test 8: build_storage_param_row converts GWh to MWh
# ---------------------------------------------------------------------------


def test_build_storage_param_row_converts_gwh_to_mwh() -> None:
    """Given a unit with max_volume_gwh == 0.15 and pmax_mw == 50.0,
    verify build_storage_param_row produces energy_mwh == 150.0
    and duration_hr == 3.0.
    """
    unit = _make_storage_unit(pmax_mw=50.0, max_volume_gwh=0.15)
    row = build_storage_param_row(unit)

    assert row.energy_mwh == 150.0  # 0.15 * 1000
    assert row.duration_hr == 3.0  # 150 / 50


# ---------------------------------------------------------------------------
# Test 9: build_storage_param_row assigns defaults
# ---------------------------------------------------------------------------


def test_build_storage_param_row_assigns_defaults() -> None:
    """Verify build_storage_param_row produces correct default values."""
    unit = _make_storage_unit()
    row = build_storage_param_row(unit)

    assert row.min_soc == DEFAULT_MIN_SOC  # 0.10
    assert row.max_soc == DEFAULT_MAX_SOC  # 0.90
    assert row.init_soc == DEFAULT_INIT_SOC  # 0.50
    assert row.cyclic_soc is DEFAULT_CYCLIC_SOC  # True
    assert row.spinning_eligible is DEFAULT_SPINNING_ELIGIBLE  # True
    assert row.non_spinning_eligible is DEFAULT_NON_SPINNING_ELIGIBLE  # True


# ---------------------------------------------------------------------------
# Test 10: build_storage_param_row ramp rate conversion
# ---------------------------------------------------------------------------


def test_build_storage_param_row_ramp_rate_conversion() -> None:
    """Given a unit with ramp_rate_mw_per_min == 50.0, verify the output
    has ramp_rate_mw_per_hr == 3000.0.
    """
    unit = _make_storage_unit(ramp_rate_mw_per_min=50.0)
    row = build_storage_param_row(unit)

    assert row.ramp_rate_mw_per_hr == 3000.0  # 50 * 60


# ---------------------------------------------------------------------------
# Test 11: build_storage_reference produces one row
# ---------------------------------------------------------------------------


def test_build_storage_reference_produces_one_row(tmp_path: Path) -> None:
    """Run build_storage_reference on synthetic files and verify the result
    contains exactly one StorageParamRow with tech_class == 'battery'
    and generator_count == 1.
    """
    gen_csv = _write_gen_csv(tmp_path / "gen.csv")
    storage_csv = _write_storage_csv(tmp_path / "storage.csv")

    result = build_storage_reference(gen_csv, storage_csv)

    assert len(result.params) == 1
    assert result.params[0].tech_class == "battery"
    assert result.params[0].generator_count == 1


# ---------------------------------------------------------------------------
# Test 12: write_storage_reference_csv has provenance header
# ---------------------------------------------------------------------------


def test_write_storage_reference_csv_has_provenance_header(tmp_path: Path) -> None:
    """Write the reference table to a temp file, read back, and verify
    provenance comment lines.
    """
    unit = _make_storage_unit()
    row = build_storage_param_row(unit)
    provenance = _make_provenance()

    result = StorageReferenceResult(
        provenance=provenance,
        params=[row],
        parameter_metadata=STORAGE_PARAMETER_METADATA,
        warnings=[],
    )

    dest = tmp_path / "storage_params.csv"
    write_storage_reference_csv(result, dest, provenance=provenance)

    text = dest.read_text(encoding="utf-8")
    lines = text.splitlines()

    # First lines must be comments.
    comment_lines = [line for line in lines if line.startswith("#")]
    assert len(comment_lines) >= 5

    # Must contain repo URL, commit hash, and both source file paths.
    comment_text = "\n".join(comment_lines)
    assert "https://github.com/GridMod/RTS-GMLC" in comment_text
    assert "v3.2" in comment_text
    assert "gen.csv" in comment_text
    assert "storage.csv" in comment_text


# ---------------------------------------------------------------------------
# Test 13: write_storage_reference_csv roundtrip
# ---------------------------------------------------------------------------


def test_write_storage_reference_csv_roundtrip(tmp_path: Path) -> None:
    """Write the reference table, read back as CSV (skipping comments),
    and verify structure and content.
    """
    unit = _make_storage_unit()
    row = build_storage_param_row(unit)
    provenance = _make_provenance()

    result = StorageReferenceResult(
        provenance=provenance,
        params=[row],
        parameter_metadata=STORAGE_PARAMETER_METADATA,
        warnings=[],
    )

    dest = tmp_path / "storage_params.csv"
    write_storage_reference_csv(result, dest, provenance=provenance)

    # Read back, skipping comment lines.
    text = dest.read_text(encoding="utf-8")
    data_lines = [line for line in text.splitlines() if not line.startswith("#")]
    data_text = "\n".join(data_lines)

    reader = csv.DictReader(io.StringIO(data_text))
    rows = list(reader)

    # (a) Number of data rows equals number of StorageParamRow entries.
    assert len(rows) == len(result.params)

    # (b) All expected columns are present.
    expected_columns = {
        "tech_class",
        "gen_uid",
        "power_mw",
        "energy_mwh",
        "duration_hr",
        "roundtrip_efficiency",
        "charge_efficiency",
        "discharge_efficiency",
        "min_soc",
        "max_soc",
        "init_soc",
        "cyclic_soc",
        "ramp_rate_mw_per_min",
        "ramp_rate_mw_per_hr",
        "spinning_eligible",
        "non_spinning_eligible",
        "generator_count",
        "source_gen_uids",
    }
    assert expected_columns.issubset(set(reader.fieldnames or []))

    # (c) power_mw is positive.
    assert float(rows[0]["power_mw"]) > 0

    # (d) Boolean columns contain lowercase "true" or "false".
    for bool_col in ("cyclic_soc", "spinning_eligible", "non_spinning_eligible"):
        assert rows[0][bool_col] in ("true", "false")


# ---------------------------------------------------------------------------
# Test 14: parameter_metadata covers all columns
# ---------------------------------------------------------------------------


def test_parameter_metadata_covers_all_columns() -> None:
    """Verify STORAGE_PARAMETER_METADATA contains entries for every
    non-identifier column in StorageParamRow, with no duplicates.
    """
    expected_params = {
        "power_mw",
        "energy_mwh",
        "duration_hr",
        "roundtrip_efficiency",
        "charge_efficiency",
        "discharge_efficiency",
        "min_soc",
        "max_soc",
        "init_soc",
        "cyclic_soc",
        "ramp_rate_mw_per_min",
        "ramp_rate_mw_per_hr",
        "spinning_eligible",
        "non_spinning_eligible",
    }

    meta_names = [m.name for m in STORAGE_PARAMETER_METADATA]

    # All expected parameters are covered.
    assert expected_params.issubset(set(meta_names))

    # No duplicates.
    assert len(meta_names) == len(set(meta_names))


# ---------------------------------------------------------------------------
# Test 15: parameter_metadata intensive/extensive classification
# ---------------------------------------------------------------------------


def test_parameter_metadata_intensive_extensive_classification() -> None:
    """Verify intensive/extensive classification of parameters."""
    meta_by_name = {m.name: m for m in STORAGE_PARAMETER_METADATA}

    expected_intensive = {
        "roundtrip_efficiency",
        "charge_efficiency",
        "discharge_efficiency",
        "min_soc",
        "max_soc",
        "init_soc",
        "cyclic_soc",
        "duration_hr",
        "spinning_eligible",
        "non_spinning_eligible",
    }
    expected_extensive = {
        "power_mw",
        "energy_mwh",
        "ramp_rate_mw_per_min",
        "ramp_rate_mw_per_hr",
    }

    for name in expected_intensive:
        assert meta_by_name[name].scale_type == ParameterScaleType.INTENSIVE, (
            f"{name} should be INTENSIVE"
        )

    for name in expected_extensive:
        assert meta_by_name[name].scale_type == ParameterScaleType.EXTENSIVE, (
            f"{name} should be EXTENSIVE"
        )


# ---------------------------------------------------------------------------
# Test 16: storage_param_row no negative values
# ---------------------------------------------------------------------------


def test_storage_param_row_no_negative_values() -> None:
    """Verify the StorageParamRow has no negative numeric values."""
    unit = _make_storage_unit()
    row = build_storage_param_row(unit)

    assert row.power_mw >= 0
    assert row.energy_mwh >= 0
    assert row.duration_hr >= 0
    assert row.roundtrip_efficiency >= 0
    assert row.charge_efficiency >= 0
    assert row.discharge_efficiency >= 0
    assert row.min_soc >= 0
    assert row.max_soc >= 0
    assert row.init_soc >= 0
    assert row.ramp_rate_mw_per_min >= 0
    assert row.ramp_rate_mw_per_hr >= 0
