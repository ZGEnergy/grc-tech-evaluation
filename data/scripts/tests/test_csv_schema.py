"""Tests for the Canonical CSV Schema Specification (PRD 04)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.csv_schema import (
    ColumnDtype,
    CsvFileType,
    FileTypeSchema,
    Unit,
    build_bess_units_schema,
    build_canonical_schema,
    build_flowgates_schema,
    build_gen_temporal_params_schema,
    build_load_schema,
    build_reserve_requirements_schema,
    build_scenario_multipliers_schema,
    build_solar_actual_schema,
    build_solar_forecast_schema,
    build_wind_actual_schema,
    build_wind_forecast_schema,
    infer_file_type,
    schema_to_json_schema,
    validate_csv_file,
    write_json_schema,
    write_markdown_doc,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

HR_NAMES = [f"HR_{h}" for h in range(1, 25)]

TEMPORAL_BUILDERS: list[tuple[str, callable]] = [
    ("load", build_load_schema),
    ("wind_forecast", build_wind_forecast_schema),
    ("wind_actual", build_wind_actual_schema),
    ("solar_forecast", build_solar_forecast_schema),
    ("solar_actual", build_solar_actual_schema),
    ("reserve_requirements", build_reserve_requirements_schema),
    ("scenario_multipliers", build_scenario_multipliers_schema),
]


def _col_by_name(schema: FileTypeSchema, name: str):
    """Get a ColumnSpec by name from a FileTypeSchema."""
    for col in schema.columns:
        if col.name == name:
            return col
    msg = f"Column '{name}' not found in schema for {schema.file_type}"
    raise KeyError(msg)


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    """Write a minimal CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        fh.write(",".join(header) + "\n")
        for row in rows:
            fh.write(",".join(row) + "\n")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBuildLoadSchema:
    """Tests 1-3: load schema structure and constraints."""

    def test_build_load_schema_has_25_columns(self) -> None:
        """Verify load schema has exactly 25 columns: bus_id + HR_1..HR_24."""
        schema = build_load_schema()
        assert len(schema.columns) == 25
        col_names = [c.name for c in schema.columns]
        assert col_names[0] == "bus_id"
        assert col_names[1:] == HR_NAMES

    def test_build_load_schema_bus_id_is_int_required(self) -> None:
        """Verify bus_id column has dtype=INT, required=True, unit=NONE."""
        schema = build_load_schema()
        bus_id = _col_by_name(schema, "bus_id")
        assert bus_id.dtype == ColumnDtype.INT
        assert bus_id.required is True
        assert bus_id.unit == Unit.NONE

    def test_build_load_schema_hr_columns_are_float_mw_nonneg(self) -> None:
        """Verify every HR_* column has dtype=FLOAT, unit=MW, required=True, min_value=0.0."""
        schema = build_load_schema()
        for hr_name in HR_NAMES:
            col = _col_by_name(schema, hr_name)
            assert col.dtype == ColumnDtype.FLOAT, f"{hr_name} dtype"
            assert col.unit == Unit.MW, f"{hr_name} unit"
            assert col.required is True, f"{hr_name} required"
            assert col.min_value == 0.0, f"{hr_name} min_value"


class TestTemporalSchemas:
    """Test 4: all temporal schemas have 24 HR columns."""

    @pytest.mark.parametrize(
        ("name", "builder"), TEMPORAL_BUILDERS, ids=[t[0] for t in TEMPORAL_BUILDERS]
    )
    def test_all_temporal_schemas_have_24_hr_columns(self, name: str, builder: callable) -> None:
        """Verify each temporal file type has HR_1..HR_24 with no gaps or duplicates."""
        schema = builder()
        hr_cols = [c.name for c in schema.columns if c.name.startswith("HR_")]
        assert hr_cols == HR_NAMES, f"{name}: expected {HR_NAMES}, got {hr_cols}"


class TestGenTemporalParamsSchema:
    """Test 5: generator temporal params constraints."""

    def test_gen_temporal_params_schema_constraints(self) -> None:
        """Verify non-negative constraints on key generator parameters."""
        schema = build_gen_temporal_params_schema()
        constrained_cols = [
            "pmin",
            "ramp_rate",
            "min_up_time",
            "min_down_time",
            "startup_cost",
            "marginal_cost",
        ]
        for col_name in constrained_cols:
            col = _col_by_name(schema, col_name)
            assert col.min_value == 0.0, f"{col_name} should have min_value=0.0"


class TestBessUnitsSchema:
    """Test 6: BESS units SOC constraints."""

    def test_bess_units_schema_soc_constraints(self) -> None:
        """Verify min_soc, max_soc have [0,1] bounds and efficiency has [0,1] bounds."""
        schema = build_bess_units_schema()
        for col_name in ("min_soc", "max_soc"):
            col = _col_by_name(schema, col_name)
            assert col.min_value == 0.0, f"{col_name} min"
            assert col.max_value == 1.0, f"{col_name} max"

        eff = _col_by_name(schema, "efficiency")
        assert eff.min_value == 0.0
        assert eff.max_value == 1.0


class TestScenarioMultipliersSchema:
    """Test 7: scenario multipliers schema structure."""

    def test_scenario_multipliers_schema_has_scenario_id(self) -> None:
        """Verify scenario_id is INT, required, and 24 HR columns exist."""
        schema = build_scenario_multipliers_schema()
        sid = _col_by_name(schema, "scenario_id")
        assert sid.dtype == ColumnDtype.INT
        assert sid.required is True

        hr_cols = [c.name for c in schema.columns if c.name.startswith("HR_")]
        assert len(hr_cols) == 24


class TestFlowgatesSchema:
    """Test 8: flowgates schema semicolon-delimited columns."""

    def test_flowgates_schema_defines_semicolon_delimited_columns(self) -> None:
        """Verify line_ids and weights are STR (semicolon-delimited encoding)."""
        schema = build_flowgates_schema()
        line_ids = _col_by_name(schema, "line_ids")
        weights = _col_by_name(schema, "weights")
        assert line_ids.dtype == ColumnDtype.STR
        assert weights.dtype == ColumnDtype.STR


class TestCanonicalSchema:
    """Test 9: canonical schema completeness."""

    def test_build_canonical_schema_contains_all_file_types(self) -> None:
        """Verify canonical schema has exactly 12 FileTypeSchema entries."""
        schema = build_canonical_schema()
        assert len(schema.file_types) == 12

        # Verify all CsvFileType enum members are represented
        schema_types = {ft.file_type for ft in schema.file_types}
        enum_types = set(CsvFileType)
        assert schema_types == enum_types


class TestJsonSchemaOutput:
    """Tests 10-11: JSON Schema generation and roundtrip."""

    def test_schema_to_json_schema_produces_valid_json_schema(self) -> None:
        """Verify JSON Schema has $schema key with draft-2020-12 and oneOf structure."""
        schema = build_canonical_schema()
        json_schema = schema_to_json_schema(schema)

        # Serialize and parse back
        serialized = json.dumps(json_schema)
        parsed = json.loads(serialized)

        assert "$schema" in parsed
        assert "2020-12" in parsed["$schema"]
        assert "items" in parsed
        assert "oneOf" in parsed["items"]
        assert "$defs" in parsed

    def test_write_json_schema_roundtrip(self, tmp_path: Path) -> None:
        """Verify JSON Schema writes and reads back correctly."""
        schema = build_canonical_schema()
        dest = tmp_path / "test_schema.json"
        write_json_schema(schema, dest)

        with open(dest) as fh:
            loaded = json.load(fh)

        assert "$schema" in loaded
        assert "$defs" in loaded
        assert "items" in loaded
        assert len(loaded["$defs"]) == 12


class TestMarkdownOutput:
    """Test 12: markdown documentation completeness."""

    def test_write_markdown_doc_contains_all_file_types(self, tmp_path: Path) -> None:
        """Verify markdown doc contains every CsvFileType value."""
        schema = build_canonical_schema()
        dest = tmp_path / "test_schema.md"
        write_markdown_doc(schema, dest)

        content = dest.read_text()
        for ft in CsvFileType:
            assert ft.value in content, f"Missing file type '{ft.value}' in markdown"


class TestInferFileType:
    """Tests 13-14: file type inference."""

    def test_infer_file_type_known_names(self) -> None:
        """Verify all known file names map to the correct CsvFileType."""
        known = {
            "load_24h.csv": CsvFileType.LOAD_24H,
            "wind_forecast_24h.csv": CsvFileType.WIND_FORECAST_24H,
            "wind_actual_24h.csv": CsvFileType.WIND_ACTUAL_24H,
            "solar_forecast_24h.csv": CsvFileType.SOLAR_FORECAST_24H,
            "solar_actual_24h.csv": CsvFileType.SOLAR_ACTUAL_24H,
            "gen_temporal_params.csv": CsvFileType.GEN_TEMPORAL_PARAMS,
            "reserve_requirements_24h.csv": CsvFileType.RESERVE_REQUIREMENTS_24H,
            "reserve_eligibility.csv": CsvFileType.RESERVE_ELIGIBILITY,
            "bess_units.csv": CsvFileType.BESS_UNITS,
            "dr_buses.csv": CsvFileType.DR_BUSES,
            "flowgates.csv": CsvFileType.FLOWGATES,
            "scenario_multipliers_50x24.csv": CsvFileType.SCENARIO_MULTIPLIERS,
        }
        for fname, expected in known.items():
            result = infer_file_type(Path(fname))
            assert result == expected, f"{fname} -> {result}, expected {expected}"

    def test_infer_file_type_unknown_raises(self) -> None:
        """Verify ValueError for unrecognized file names."""
        with pytest.raises(ValueError, match="Cannot infer file type"):
            infer_file_type(Path("unknown_data.csv"))


class TestValidateCsvFile:
    """Tests 15-18: CSV validation."""

    def _make_load_header(self) -> list[str]:
        return ["bus_id"] + HR_NAMES

    def _make_load_row(self, bus_id: int, value: float = 100.0) -> list[str]:
        return [str(bus_id)] + [str(value)] * 24

    def test_validate_csv_valid_load_file(self, tmp_path: Path) -> None:
        """Validate a minimal valid load_24h.csv — expect valid=True, no errors."""
        path = tmp_path / "load_24h.csv"
        header = self._make_load_header()
        rows = [
            self._make_load_row(1, 150.0),
            self._make_load_row(2, 200.5),
        ]
        _write_csv(path, header, rows)

        schema = build_canonical_schema()
        result = validate_csv_file(path, schema)

        assert result.valid is True
        assert len(result.errors) == 0
        assert result.row_count == 2
        assert result.file_type == CsvFileType.LOAD_24H

    def test_validate_csv_missing_required_column(self, tmp_path: Path) -> None:
        """Validate a load_24h.csv missing HR_12 — expect missing_required error."""
        header = ["bus_id"] + [f"HR_{h}" for h in range(1, 25) if h != 12]
        rows = [
            [str(1)] + [str(100.0)] * 23,
            [str(2)] + [str(200.0)] * 23,
        ]
        path = tmp_path / "load_24h.csv"
        _write_csv(path, header, rows)

        schema = build_canonical_schema()
        result = validate_csv_file(path, schema)

        assert result.valid is False
        missing_errors = [e for e in result.errors if e.error_type == "missing_required"]
        assert len(missing_errors) >= 1
        assert any(e.column_name == "HR_12" for e in missing_errors)

    def test_validate_csv_negative_value_in_load(self, tmp_path: Path) -> None:
        """Validate a load_24h.csv with a negative MW value in HR_5 — expect out_of_range."""
        path = tmp_path / "load_24h.csv"
        header = self._make_load_header()
        row = self._make_load_row(1, 100.0)
        # HR_5 is at index 5 (bus_id is 0, HR_1 is 1, ..., HR_5 is 5)
        row[5] = "-50.0"
        _write_csv(path, header, [row])

        schema = build_canonical_schema()
        result = validate_csv_file(path, schema)

        assert result.valid is False
        range_errors = [e for e in result.errors if e.error_type == "out_of_range"]
        assert len(range_errors) >= 1
        assert any(e.column_name == "HR_5" for e in range_errors)

    def test_validate_csv_wrong_dtype(self, tmp_path: Path) -> None:
        """Validate a bess_units.csv with non-numeric power_mw — expect wrong_dtype."""
        path = tmp_path / "bess_units.csv"
        header = [
            "unit_id",
            "bus_id",
            "power_mw",
            "energy_mwh",
            "efficiency",
            "min_soc",
            "max_soc",
            "init_soc",
        ]
        rows = [
            ["BESS_1", "100", "not_a_number", "400.0", "0.9", "0.1", "0.9", "0.5"],
        ]
        _write_csv(path, header, rows)

        schema = build_canonical_schema()
        result = validate_csv_file(path, schema)

        assert result.valid is False
        dtype_errors = [e for e in result.errors if e.error_type == "wrong_dtype"]
        assert len(dtype_errors) >= 1
        assert any(e.column_name == "power_mw" for e in dtype_errors)
