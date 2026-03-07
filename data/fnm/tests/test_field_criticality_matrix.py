"""Structural validation tests for the field criticality matrix document.

Tests verify that data/fnm/docs/field-criticality-matrix.md contains all required
sections, classifies every schema field, maintains count consistency, and respects
Phase 1 D7 JSON Schema annotations (x-psse-present-but-inactive, x-psse-preservation-critical)
as specified in PRD 02/05.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DOC_PATH = REPO_ROOT / "data" / "fnm" / "docs" / "field-criticality-matrix.md"
SCHEMAS_DIR = REPO_ROOT / "data" / "fnm" / "intermediate" / "schemas"
MAPPING_GUIDE_PATH = REPO_ROOT / "data" / "fnm" / "docs" / "mapping-guide.md"

VALID_TIERS = {"DCPF-critical", "ACPF-critical", "Informational", "Discardable"}

# Schema filename to display name mapping (matches the document H2 headings)
SCHEMA_DISPLAY_NAMES: dict[str, str] = {
    "bus": "Bus",
    "load": "Load",
    "fixed_shunt": "Fixed Shunt",
    "generator": "Generator",
    "branch": "Branch",
    "transformer": "Transformer",
    "area": "Area",
    "two_terminal_dc": "Two-Terminal DC",
    "vsc_dc": "VSC DC",
    "impedance_correction": "Impedance Correction",
    "multi_terminal_dc": "Multi-Terminal DC",
    "multi_section_line": "Multi-Section Line",
    "zone": "Zone",
    "interarea_transfer": "Interarea Transfer",
    "owner": "Owner",
    "facts": "FACTS",
    "switched_shunt": "Switched Shunt",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_schema(name: str) -> dict:
    """Load a JSON Schema file by record-type name (without .schema.json)."""
    path = SCHEMAS_DIR / f"{name}.schema.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _non_manifest_schemas() -> list[str]:
    """Return sorted list of non-manifest schema basenames (without extension)."""
    schemas = []
    for p in sorted(SCHEMAS_DIR.glob("*.schema.json")):
        name = p.stem.replace(".schema", "")
        if name != "manifest":
            schemas.append(name)
    return schemas


def _split_h2_sections(text: str) -> dict[str, str]:
    """Split markdown text into H2 sections keyed by heading."""
    sections: dict[str, str] = {}
    current_heading = ""
    current_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## ") and not line.startswith("### "):
            if current_heading:
                sections[current_heading] = "\n".join(current_lines)
            current_heading = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_heading:
        sections[current_heading] = "\n".join(current_lines)
    return sections


def _parse_field_table(section_body: str) -> list[dict[str, str]]:
    """Parse a pipe-delimited markdown table from a section body.

    Returns a list of dicts with keys: Field, Type, Tier, Rationale.
    """
    rows: list[dict[str, str]] = []
    in_table = False
    header_found = False
    for line in section_body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table:
                break
            continue
        parts = [p.strip() for p in stripped.split("|")]
        parts = [p for p in parts if p]
        if len(parts) < 4:
            continue
        if "Field" in parts[0] and "Type" in parts[1] and "Tier" in parts[2]:
            header_found = True
            continue
        if header_found and stripped.startswith("|--"):
            in_table = True
            continue
        if in_table:
            # Strip backticks from field name
            field = parts[0].strip("`").strip()
            rows.append(
                {
                    "Field": field,
                    "Type": parts[1],
                    "Tier": parts[2],
                    "Rationale": parts[3] if len(parts) > 3 else "",
                }
            )
    return rows


def _parse_summary_table(section_body: str) -> list[dict[str, str | int]]:
    """Parse the summary table from the Summary section body.

    Returns a list of dicts with keys: Record Type, Total, DCPF-Critical,
    ACPF-Critical, Informational, Discardable.
    """
    rows: list[dict[str, str | int]] = []
    in_table = False
    header_found = False
    for line in section_body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table:
                break
            continue
        parts = [p.strip() for p in stripped.split("|")]
        parts = [p for p in parts if p]
        if len(parts) < 6:
            continue
        if "Record Type" in parts[0] and "Total" in parts[1]:
            header_found = True
            continue
        if header_found and stripped.startswith("|--"):
            in_table = True
            continue
        if in_table:
            # Strip markdown bold
            rt = parts[0].replace("**", "").strip()
            try:
                total = int(parts[1].replace("**", "").strip())
                dcpf = int(parts[2].replace("**", "").strip())
                acpf = int(parts[3].replace("**", "").strip())
                info = int(parts[4].replace("**", "").strip())
                disc = int(parts[5].replace("**", "").strip())
            except ValueError:
                continue
            rows.append(
                {
                    "Record Type": rt,
                    "Total": total,
                    "DCPF-Critical": dcpf,
                    "ACPF-Critical": acpf,
                    "Informational": info,
                    "Discardable": disc,
                }
            )
    return rows


def _get_tier3_record_types() -> set[str]:
    """Parse the mapping guide to find Tier 3 record types.

    Returns a set of display names (e.g., 'Zone', 'Owner').
    """
    if not MAPPING_GUIDE_PATH.exists():
        return set()
    text = MAPPING_GUIDE_PATH.read_text(encoding="utf-8")
    tier3: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        parts = [p.strip() for p in stripped.split("|")]
        parts = [p for p in parts if p]
        if len(parts) < 5:
            continue
        # Look for rows where the Tier column (index 3) is "3"
        if parts[3].strip() == "3":
            tier3.add(parts[1].strip())
    return tier3


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def doc_text() -> str:
    """Read the field criticality matrix document."""
    assert DOC_PATH.exists(), f"Document not found at {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def doc_sections(doc_text: str) -> dict[str, str]:
    """Split the document into H2 sections."""
    return _split_h2_sections(doc_text)


@pytest.fixture(scope="module")
def schema_names() -> list[str]:
    """Return all non-manifest schema basenames."""
    return _non_manifest_schemas()


@pytest.fixture(scope="module")
def record_type_field_tables(doc_sections: dict[str, str]) -> dict[str, list[dict[str, str]]]:
    """Parse field classification tables for all record-type sections."""
    tables: dict[str, list[dict[str, str]]] = {}
    for display_name in SCHEMA_DISPLAY_NAMES.values():
        if display_name in doc_sections:
            tables[display_name] = _parse_field_table(doc_sections[display_name])
    return tables


@pytest.fixture(scope="module")
def summary_rows(doc_sections: dict[str, str]) -> list[dict[str, str | int]]:
    """Parse summary table rows."""
    assert "Summary" in doc_sections, "Summary section not found"
    return _parse_summary_table(doc_sections["Summary"])


# ---------------------------------------------------------------------------
# T01-T05: Structural validation tests
# ---------------------------------------------------------------------------


@pytest.mark.docs
def test_document_exists() -> None:
    """T01: Verify the document exists and is non-empty."""
    assert DOC_PATH.exists(), f"Document not found at {DOC_PATH}"
    content = DOC_PATH.read_text(encoding="utf-8")
    assert len(content.strip()) > 0, "Document is empty"


@pytest.mark.docs
def test_tier_definitions_section_present(doc_sections: dict[str, str]) -> None:
    """T02: Verify Tier Definitions section with exactly 4 tier rows."""
    assert "Tier Definitions" in doc_sections, "Missing '## Tier Definitions' section"
    body = doc_sections["Tier Definitions"]
    # Check that all four tier labels appear
    for tier_label in ("DCPF-critical", "ACPF-critical", "Informational", "Discardable"):
        assert tier_label in body, f"Tier label '{tier_label}' not found in Tier Definitions"
    # Count table data rows (exclude header and separator)
    tier_rows = 0
    in_table = False
    header_found = False
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if "Tier" in stripped and "Label" in stripped:
            header_found = True
            continue
        if header_found and stripped.startswith("|--"):
            in_table = True
            continue
        if in_table:
            tier_rows += 1
    assert tier_rows == 4, f"Expected 4 tier definition rows, found {tier_rows}"


@pytest.mark.docs
def test_summary_table_present_and_complete(
    summary_rows: list[dict[str, str | int]],
    schema_names: list[str],
) -> None:
    """T03: Verify summary table has one row per non-empty record type plus grand total."""
    summary_rt_names = {str(r["Record Type"]) for r in summary_rows}
    # Should have a 'Total' row
    assert "Total" in summary_rt_names, "Missing grand total row in summary table"
    # All non-manifest schemas should have a summary row
    for schema_name in schema_names:
        display = SCHEMA_DISPLAY_NAMES.get(schema_name, schema_name)
        assert display in summary_rt_names, (
            f"Missing summary row for record type '{display}' (schema: {schema_name})"
        )
    # Verify required columns exist (implicitly verified by parsing)
    for row in summary_rows:
        for col in (
            "Record Type",
            "Total",
            "DCPF-Critical",
            "ACPF-Critical",
            "Informational",
            "Discardable",
        ):
            assert col in row, f"Missing column '{col}' in summary row {row}"


@pytest.mark.docs
def test_every_non_empty_record_type_has_section(
    doc_sections: dict[str, str],
    schema_names: list[str],
) -> None:
    """T04: Verify every non-manifest schema has an H2 section."""
    for schema_name in schema_names:
        display = SCHEMA_DISPLAY_NAMES.get(schema_name, schema_name)
        assert display in doc_sections, (
            f"Missing H2 section for record type '{display}' (schema: {schema_name})"
        )


@pytest.mark.docs
def test_field_tables_have_required_columns(
    record_type_field_tables: dict[str, list[dict[str, str]]],
) -> None:
    """T05: Verify each field table has Field, Type, Tier, Rationale columns."""
    for rt_name, rows in record_type_field_tables.items():
        assert len(rows) > 0, f"No field rows found in table for '{rt_name}'"
        for row in rows:
            for col in ("Field", "Type", "Tier", "Rationale"):
                assert col in row, f"Missing column '{col}' in field table for '{rt_name}'"


# ---------------------------------------------------------------------------
# T06-T08: Field coverage tests
# ---------------------------------------------------------------------------


@pytest.mark.docs
def test_all_schema_fields_classified(
    record_type_field_tables: dict[str, list[dict[str, str]]],
    schema_names: list[str],
) -> None:
    """T06: Verify every JSON Schema property appears in the classification table."""
    for schema_name in schema_names:
        schema = _load_schema(schema_name)
        schema_fields = set(schema.get("properties", {}).keys())
        display = SCHEMA_DISPLAY_NAMES.get(schema_name, schema_name)
        assert display in record_type_field_tables, (
            f"No field table found for '{display}' (schema: {schema_name})"
        )
        doc_fields = {row["Field"] for row in record_type_field_tables[display]}
        missing = schema_fields - doc_fields
        assert not missing, f"Fields missing from '{display}' table: {sorted(missing)}"


@pytest.mark.docs
def test_no_duplicate_fields_per_record_type(
    record_type_field_tables: dict[str, list[dict[str, str]]],
) -> None:
    """T07: Verify no field name appears more than once in a single record type."""
    for rt_name, rows in record_type_field_tables.items():
        fields = [row["Field"] for row in rows]
        seen: set[str] = set()
        duplicates: set[str] = set()
        for f in fields:
            if f in seen:
                duplicates.add(f)
            seen.add(f)
        assert not duplicates, f"Duplicate fields in '{rt_name}': {sorted(duplicates)}"


@pytest.mark.docs
def test_all_tier_values_valid(
    record_type_field_tables: dict[str, list[dict[str, str]]],
) -> None:
    """T08: Verify every Tier cell contains a valid tier label."""
    for rt_name, rows in record_type_field_tables.items():
        for row in rows:
            tier = row["Tier"]
            assert tier in VALID_TIERS, (
                f"Invalid tier '{tier}' for field '{row['Field']}' in '{rt_name}'. "
                f"Must be one of: {sorted(VALID_TIERS)}"
            )


# ---------------------------------------------------------------------------
# T09-T12: Consistency tests
# ---------------------------------------------------------------------------


@pytest.mark.docs
def test_summary_counts_match_detail_tables(
    summary_rows: list[dict[str, str | int]],
    record_type_field_tables: dict[str, list[dict[str, str]]],
) -> None:
    """T09: Verify per-tier counts in summary match the detail tables."""
    summary_by_rt = {str(r["Record Type"]): r for r in summary_rows}
    for rt_name, rows in record_type_field_tables.items():
        assert rt_name in summary_by_rt, (
            f"Record type '{rt_name}' in detail tables but not in summary"
        )
        summary = summary_by_rt[rt_name]
        # Count tiers from detail table
        tier_counts: dict[str, int] = {t: 0 for t in VALID_TIERS}
        for row in rows:
            tier_counts[row["Tier"]] += 1
        total = len(rows)
        # Verify total
        assert total == summary["Total"], (
            f"'{rt_name}': detail table has {total} rows but summary Total is {summary['Total']}"
        )
        # Verify per-tier counts
        assert tier_counts["DCPF-critical"] == summary["DCPF-Critical"], (
            f"'{rt_name}': DCPF-Critical mismatch: "
            f"detail={tier_counts['DCPF-critical']}, summary={summary['DCPF-Critical']}"
        )
        assert tier_counts["ACPF-critical"] == summary["ACPF-Critical"], (
            f"'{rt_name}': ACPF-Critical mismatch: "
            f"detail={tier_counts['ACPF-critical']}, summary={summary['ACPF-Critical']}"
        )
        assert tier_counts["Informational"] == summary["Informational"], (
            f"'{rt_name}': Informational mismatch: "
            f"detail={tier_counts['Informational']}, summary={summary['Informational']}"
        )
        assert tier_counts["Discardable"] == summary["Discardable"], (
            f"'{rt_name}': Discardable mismatch: "
            f"detail={tier_counts['Discardable']}, summary={summary['Discardable']}"
        )
        # Verify Total = sum of tiers
        tier_sum = sum(tier_counts.values())
        assert tier_sum == summary["Total"], (
            f"'{rt_name}': Tier sum ({tier_sum}) != Total ({summary['Total']})"
        )


@pytest.mark.docs
def test_grand_total_row_correct(
    summary_rows: list[dict[str, str | int]],
) -> None:
    """T10: Verify the grand total row equals column-wise sum of all per-record-type rows."""
    grand_total = None
    rt_rows = []
    for row in summary_rows:
        if str(row["Record Type"]) == "Total":
            grand_total = row
        else:
            rt_rows.append(row)
    assert grand_total is not None, "Grand total row not found in summary"
    for col in ("Total", "DCPF-Critical", "ACPF-Critical", "Informational", "Discardable"):
        expected = sum(int(r[col]) for r in rt_rows)
        actual = int(grand_total[col])
        assert actual == expected, f"Grand total '{col}': expected {expected}, got {actual}"


@pytest.mark.docs
def test_present_but_inactive_fields_are_discardable(
    record_type_field_tables: dict[str, list[dict[str, str]]],
    schema_names: list[str],
) -> None:
    """T11: Every field with x-psse-present-but-inactive must be Discardable."""
    for schema_name in schema_names:
        schema = _load_schema(schema_name)
        display = SCHEMA_DISPLAY_NAMES.get(schema_name, schema_name)
        if display not in record_type_field_tables:
            continue
        doc_fields = {row["Field"]: row for row in record_type_field_tables[display]}
        for field_name, field_spec in schema.get("properties", {}).items():
            if field_spec.get("x-psse-present-but-inactive", False):
                assert field_name in doc_fields, (
                    f"Present-but-inactive field '{field_name}' in '{display}' "
                    f"not found in field table"
                )
                assert doc_fields[field_name]["Tier"] == "Discardable", (
                    f"Present-but-inactive field '{field_name}' in '{display}' "
                    f"should be Discardable, got '{doc_fields[field_name]['Tier']}'"
                )


@pytest.mark.docs
def test_preservation_critical_fields_are_dcpf_or_acpf(
    record_type_field_tables: dict[str, list[dict[str, str]]],
    schema_names: list[str],
) -> None:
    """T12: Every field with x-psse-preservation-critical must be DCPF or ACPF-critical."""
    allowed = {"DCPF-critical", "ACPF-critical"}
    for schema_name in schema_names:
        schema = _load_schema(schema_name)
        display = SCHEMA_DISPLAY_NAMES.get(schema_name, schema_name)
        if display not in record_type_field_tables:
            continue
        doc_fields = {row["Field"]: row for row in record_type_field_tables[display]}
        for field_name, field_spec in schema.get("properties", {}).items():
            if field_spec.get("x-psse-preservation-critical", False):
                assert field_name in doc_fields, (
                    f"Preservation-critical field '{field_name}' in '{display}' "
                    f"not found in field table"
                )
                tier = doc_fields[field_name]["Tier"]
                assert tier in allowed, (
                    f"Preservation-critical field '{field_name}' in '{display}' "
                    f"must be DCPF-critical or ACPF-critical, got '{tier}'"
                )


# ---------------------------------------------------------------------------
# T13-T14: Cross-reference and constraint tests
# ---------------------------------------------------------------------------


@pytest.mark.docs
def test_tier3_record_types_have_no_dcpf_or_acpf_fields(
    record_type_field_tables: dict[str, list[dict[str, str]]],
) -> None:
    """T13: No field in a Tier 3 record type may be DCPF-critical or ACPF-critical."""
    tier3_types = _get_tier3_record_types()
    forbidden = {"DCPF-critical", "ACPF-critical"}
    for display_name in tier3_types:
        if display_name not in record_type_field_tables:
            continue
        for row in record_type_field_tables[display_name]:
            assert row["Tier"] not in forbidden, (
                f"Tier 3 record type '{display_name}' has field '{row['Field']}' "
                f"classified as '{row['Tier']}' -- must be Informational or Discardable"
            )


@pytest.mark.docs
def test_rationale_column_non_empty_and_non_generic(
    record_type_field_tables: dict[str, list[dict[str, str]]],
) -> None:
    """T14: Every rationale must be non-empty, non-generic, and at least 8 words."""
    generic_rationales = {
        "dcpf-critical",
        "acpf-critical",
        "informational",
        "discardable",
        "needed for power flow",
        "power flow",
        "not needed",
    }
    for rt_name, rows in record_type_field_tables.items():
        for row in rows:
            rationale = row["Rationale"].strip()
            assert len(rationale) > 0, f"Empty rationale for field '{row['Field']}' in '{rt_name}'"
            # Check word count
            words = rationale.split()
            assert len(words) >= 8, (
                f"Rationale for '{row['Field']}' in '{rt_name}' has only {len(words)} "
                f"words (minimum 8): '{rationale}'"
            )
            # Check not solely a generic phrase
            rationale_lower = rationale.lower().strip().rstrip(".")
            assert rationale_lower not in generic_rationales, (
                f"Generic rationale for '{row['Field']}' in '{rt_name}': '{rationale}'"
            )
