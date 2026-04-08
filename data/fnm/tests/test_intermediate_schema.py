"""Tests for PRD 07 -- Intermediate Format Schema Specification.

T01-T10: Synthetic tests (no FNM data required).
T11-T14: Integration/end-to-end tests (require FNM_PATH, skip if unset).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fnm.scripts.intermediate_schema import (
    PSSE_V31_RECORD_TYPES,
    PerUnitBase,
    TableSchema,
    detect_inactive_fields,
    get_table_schemas,
    manifest_to_json_schema,
    table_schema_to_json_schema,
    validate_tables,
    write_schemas,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def all_table_schemas() -> list[TableSchema]:
    """Return all 17 table schemas."""
    return get_table_schemas()


@pytest.fixture
def bus_schema() -> TableSchema:
    """Return the Bus table schema."""
    schemas = get_table_schemas()
    return next(ts for ts in schemas if ts.record_type == "Bus")


@pytest.fixture
def bus_json_schema(bus_schema: TableSchema) -> dict:
    """Return the Bus JSON Schema dict."""
    return table_schema_to_json_schema(bus_schema)


# ---------------------------------------------------------------------------
# T01: get_table_schemas covers all 17 types
# ---------------------------------------------------------------------------


def test_get_table_schemas_covers_all_17_types(
    all_table_schemas: list[TableSchema],
) -> None:
    """Call get_table_schemas(). Verify it returns exactly 17 TableSchema
    objects, one per PSS/E v31 record type, in section order."""
    assert len(all_table_schemas) == 17

    returned_types = [ts.record_type for ts in all_table_schemas]
    assert tuple(returned_types) == PSSE_V31_RECORD_TYPES

    for ts in all_table_schemas:
        assert len(ts.fields) > 0, f"{ts.record_type} has no fields"
        assert len(ts.primary_key) > 0, f"{ts.record_type} has no primary_key"
        assert ts.table_name, f"{ts.record_type} has no table_name"
        assert ts.description, f"{ts.record_type} has no description"


# ---------------------------------------------------------------------------
# T02: table_schema_to_json_schema produces valid Draft 2020-12
# ---------------------------------------------------------------------------


def test_table_schema_to_json_schema_valid_draft_2020_12(
    bus_json_schema: dict,
) -> None:
    """Convert the Bus TableSchema to JSON Schema. Verify Draft 2020-12
    structure and validate against the meta-schema."""
    schema = bus_json_schema

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["type"] == "object"
    assert isinstance(schema["properties"], dict)
    assert isinstance(schema["required"], list)
    assert len(schema["properties"]) > 0
    assert "I" in schema["properties"]
    assert "additionalProperties" in schema

    # Verify custom extension keywords are present
    bus_i = schema["properties"]["I"]
    assert "x-psse-unit" in bus_i
    assert "x-psse-per-unit-base" in bus_i
    assert "x-psse-preservation-critical" in bus_i
    assert "x-psse-present-but-inactive" in bus_i
    assert "x-psse-valid-range" in bus_i

    # Validate against meta-schema using jsonschema
    try:
        from jsonschema.validators import Draft202012Validator

        Draft202012Validator.check_schema(schema)
    except ImportError:
        pytest.skip("jsonschema not installed")


# ---------------------------------------------------------------------------
# T03: manifest schema valid Draft 2020-12
# ---------------------------------------------------------------------------


def test_manifest_schema_valid_draft_2020_12() -> None:
    """Call manifest_to_json_schema(). Validate against the meta-schema.
    Verify required manifest properties."""
    schema = manifest_to_json_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["type"] == "object"

    expected_required = {
        "sbase",
        "basfrq",
        "rev",
        "case_id",
        "canonical_parser",
        "tables",
        "total_records",
        "total_tables",
        "non_empty_record_types",
        "schema_version",
        "generated_timestamp",
    }
    assert set(schema["required"]) == expected_required

    # Each expected required property should be in properties
    for prop in expected_required:
        assert prop in schema["properties"], f"Missing property: {prop}"

    try:
        from jsonschema.validators import Draft202012Validator

        Draft202012Validator.check_schema(schema)
    except ImportError:
        pytest.skip("jsonschema not installed")


# ---------------------------------------------------------------------------
# T04: preservation-critical fields present
# ---------------------------------------------------------------------------


def test_preservation_critical_fields_present(
    all_table_schemas: list[TableSchema],
) -> None:
    """Verify that preservation-critical fields are marked correctly."""
    schemas_by_type = {ts.record_type: ts for ts in all_table_schemas}

    # Transformer: K, CW, CZ, CM, WINDV1-3, NOMV1-3, ANG1, RATA1-3
    xfmr = schemas_by_type["Transformer"]
    xfmr_fields = {f.name: f for f in xfmr.fields}
    for fname in [
        "K",
        "CW",
        "CZ",
        "CM",
        "WINDV1",
        "WINDV2",
        "WINDV3",
        "NOMV1",
        "NOMV2",
        "NOMV3",
        "ANG1",
        "RATA1",
        "RATA2",
        "RATA3",
    ]:
        assert fname in xfmr_fields, f"Missing transformer field: {fname}"
        assert xfmr_fields[fname].preservation_critical, (
            f"Transformer.{fname} should be preservation_critical"
        )

    # Switched Shunt: BINIT, N1-N8, B1-B8, MODSW, SWREM
    ss = schemas_by_type["Switched Shunt"]
    ss_fields = {f.name: f for f in ss.fields}
    ss_critical = ["MODSW", "SWREM", "BINIT"]
    for i in range(1, 9):
        ss_critical.extend([f"N{i}", f"B{i}"])
    for fname in ss_critical:
        assert fname in ss_fields, f"Missing switched shunt field: {fname}"
        assert ss_fields[fname].preservation_critical, (
            f"SwitchedShunt.{fname} should be preservation_critical"
        )

    # Generator: IREG
    gen = schemas_by_type["Generator"]
    gen_fields = {f.name: f for f in gen.fields}
    assert gen_fields["IREG"].preservation_critical

    # Area: ISW, PDES, PTOL
    area = schemas_by_type["Area"]
    area_fields = {f.name: f for f in area.fields}
    for fname in ["ISW", "PDES", "PTOL"]:
        assert area_fields[fname].preservation_critical, (
            f"Area.{fname} should be preservation_critical"
        )

    # Multi-Section Line: I, J, ID, DUM1-DUM9
    msl = schemas_by_type["Multi-Section Line"]
    msl_fields = {f.name: f for f in msl.fields}
    for fname in ["I", "J", "ID"] + [f"DUM{i}" for i in range(1, 10)]:
        assert msl_fields[fname].preservation_critical, (
            f"MultiSectionLine.{fname} should be preservation_critical"
        )


# ---------------------------------------------------------------------------
# T05: per-unit base annotations complete
# ---------------------------------------------------------------------------


def test_per_unit_base_annotations_complete(
    all_table_schemas: list[TableSchema],
) -> None:
    """Verify every field has a per-unit base. Check specific expectations."""
    for ts in all_table_schemas:
        for f in ts.fields:
            assert f.per_unit_base is not None, f"{ts.record_type}.{f.name} has None per_unit_base"
            assert isinstance(f.per_unit_base, PerUnitBase), (
                f"{ts.record_type}.{f.name} per_unit_base is not PerUnitBase"
            )

    # Specific checks
    schemas_by_type = {ts.record_type: ts for ts in all_table_schemas}

    # Transformer impedance fields should be MIXED
    xfmr = schemas_by_type["Transformer"]
    xfmr_fields = {f.name: f for f in xfmr.fields}
    for fname in ["R1_2", "X1_2", "R2_3", "X2_3", "R3_1", "X3_1"]:
        assert xfmr_fields[fname].per_unit_base == PerUnitBase.MIXED, (
            f"Transformer.{fname} should be MIXED"
        )

    # Bus VM should be BUS_KV
    bus = schemas_by_type["Bus"]
    bus_fields = {f.name: f for f in bus.fields}
    assert bus_fields["VM"].per_unit_base == PerUnitBase.BUS_KV

    # Branch R should be SYSTEM_MVA
    branch = schemas_by_type["Branch"]
    branch_fields = {f.name: f for f in branch.fields}
    assert branch_fields["R"].per_unit_base == PerUnitBase.SYSTEM_MVA


# ---------------------------------------------------------------------------
# T06: write_schemas creates files
# ---------------------------------------------------------------------------


def test_write_schemas_creates_files(tmp_path: Path) -> None:
    """Call write_schemas() with three types. Verify files are created
    and valid."""
    non_empty = ["Bus", "Generator", "Area"]
    paths = write_schemas(tmp_path, non_empty)

    expected_files = [
        tmp_path / "schemas" / "bus.schema.json",
        tmp_path / "schemas" / "generator.schema.json",
        tmp_path / "schemas" / "area.schema.json",
        tmp_path / "schemas" / "manifest.schema.json",
    ]

    for ef in expected_files:
        assert ef.exists(), f"Expected file not created: {ef}"

    assert len(paths) == len(expected_files)

    # Verify each file is valid JSON and passes meta-schema validation
    try:
        from jsonschema.validators import Draft202012Validator
    except ImportError:
        pytest.skip("jsonschema not installed")

    for ef in expected_files:
        data = json.loads(ef.read_text(encoding="utf-8"))
        assert "$schema" in data
        Draft202012Validator.check_schema(data)


# ---------------------------------------------------------------------------
# T07: write_schemas respects non-empty filter
# ---------------------------------------------------------------------------


def test_write_schemas_respects_non_empty_filter(tmp_path: Path) -> None:
    """Call write_schemas() with only Bus. Verify only bus + manifest
    schemas created."""
    write_schemas(tmp_path, ["Bus"])

    schema_dir = tmp_path / "schemas"
    schema_files = list(schema_dir.glob("*.schema.json"))
    schema_names = {f.name for f in schema_files}

    assert "bus.schema.json" in schema_names
    assert "manifest.schema.json" in schema_names
    assert len(schema_files) == 2, f"Expected 2 files but got {len(schema_files)}: {schema_names}"


# ---------------------------------------------------------------------------
# T08: detect_inactive_fields
# ---------------------------------------------------------------------------


def test_detect_inactive_fields_identifies_uniform_defaults(
    tmp_path: Path,
) -> None:
    """Create synthetic CSV, verify inactive detection."""
    # Write a synthetic bus CSV with NVHI uniform at default (1.1)
    # and VM varying
    csv_dir = tmp_path / "csvs"
    csv_dir.mkdir()

    bus_csv = csv_dir / "bus.csv"
    bus_csv.write_text(
        "I,NAME,BASKV,IDE,AREA,ZONE,OWNER,VM,VA,NVHI,NVLO,EVHI,EVLO\n"
        "1,BUS1,138.0,1,1,1,1,0.98,0.0,1.1,0.9,1.1,0.9\n"
        "2,BUS2,138.0,1,1,1,1,1.01,0.0,1.1,0.9,1.1,0.9\n"
        "3,BUS3,138.0,1,1,1,1,1.05,0.0,1.1,0.9,1.1,0.9\n",
        encoding="utf-8",
    )

    result = detect_inactive_fields(
        csv_dir=csv_dir,
        non_empty_types=["Bus"],
        record_type_to_table_name={"Bus": "bus"},
    )

    assert "Bus" in result
    inactive = result["Bus"]
    assert "NVHI" in inactive
    assert "VM" not in inactive


# ---------------------------------------------------------------------------
# T09: validate_tables conformant
# ---------------------------------------------------------------------------


def test_validate_tables_conformant(tmp_path: Path) -> None:
    """Create conformant CSVs and schemas, verify is_conformant == True."""
    # Write schemas
    non_empty = ["Bus", "Generator"]
    write_schemas(tmp_path, non_empty)

    # Create CSV directory
    csv_dir = tmp_path / "tables"
    csv_dir.mkdir()

    # Bus CSV
    bus_csv = csv_dir / "bus.csv"
    bus_csv.write_text(
        "I,NAME,BASKV,IDE,AREA,ZONE,OWNER,VM,VA,NVHI,NVLO,EVHI,EVLO\n"
        "1,BUS1,138.0,1,1,1,1,1.0,0.0,1.1,0.9,1.1,0.9\n"
        "2,BUS2,345.0,2,1,1,1,1.02,5.0,1.1,0.9,1.1,0.9\n",
        encoding="utf-8",
    )

    # Generator CSV -- include all required fields
    gen_schema = get_table_schemas()
    gen_ts = next(ts for ts in gen_schema if ts.record_type == "Generator")
    gen_required = [f.name for f in gen_ts.fields if f.required]
    gen_header = ",".join(gen_required)
    gen_row1_vals = []
    gen_row2_vals = []
    for f in gen_ts.fields:
        if not f.required:
            continue
        if f.data_type == "integer":
            gen_row1_vals.append("1")
            gen_row2_vals.append("2")
        elif f.data_type == "number":
            gen_row1_vals.append("100.0")
            gen_row2_vals.append("200.0")
        else:
            gen_row1_vals.append("G1")
            gen_row2_vals.append("G2")

    gen_csv = csv_dir / "generator.csv"
    gen_csv.write_text(
        gen_header + "\n" + ",".join(gen_row1_vals) + "\n" + ",".join(gen_row2_vals) + "\n",
        encoding="utf-8",
    )

    # Create manifest
    manifest = {
        "sbase": 100.0,
        "basfrq": 60.0,
        "rev": 31.0,
        "case_id": "Test Case",
        "canonical_parser": "gridcal",
        "tables": [
            {
                "table_name": "bus",
                "record_type": "Bus",
                "file_name": "bus.csv",
                "record_count": 2,
                "column_count": 13,
                "schema_file": "schemas/bus.schema.json",
            },
            {
                "table_name": "generator",
                "record_type": "Generator",
                "file_name": "generator.csv",
                "record_count": 2,
                "column_count": len(gen_required),
                "schema_file": "schemas/generator.schema.json",
            },
        ],
        "total_records": 4,
        "total_tables": 2,
        "non_empty_record_types": ["Bus", "Generator"],
        "schema_version": "1.0.0",
        "generated_timestamp": "2026-01-01T00:00:00Z",
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = validate_tables(
        csv_dir=csv_dir,
        schema_dir=tmp_path / "schemas",
        manifest_path=manifest_path,
    )

    assert report.is_conformant, (
        f"Expected conformant but got errors: {[f.message for f in report.errors]}"
    )
    assert len(report.errors) == 0


# ---------------------------------------------------------------------------
# T10: validate_tables missing required field
# ---------------------------------------------------------------------------


def test_validate_tables_missing_required_field(tmp_path: Path) -> None:
    """Create bus.csv missing required I column. Verify error."""
    # Write schemas
    write_schemas(tmp_path, ["Bus"])

    csv_dir = tmp_path / "tables"
    csv_dir.mkdir()

    # Bus CSV missing 'I' column
    bus_csv = csv_dir / "bus.csv"
    bus_csv.write_text(
        "NAME,BASKV,IDE,AREA,ZONE,OWNER,VM,VA\nBUS1,138.0,1,1,1,1,1.0,0.0\n",
        encoding="utf-8",
    )

    manifest = {
        "sbase": 100.0,
        "basfrq": 60.0,
        "rev": 31.0,
        "case_id": "Test",
        "canonical_parser": "gridcal",
        "tables": [
            {
                "table_name": "bus",
                "record_type": "Bus",
                "file_name": "bus.csv",
                "record_count": 1,
                "column_count": 8,
                "schema_file": "schemas/bus.schema.json",
            },
        ],
        "total_records": 1,
        "total_tables": 1,
        "non_empty_record_types": ["Bus"],
        "schema_version": "1.0.0",
        "generated_timestamp": "2026-01-01T00:00:00Z",
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = validate_tables(
        csv_dir=csv_dir,
        schema_dir=tmp_path / "schemas",
        manifest_path=manifest_path,
    )

    assert not report.is_conformant
    error_ids = [f.check_id for f in report.errors]
    assert "missing_required_field" in error_ids

    # Verify it specifically notes field 'I' in table 'bus'
    matching = [
        f
        for f in report.errors
        if f.check_id == "missing_required_field" and f.field_name == "I" and f.table_name == "bus"
    ]
    assert len(matching) > 0


# ---------------------------------------------------------------------------
# T11-T14: Integration tests (require FNM_PATH) - marked with @pytest.mark.fnm
# ---------------------------------------------------------------------------


@pytest.mark.fnm
def test_write_schemas_for_fnm_non_empty_types(require_fnm: dict, tmp_path: Path) -> None:
    """T11: Load D3 raw record count summary, write schemas for all
    non-empty types."""
    repo_root = Path(require_fnm.get("repo_root", "."))
    raw_counts_path = repo_root / "data" / "fnm" / "intermediate" / "raw_counts.json"
    if not raw_counts_path.exists():
        pytest.skip("D3 raw_counts.json not found")

    raw_data = json.loads(raw_counts_path.read_text(encoding="utf-8"))
    non_empty = raw_data.get("non_empty_sections", [])
    assert len(non_empty) > 0

    paths = write_schemas(tmp_path, non_empty)

    # Verify a schema file for every non-empty type
    for rt in non_empty:
        table_name = rt.lower().replace(" ", "_").replace("-", "_")
        schema_path = tmp_path / "schemas" / f"{table_name}.schema.json"
        assert schema_path.exists(), f"Missing schema for {rt}"

    try:
        from jsonschema.validators import Draft202012Validator

        for p in paths:
            data = json.loads(p.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(data)
    except ImportError:
        pass  # jsonschema not required for this assertion


@pytest.mark.fnm
def test_inactive_fields_detected_from_canonical_parser(require_fnm: dict, tmp_path: Path) -> None:
    """T12: Detect inactive fields from canonical parser CSV exports."""
    repo_root = Path(require_fnm.get("repo_root", "."))
    raw_counts_path = repo_root / "data" / "fnm" / "intermediate" / "raw_counts.json"
    if not raw_counts_path.exists():
        pytest.skip("D3 raw_counts.json not found")

    raw_data = json.loads(raw_counts_path.read_text(encoding="utf-8"))
    non_empty = raw_data.get("non_empty_sections", [])

    # Try to find canonical parser CSV directory
    csv_dir = repo_root / "data" / "fnm" / "intermediate" / "csvs"
    if not csv_dir.exists():
        pytest.skip("Canonical parser CSV directory not found")

    rt_to_tn = {rt: rt.lower().replace(" ", "_").replace("-", "_") for rt in non_empty}

    result = detect_inactive_fields(csv_dir, non_empty, rt_to_tn)

    # At least some fields should be inactive in a large model
    assert isinstance(result, dict)
    # Log for manual review
    for rt, fields in sorted(result.items()):
        print(f"  {rt}: {fields}")


@pytest.mark.fnm
def test_generate_subcommand_produces_all_outputs(require_fnm: dict, tmp_path: Path) -> None:
    """T13: Run generate subcommand, verify output files."""
    from fnm.scripts.intermediate_schema import main as schema_main

    repo_root = Path(require_fnm.get("repo_root", "."))
    raw_counts_path = repo_root / "data" / "fnm" / "intermediate" / "raw_counts.json"
    if not raw_counts_path.exists():
        pytest.skip("D3 raw_counts.json not found")

    raw_data = json.loads(raw_counts_path.read_text(encoding="utf-8"))
    non_empty = raw_data.get("non_empty_sections", [])

    schema_main(
        [
            "generate",
            "--raw-summary",
            str(raw_counts_path),
            "-o",
            str(tmp_path),
        ]
    )

    # Verify schemas directory
    schema_dir = tmp_path / "schemas"
    assert schema_dir.exists()
    schema_files = list(schema_dir.glob("*.schema.json"))
    assert len(schema_files) >= len(non_empty) + 1  # +1 for manifest

    # Verify markdown reference
    md_path = tmp_path / "intermediate_format_reference.md"
    assert md_path.exists()
    md_text = md_path.read_text(encoding="utf-8")
    for rt in non_empty:
        assert rt in md_text, f"Markdown missing section for {rt}"


@pytest.mark.fnm
def test_validate_subcommand_on_canonical_output(require_fnm: dict, tmp_path: Path) -> None:
    """T14: Validate canonical parser CSV exports against generated schemas."""
    from fnm.scripts.intermediate_schema import main as schema_main

    repo_root = Path(require_fnm.get("repo_root", "."))
    raw_counts_path = repo_root / "data" / "fnm" / "intermediate" / "raw_counts.json"
    csv_dir = repo_root / "data" / "fnm" / "intermediate" / "csvs"

    if not raw_counts_path.exists():
        pytest.skip("D3 raw_counts.json not found")
    if not csv_dir.exists():
        pytest.skip("Canonical parser CSV directory not found")

    # Generate schemas first
    schema_main(
        [
            "generate",
            "--raw-summary",
            str(raw_counts_path),
            "-o",
            str(tmp_path),
        ]
    )

    # Create a synthetic manifest for the canonical CSVs
    raw_data = json.loads(raw_counts_path.read_text(encoding="utf-8"))
    non_empty = raw_data.get("non_empty_sections", [])

    tables_entries = []
    for rt in non_empty:
        tn = rt.lower().replace(" ", "_").replace("-", "_")
        csv_path = csv_dir / f"{tn}.csv"
        if csv_path.exists():
            tables_entries.append(
                {
                    "table_name": tn,
                    "record_type": rt,
                    "file_name": f"{tn}.csv",
                    "record_count": 0,  # placeholder
                    "column_count": 1,  # placeholder
                    "schema_file": f"schemas/{tn}.schema.json",
                }
            )

    manifest = {
        "sbase": 100.0,
        "basfrq": 60.0,
        "rev": 31.0,
        "case_id": "FNM",
        "canonical_parser": "gridcal",
        "tables": tables_entries,
        "total_records": 0,
        "total_tables": len(tables_entries),
        "non_empty_record_types": non_empty,
        "schema_version": "1.0.0",
        "generated_timestamp": "2026-01-01T00:00:00Z",
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    # Run validate
    schema_main(
        [
            "validate",
            "--csv-dir",
            str(csv_dir),
            "--schema-dir",
            str(tmp_path / "schemas"),
            "--manifest",
            str(manifest_path),
            "-o",
            str(tmp_path),
        ]
    )

    report_path = tmp_path / "conformance_report.json"
    assert report_path.exists()
    report_data = json.loads(report_path.read_text(encoding="utf-8"))
    print(
        f"  Conformance: errors={len(report_data['errors'])}, "
        f"warnings={len(report_data['warnings'])}, "
        f"info={len(report_data['info'])}"
    )
