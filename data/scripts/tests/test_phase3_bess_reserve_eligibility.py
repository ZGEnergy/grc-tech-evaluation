"""Tests for BESS Reserve Eligibility Integration (Phase 3 D3).

Self-contained tests -- no external files or network calls required.
All test data is constructed inline.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

from scripts.assign_reserve_eligibility import (
    OUTPUT_CSV_COLUMNS,
    ReserveEligibilityRow,
)
from scripts.phase3_bess_placement import BessUnit
from scripts.phase3_bess_reserve_eligibility import (
    BESS_TECH_CLASS,
    EXTENDED_OUTPUT_CSV_COLUMNS,
    SOC_NOTE_TEXT,
    BessReserveEligibilityRow,
    BessReserveNetworkId,
    build_all_bess_eligibility_rows,
    build_bess_eligibility_row,
    compute_adequacy_comparison,
    compute_bess_max_non_spinning_mw,
    compute_bess_max_spinning_mw,
    load_existing_eligibility,
    merge_eligibility_rows,
    process_network,
    write_combined_eligibility_csv,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bess_unit(
    unit_id: str = "BESS_SMALL_001",
    bus: int = 100,
    power_mw: float = 50.0,
    ramp_rate_mw_per_min: float = 50.0,
    energy_mwh: float = 200.0,
    duration_hr: float = 4.0,
    charge_eff: float = 0.92,
    discharge_eff: float = 0.92,
    roundtrip_eff: float = 0.8464,
    min_soc_pct: float = 10.0,
    max_soc_pct: float = 90.0,
    initial_soc_pct: float = 50.0,
    cyclic_soc: bool = True,
) -> BessUnit:
    """Create a BessUnit with sensible defaults for testing."""
    return BessUnit(
        unit_id=unit_id,
        bus=bus,
        power_mw=power_mw,
        energy_mwh=energy_mwh,
        duration_hr=duration_hr,
        charge_eff=charge_eff,
        discharge_eff=discharge_eff,
        roundtrip_eff=roundtrip_eff,
        min_soc_pct=min_soc_pct,
        max_soc_pct=max_soc_pct,
        initial_soc_pct=initial_soc_pct,
        ramp_rate_mw_per_min=ramp_rate_mw_per_min,
        cyclic_soc=cyclic_soc,
    )


def _make_thermal_row(
    gen_uid: str = "bus_1_gen_0",
    tech_class: str = "gas_CT_small",
    fuel_type: str = "gas",
    spinning_eligible: bool = True,
    non_spinning_eligible: bool = True,
    max_spinning_mw: float = 100.0,
    max_non_spinning_mw: float = 100.0,
) -> ReserveEligibilityRow:
    """Create a thermal ReserveEligibilityRow for testing."""
    return ReserveEligibilityRow(
        gen_uid=gen_uid,
        tech_class=tech_class,
        fuel_type=fuel_type,
        spinning_eligible=spinning_eligible,
        non_spinning_eligible=non_spinning_eligible,
        max_spinning_mw=max_spinning_mw,
        max_non_spinning_mw=max_non_spinning_mw,
    )


def _write_reserve_requirements_csv(path: Path, spinning_mw: float, non_spinning_mw: float) -> None:
    """Write a minimal reserve_requirements_24h.csv for testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    header = ["Product"] + [f"HR_{h}" for h in range(1, 25)]
    rows = [
        ["spinning"] + [f"{spinning_mw:.2f}"] * 24,
        ["non_spinning"] + [f"{non_spinning_mw:.2f}"] * 24,
    ]
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


def _write_bess_units_csv(path: Path, units: list[BessUnit]) -> None:
    """Write a bess_units.csv for testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "unit_id",
        "bus",
        "power_mw",
        "energy_mwh",
        "duration_hr",
        "charge_eff",
        "discharge_eff",
        "roundtrip_eff",
        "min_soc_pct",
        "max_soc_pct",
        "initial_soc_pct",
        "ramp_rate_mw_per_min",
        "cyclic_soc",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for u in units:
        writer.writerow(
            {
                "unit_id": u.unit_id,
                "bus": u.bus,
                "power_mw": f"{u.power_mw:.1f}",
                "energy_mwh": f"{u.energy_mwh:.1f}",
                "duration_hr": f"{u.duration_hr:.1f}",
                "charge_eff": f"{u.charge_eff:.4f}",
                "discharge_eff": f"{u.discharge_eff:.4f}",
                "roundtrip_eff": f"{u.roundtrip_eff:.4f}",
                "min_soc_pct": f"{u.min_soc_pct:.1f}",
                "max_soc_pct": f"{u.max_soc_pct:.1f}",
                "initial_soc_pct": f"{u.initial_soc_pct:.1f}",
                "ramp_rate_mw_per_min": f"{u.ramp_rate_mw_per_min:.2f}",
                "cyclic_soc": str(u.cyclic_soc).lower(),
            }
        )
    path.write_text(output.getvalue(), encoding="utf-8")


def _write_eligibility_csv(
    path: Path,
    rows: list[ReserveEligibilityRow],
    include_bess: bool = False,
    bess_rows: list[BessReserveEligibilityRow] | None = None,
) -> None:
    """Write a reserve_eligibility.csv for testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Use the extended columns if BESS rows included, else original 7
    columns = list(EXTENDED_OUTPUT_CSV_COLUMNS) if include_bess else list(OUTPUT_CSV_COLUMNS)
    if include_bess and "soc_note" not in columns:
        columns.append("soc_note")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)

    for r in rows:
        row_data = [
            r.gen_uid,
            r.tech_class,
            r.fuel_type,
            "true" if r.spinning_eligible else "false",
            "true" if r.non_spinning_eligible else "false",
            f"{r.max_spinning_mw:.2f}",
            f"{r.max_non_spinning_mw:.2f}",
        ]
        if include_bess:
            row_data.append("")
        writer.writerow(row_data)

    if bess_rows:
        for br in bess_rows:
            writer.writerow(
                [
                    br.gen_uid,
                    br.tech_class,
                    br.fuel_type,
                    "true" if br.spinning_eligible else "false",
                    "true" if br.non_spinning_eligible else "false",
                    f"{br.max_spinning_mw:.2f}",
                    f"{br.max_non_spinning_mw:.2f}",
                    br.soc_note,
                ]
            )

    path.write_text(output.getvalue(), encoding="utf-8")


# ---------------------------------------------------------------------------
# Test 1: compute_bess_max_spinning_mw -- power-limited case
# ---------------------------------------------------------------------------


def test_compute_bess_max_spinning_mw_power_limited() -> None:
    """BESS with fast ramp (100 MW/min) is power-limited at 100 MW.

    10-minute ramp capacity = 100.0 * 10 = 1000.0 MW, which exceeds
    power_mw = 100.0. Result should be capped at power_mw.
    """
    result = compute_bess_max_spinning_mw(power_mw=100.0, ramp_rate_mw_per_min=100.0)
    assert result == 100.0


# ---------------------------------------------------------------------------
# Test 2: compute_bess_max_spinning_mw -- ramp-limited case
# ---------------------------------------------------------------------------


def test_compute_bess_max_spinning_mw_ramp_limited() -> None:
    """Hypothetical slow-ramping BESS is ramp-limited at 50 MW.

    10-minute ramp capacity = 5.0 * 10 = 50.0 MW, which is less than
    power_mw = 200.0. Result should be the ramp capacity (50.0).
    This is a synthetic edge case -- real BESS units have high ramp rates.
    """
    result = compute_bess_max_spinning_mw(power_mw=200.0, ramp_rate_mw_per_min=5.0)
    assert result == 50.0


# ---------------------------------------------------------------------------
# Test 3: compute_bess_max_non_spinning_mw
# ---------------------------------------------------------------------------


def test_compute_bess_max_non_spinning_mw() -> None:
    """BESS non-spinning reserve equals full power capacity."""
    result = compute_bess_max_non_spinning_mw(power_mw=75.0)
    assert result == 75.0


# ---------------------------------------------------------------------------
# Test 4: build_bess_eligibility_row_fields
# ---------------------------------------------------------------------------


def test_build_bess_eligibility_row_fields() -> None:
    """Verify all fields of a BESS eligibility row."""
    unit = _make_bess_unit(
        unit_id="BESS_SMALL_001",
        power_mw=50.0,
        ramp_rate_mw_per_min=50.0,
    )
    row = build_bess_eligibility_row(unit)

    assert row.gen_uid == "BESS_SMALL_001"
    assert row.tech_class == "bess"
    assert row.fuel_type == "storage"
    assert row.spinning_eligible is True
    assert row.non_spinning_eligible is True
    assert row.max_spinning_mw == 50.0
    assert row.max_non_spinning_mw == 50.0
    assert row.soc_note == SOC_NOTE_TEXT


# ---------------------------------------------------------------------------
# Test 5: build_all_bess_eligibility_rows_sorted
# ---------------------------------------------------------------------------


def test_build_all_bess_eligibility_rows_sorted() -> None:
    """Rows should be sorted by gen_uid regardless of input order."""
    units = [
        _make_bess_unit(unit_id="BESS_SMALL_003", bus=300),
        _make_bess_unit(unit_id="BESS_SMALL_001", bus=100),
        _make_bess_unit(unit_id="BESS_SMALL_002", bus=200),
    ]
    rows = build_all_bess_eligibility_rows(units)

    assert len(rows) == 3
    assert rows[0].gen_uid == "BESS_SMALL_001"
    assert rows[1].gen_uid == "BESS_SMALL_002"
    assert rows[2].gen_uid == "BESS_SMALL_003"


# ---------------------------------------------------------------------------
# Test 6: build_all_bess_eligibility_rows_empty_raises
# ---------------------------------------------------------------------------


def test_build_all_bess_eligibility_rows_empty_raises() -> None:
    """Empty input should raise ValueError."""
    with pytest.raises(ValueError, match="must not be empty"):
        build_all_bess_eligibility_rows([])


# ---------------------------------------------------------------------------
# Test 7: merge_eligibility_rows_preserves_thermal_order
# ---------------------------------------------------------------------------


def test_merge_eligibility_rows_preserves_thermal_order() -> None:
    """Thermal rows keep original order; BESS rows are appended at end."""
    thermal = [
        _make_thermal_row(gen_uid="bus_1_gen_0"),
        _make_thermal_row(gen_uid="bus_2_gen_0"),
        _make_thermal_row(gen_uid="bus_3_gen_0"),
    ]
    bess = [
        BessReserveEligibilityRow(
            gen_uid="BESS_SMALL_001",
            tech_class="bess",
            fuel_type="storage",
            spinning_eligible=True,
            non_spinning_eligible=True,
            max_spinning_mw=50.0,
            max_non_spinning_mw=50.0,
            soc_note=SOC_NOTE_TEXT,
        ),
        BessReserveEligibilityRow(
            gen_uid="BESS_SMALL_002",
            tech_class="bess",
            fuel_type="storage",
            spinning_eligible=True,
            non_spinning_eligible=True,
            max_spinning_mw=75.0,
            max_non_spinning_mw=75.0,
            soc_note=SOC_NOTE_TEXT,
        ),
    ]

    combined = merge_eligibility_rows(thermal, bess)

    # (a) total rows
    assert len(combined) == 5

    # (b) first 3 rows are thermal in order
    assert combined[0].gen_uid == "bus_1_gen_0"
    assert combined[1].gen_uid == "bus_2_gen_0"
    assert combined[2].gen_uid == "bus_3_gen_0"

    # (c) last 2 rows are BESS
    assert combined[3].gen_uid == "BESS_SMALL_001"
    assert combined[4].gen_uid == "BESS_SMALL_002"

    # (d) thermal rows have empty soc_note
    for i in range(3):
        assert combined[i].soc_note == ""

    # (e) BESS rows have non-empty soc_note
    for i in range(3, 5):
        assert combined[i].soc_note != ""


# ---------------------------------------------------------------------------
# Test 8: load_existing_eligibility_filters_prior_bess_rows
# ---------------------------------------------------------------------------


def test_load_existing_eligibility_filters_prior_bess_rows(tmp_path: Path) -> None:
    """Prior BESS rows (tech_class='bess') should be filtered out."""
    thermal = [_make_thermal_row(gen_uid=f"gen_{i}", tech_class="gas_CT_small") for i in range(5)]
    bess = [
        BessReserveEligibilityRow(
            gen_uid=f"BESS_{i}",
            tech_class="bess",
            fuel_type="storage",
            spinning_eligible=True,
            non_spinning_eligible=True,
            max_spinning_mw=50.0,
            max_non_spinning_mw=50.0,
            soc_note=SOC_NOTE_TEXT,
        )
        for i in range(2)
    ]

    csv_path = tmp_path / "reserve_eligibility.csv"
    _write_eligibility_csv(csv_path, thermal, include_bess=True, bess_rows=bess)

    loaded = load_existing_eligibility(csv_path)

    # Only 5 thermal rows; the 2 BESS rows are filtered out
    assert len(loaded) == 5
    for row in loaded:
        assert row.tech_class != BESS_TECH_CLASS


# ---------------------------------------------------------------------------
# Test 9: compute_adequacy_comparison_values
# ---------------------------------------------------------------------------


def test_compute_adequacy_comparison_values() -> None:
    """Verify numeric values of the spinning adequacy comparison."""
    thermal = [
        _make_thermal_row(gen_uid="g1", max_spinning_mw=100.0, max_non_spinning_mw=100.0),
        _make_thermal_row(gen_uid="g2", max_spinning_mw=200.0, max_non_spinning_mw=200.0),
        _make_thermal_row(gen_uid="g3", max_spinning_mw=150.0, max_non_spinning_mw=150.0),
    ]
    bess = [
        BessReserveEligibilityRow(
            gen_uid="B1",
            tech_class="bess",
            fuel_type="storage",
            spinning_eligible=True,
            non_spinning_eligible=True,
            max_spinning_mw=50.0,
            max_non_spinning_mw=50.0,
            soc_note=SOC_NOTE_TEXT,
        ),
        BessReserveEligibilityRow(
            gen_uid="B2",
            tech_class="bess",
            fuel_type="storage",
            spinning_eligible=True,
            non_spinning_eligible=True,
            max_spinning_mw=75.0,
            max_non_spinning_mw=75.0,
            soc_note=SOC_NOTE_TEXT,
        ),
    ]

    spinning, _ = compute_adequacy_comparison(
        thermal,
        bess,
        spinning_requirement_mw=300.0,
        non_spinning_requirement_mw=300.0,
    )

    assert spinning.pre_bess_eligible_mw == 450.0
    assert spinning.post_bess_eligible_mw == 575.0
    assert spinning.bess_contribution_mw == 125.0
    assert spinning.pre_bess_ratio == pytest.approx(1.5, abs=1e-6)
    assert spinning.post_bess_ratio == pytest.approx(575.0 / 300.0, abs=1e-6)
    assert spinning.ratio_improvement == pytest.approx(575.0 / 300.0 - 450.0 / 300.0, abs=1e-6)
    assert spinning.bess_fraction_of_eligible == pytest.approx(125.0 / 575.0, abs=1e-4)
    assert spinning.is_adequate is True


# ---------------------------------------------------------------------------
# Test 10: compute_adequacy_comparison_zero_requirement
# ---------------------------------------------------------------------------


def test_compute_adequacy_comparison_zero_requirement() -> None:
    """Zero requirement should give inf ratios and is_adequate=True."""
    thermal = [_make_thermal_row(gen_uid="g1", max_spinning_mw=100.0)]
    bess = [
        BessReserveEligibilityRow(
            gen_uid="B1",
            tech_class="bess",
            fuel_type="storage",
            spinning_eligible=True,
            non_spinning_eligible=True,
            max_spinning_mw=50.0,
            max_non_spinning_mw=50.0,
            soc_note=SOC_NOTE_TEXT,
        ),
    ]

    spinning, _ = compute_adequacy_comparison(
        thermal,
        bess,
        spinning_requirement_mw=0.0,
        non_spinning_requirement_mw=0.0,
    )

    assert spinning.pre_bess_ratio == float("inf")
    assert spinning.post_bess_ratio == float("inf")
    # With zero requirement, post_bess_eligible_mw (150) > 0.0, so is_adequate is True
    assert spinning.is_adequate is True


# ---------------------------------------------------------------------------
# Test 11: write_combined_eligibility_csv_format
# ---------------------------------------------------------------------------


def test_write_combined_eligibility_csv_format(tmp_path: Path) -> None:
    """Verify CSV output format: headers, booleans, decimals, soc_note."""
    thermal = [
        _make_thermal_row(gen_uid="gen_0", max_spinning_mw=100.0, max_non_spinning_mw=100.0),
        _make_thermal_row(gen_uid="gen_1", max_spinning_mw=200.5, max_non_spinning_mw=150.25),
    ]
    bess = [
        BessReserveEligibilityRow(
            gen_uid="BESS_001",
            tech_class="bess",
            fuel_type="storage",
            spinning_eligible=True,
            non_spinning_eligible=True,
            max_spinning_mw=50.0,
            max_non_spinning_mw=50.0,
            soc_note=SOC_NOTE_TEXT,
        ),
    ]

    combined = merge_eligibility_rows(thermal, bess)
    csv_path = tmp_path / "output.csv"
    write_combined_eligibility_csv(combined, csv_path)

    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))

    # (a) header matches EXTENDED_OUTPUT_CSV_COLUMNS
    assert reader.fieldnames is not None
    assert tuple(reader.fieldnames) == EXTENDED_OUTPUT_CSV_COLUMNS

    rows = list(reader)

    # (b) 3 data rows
    assert len(rows) == 3

    # (c) boolean columns are "true" or "false"
    for r in rows:
        assert r["spinning_eligible"] in ("true", "false")
        assert r["non_spinning_eligible"] in ("true", "false")

    # (d) MW columns have 2 decimal places
    for r in rows:
        spin_val = r["max_spinning_mw"]
        assert "." in spin_val
        assert len(spin_val.split(".")[1]) == 2

        nonspin_val = r["max_non_spinning_mw"]
        assert "." in nonspin_val
        assert len(nonspin_val.split(".")[1]) == 2

    # (e) thermal rows have empty soc_note
    assert rows[0]["soc_note"] == ""
    assert rows[1]["soc_note"] == ""

    # (f) BESS row has non-empty soc_note
    assert rows[2]["soc_note"] != ""
    assert rows[2]["soc_note"] == SOC_NOTE_TEXT


# ---------------------------------------------------------------------------
# Test 12: process_network_end_to_end
# ---------------------------------------------------------------------------


def test_process_network_end_to_end(tmp_path: Path) -> None:
    """End-to-end test: D2 + D5 + D4 inputs -> combined output CSV."""
    network_dir = tmp_path / "ACTIVSg2000"
    network_dir.mkdir(parents=True)

    # Create D2 bess_units.csv with 2 BESS units
    bess_units = [
        _make_bess_unit(
            unit_id="BESS_SMALL_001",
            bus=100,
            power_mw=50.0,
            ramp_rate_mw_per_min=50.0,
            energy_mwh=200.0,
        ),
        _make_bess_unit(
            unit_id="BESS_SMALL_002",
            bus=200,
            power_mw=50.0,
            ramp_rate_mw_per_min=50.0,
            energy_mwh=200.0,
        ),
    ]
    _write_bess_units_csv(network_dir / "bess_units.csv", bess_units)

    # Create D5 reserve_eligibility.csv with 5 thermal generators
    thermal = [
        _make_thermal_row(
            gen_uid=f"gen_{i}",
            tech_class="gas_CT_small",
            fuel_type="gas",
            spinning_eligible=True,
            non_spinning_eligible=True,
            max_spinning_mw=100.0,
            max_non_spinning_mw=100.0,
        )
        for i in range(5)
    ]
    _write_eligibility_csv(network_dir / "reserve_eligibility.csv", thermal)

    # Create D4 reserve_requirements_24h.csv
    _write_reserve_requirements_csv(
        network_dir / "reserve_requirements_24h.csv",
        spinning_mw=200.0,
        non_spinning_mw=200.0,
    )

    result = process_network(
        network_id=BessReserveNetworkId.SMALL,
        bess_units_csv_path=network_dir / "bess_units.csv",
        eligibility_csv_path=network_dir / "reserve_eligibility.csv",
        reserve_req_csv_path=network_dir / "reserve_requirements_24h.csv",
        output_dir=network_dir,
    )

    # Verify result counts
    assert result.bess_unit_count == 2
    assert result.thermal_row_count == 5
    assert result.total_row_count == 7

    # Verify output CSV exists and has correct row count
    output_csv = network_dir / "reserve_eligibility.csv"
    assert output_csv.exists()

    text = output_csv.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    csv_rows = list(reader)
    assert len(csv_rows) == 7

    # Verify post-BESS spinning adequacy reflects combined capacity
    # Thermal spinning: 5 * 100 = 500 MW; BESS: 2 * 50 = 100 MW; total = 600 MW
    # Requirement: 200 MW; ratio = 600/200 = 3.0
    assert result.spinning_adequacy.post_bess_eligible_mw == pytest.approx(600.0)
    assert result.spinning_adequacy.is_adequate is True
