"""Tests for PRD 04/01 -- Supplemental CSV Reference Documentation.

Validates the document at data/fnm/docs/supplemental-csvs.md for structural
completeness, content consistency, and cross-reference integrity.

Tests T01-T15 are pure markdown parsing tests using pathlib, re, and pytest.
Test T16 requires FNM_PATH and validates field counts against actual CSV headers.
"""

from __future__ import annotations

import csv
import os
import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths (relative to repo root)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DOC_PATH = _REPO_ROOT / "fnm" / "docs" / "supplemental-csvs.md"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXPECTED_CSVS: list[str] = [
    "LINE_AND_TRANSFORMER.csv",
    "TRADING_HUB.csv",
    "GEN_DISTRIBUTION_FACTOR.csv",
    "CONTINGENCY.csv",
    "INTERFACE.csv",
    "INTERFACE_ELEMENT.csv",
    "OUTAGE.csv",
]

EXPECTED_TOOLS: list[str] = [
    "PyPSA",
    "pandapower",
    "GridCal",
    "PowerModels.jl",
    "PowerSimulations.jl",
    "MATPOWER",
]

VALID_DOMAINS: set[str] = {"Transmission", "Generation", "Market", "Outage"}

REQUIRED_CSV_SUBSECTIONS: list[str] = [
    "### Join Keys",
    "### Fields",
    "### Representability",
    "### Summary",
    "### Key Findings",
]

FIELD_TABLE_COLUMNS: list[str] = ["Field", "Type", "Semantic Description", "Example", "Join Key"]

REPR_TABLE_COLUMNS: list[str] = [
    "Field",
    "PyPSA",
    "pandapower",
    "GridCal",
    "PowerModels.jl",
    "PowerSimulations.jl",
    "MATPOWER",
]

SUMMARY_TABLE_COLUMNS: list[str] = [
    "Tool",
    "Native (N)",
    "Extension (E)",
    "External (X)",
    "N%",
    "E%",
    "X%",
]

EXT_MECH_COLUMNS: list[str] = [
    "Tool",
    "Extension Mechanism",
    "Mechanism Description",
    "Citation",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_doc() -> str:
    """Read the supplemental CSV reference document."""
    assert _DOC_PATH.exists(), f"Document not found: {_DOC_PATH}"
    return _DOC_PATH.read_text(encoding="utf-8")


def _get_csv_section(doc: str, csv_name: str) -> str:
    """Extract the full H2 section for a specific CSV."""
    pattern = rf"^## {re.escape(csv_name)}\s*\n(.*?)(?=\n## [^#]|\Z)"
    match = re.search(pattern, doc, re.MULTILINE | re.DOTALL)
    assert match is not None, f"Section not found for {csv_name}"
    return match.group(0)


def _parse_table(text: str, heading: str) -> list[dict[str, str]]:
    """Parse a markdown table following a given heading into list of row dicts.

    Searches for the heading, then reads the next markdown table found.
    Returns a list of dicts with column headers as keys.
    """
    # Find heading position
    heading_pattern = rf"^{re.escape(heading)}\s*$"
    heading_match = re.search(heading_pattern, text, re.MULTILINE)
    if heading_match is None:
        return []

    remaining = text[heading_match.end() :]

    # Find the first table (lines starting with |)
    table_lines: list[str] = []
    in_table = False
    for line in remaining.split("\n"):
        stripped = line.strip()
        if stripped.startswith("|"):
            in_table = True
            table_lines.append(stripped)
        elif in_table:
            break

    if len(table_lines) < 3:
        return []

    # Parse header
    header_line = table_lines[0]
    headers = [h.strip() for h in header_line.strip("|").split("|")]

    # Skip separator line (index 1), parse data rows
    rows: list[dict[str, str]] = []
    for row_line in table_lines[2:]:
        cells = [c.strip() for c in row_line.strip("|").split("|")]
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))

    return rows


def _parse_first_table_after(text: str, start_pos: int) -> list[dict[str, str]]:
    """Parse the first markdown table found after a given position in text."""
    remaining = text[start_pos:]
    table_lines: list[str] = []
    in_table = False
    for line in remaining.split("\n"):
        stripped = line.strip()
        if stripped.startswith("|"):
            in_table = True
            table_lines.append(stripped)
        elif in_table:
            break

    if len(table_lines) < 3:
        return []

    header_line = table_lines[0]
    headers = [h.strip() for h in header_line.strip("|").split("|")]

    rows: list[dict[str, str]] = []
    for row_line in table_lines[2:]:
        cells = [c.strip() for c in row_line.strip("|").split("|")]
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))

    return rows


def _get_table_columns(text: str, heading: str) -> list[str]:
    """Extract column headers from the markdown table following a heading."""
    heading_pattern = rf"^{re.escape(heading)}\s*$"
    heading_match = re.search(heading_pattern, text, re.MULTILINE)
    if heading_match is None:
        return []

    remaining = text[heading_match.end() :]
    for line in remaining.split("\n"):
        stripped = line.strip()
        if stripped.startswith("|"):
            return [h.strip() for h in stripped.strip("|").split("|")]
    return []


# ---------------------------------------------------------------------------
# T01: Document exists
# ---------------------------------------------------------------------------


def test_document_exists() -> None:
    """Verify that data/fnm/docs/supplemental-csvs.md exists and is non-empty."""
    assert _DOC_PATH.exists(), f"Document not found: {_DOC_PATH}"
    content = _DOC_PATH.read_text(encoding="utf-8")
    assert len(content.strip()) > 0, "Document is empty"


# ---------------------------------------------------------------------------
# T02: All 7 CSVs have sections
# ---------------------------------------------------------------------------


def test_all_7_csvs_have_sections() -> None:
    """Verify all 7 supplemental CSVs each have an H2 section matching the CSV file name."""
    doc = _read_doc()
    for csv_name in EXPECTED_CSVS:
        pattern = rf"^## {re.escape(csv_name)}\s*$"
        match = re.search(pattern, doc, re.MULTILINE)
        assert match is not None, f"Missing H2 section for {csv_name}"


# ---------------------------------------------------------------------------
# T03: CSV overview table has 7 rows
# ---------------------------------------------------------------------------


def test_csv_overview_table_has_7_rows() -> None:
    """Parse the CSV Overview table and verify it contains exactly 7 rows."""
    doc = _read_doc()
    rows = _parse_table(doc, "## CSV Overview")
    assert len(rows) == 7, f"Expected 7 rows in CSV Overview table, got {len(rows)}"

    # Verify required columns
    required_cols = [
        "CSV File",
        "Domain",
        "Purpose",
        "Columns",
        "Join Target",
        "Join Cardinality",
        "Join Match Rate",
    ]
    if rows:
        actual_cols = list(rows[0].keys())
        for col in required_cols:
            assert col in actual_cols, f"Missing column '{col}' in CSV Overview table"


# ---------------------------------------------------------------------------
# T04: Every CSV section has required subsections
# ---------------------------------------------------------------------------


def test_every_csv_section_has_required_subsections() -> None:
    """For each CSV section: verify presence of required subsections."""
    doc = _read_doc()
    for csv_name in EXPECTED_CSVS:
        section = _get_csv_section(doc, csv_name)
        for subsection in REQUIRED_CSV_SUBSECTIONS:
            assert subsection in section, (
                f"Missing subsection '{subsection}' in section for {csv_name}"
            )


# ---------------------------------------------------------------------------
# T05: Field tables have required columns
# ---------------------------------------------------------------------------


def test_field_tables_have_required_columns() -> None:
    """For each CSV's Fields table: verify required columns."""
    doc = _read_doc()
    for csv_name in EXPECTED_CSVS:
        section = _get_csv_section(doc, csv_name)
        cols = _get_table_columns(section, "### Fields")
        assert len(cols) > 0, f"No Fields table found for {csv_name}"
        for expected_col in FIELD_TABLE_COLUMNS:
            assert expected_col in cols, (
                f"Missing column '{expected_col}' in Fields table for {csv_name}"
            )


# ---------------------------------------------------------------------------
# T06: Representability tables have all tools
# ---------------------------------------------------------------------------


def test_representability_tables_have_all_tools() -> None:
    """For each CSV's Representability table: verify tool columns and N/E/X values."""
    doc = _read_doc()
    for csv_name in EXPECTED_CSVS:
        section = _get_csv_section(doc, csv_name)
        cols = _get_table_columns(section, "### Representability")
        assert len(cols) > 0, f"No Representability table found for {csv_name}"

        for expected_col in REPR_TABLE_COLUMNS:
            assert expected_col in cols, (
                f"Missing column '{expected_col}' in Representability table for {csv_name}"
            )

        # Verify every cell value starts with N, E, or X
        rows = _parse_table(section, "### Representability")
        for row in rows:
            for tool in EXPECTED_TOOLS:
                if tool in row:
                    cell = row[tool].strip()
                    assert re.match(r"^[NEX]", cell), (
                        f"Cell for {tool} in {csv_name} does not start with N/E/X: '{cell}'"
                    )


# ---------------------------------------------------------------------------
# T07: Representability field count matches schema
# ---------------------------------------------------------------------------


def test_representability_field_count_matches_schema() -> None:
    """For each CSV: field count and names match between Fields and Representability tables."""
    doc = _read_doc()
    for csv_name in EXPECTED_CSVS:
        section = _get_csv_section(doc, csv_name)
        field_rows = _parse_table(section, "### Fields")
        repr_rows = _parse_table(section, "### Representability")

        assert len(field_rows) == len(repr_rows), (
            f"{csv_name}: Fields table has {len(field_rows)} rows but "
            f"Representability table has {len(repr_rows)} rows"
        )

        field_names = [r["Field"] for r in field_rows]
        repr_names = [r["Field"] for r in repr_rows]
        assert field_names == repr_names, (
            f"{csv_name}: Field names mismatch between Fields and Representability tables. "
            f"Fields: {field_names}, Repr: {repr_names}"
        )


# ---------------------------------------------------------------------------
# T08: Summary tables have all tools with valid percentages
# ---------------------------------------------------------------------------


def test_summary_tables_have_all_tools() -> None:
    """For each CSV's Summary table: 6 rows, correct columns, percentages sum to ~100%."""
    doc = _read_doc()
    for csv_name in EXPECTED_CSVS:
        section = _get_csv_section(doc, csv_name)
        rows = _parse_table(section, "### Summary")

        assert len(rows) == 6, f"{csv_name}: Summary table has {len(rows)} rows, expected 6"

        # Verify columns
        if rows:
            actual_cols = list(rows[0].keys())
            for col in SUMMARY_TABLE_COLUMNS:
                assert col in actual_cols, f"Missing column '{col}' in Summary table for {csv_name}"

        # Verify all tool names present
        tool_names = {r["Tool"] for r in rows}
        for tool in EXPECTED_TOOLS:
            assert tool in tool_names, f"Tool '{tool}' missing from Summary table for {csv_name}"

        # Verify percentages sum to ~100%
        for row in rows:
            n_pct = float(row["N%"].rstrip("%"))
            e_pct = float(row["E%"].rstrip("%"))
            x_pct = float(row["X%"].rstrip("%"))
            total = n_pct + e_pct + x_pct
            assert 98.0 <= total <= 102.0, (
                f"{csv_name}, {row['Tool']}: percentages sum to {total}%, expected 98-102%"
            )


# ---------------------------------------------------------------------------
# T09: Representability citations present
# ---------------------------------------------------------------------------


def test_representability_citations_present() -> None:
    """Every Representability cell must have a parenthetical citation after the tier code."""
    doc = _read_doc()
    citation_pattern = re.compile(r"^[NEX]\s*\(.*\)$")

    for csv_name in EXPECTED_CSVS:
        section = _get_csv_section(doc, csv_name)
        rows = _parse_table(section, "### Representability")
        for row in rows:
            for tool in EXPECTED_TOOLS:
                if tool in row:
                    cell = row[tool].strip()
                    assert citation_pattern.match(cell), (
                        f"{csv_name}, field '{row['Field']}', tool '{tool}': "
                        f"cell '{cell}' does not match pattern '[NEX] (citation)'"
                    )


# ---------------------------------------------------------------------------
# T10: Join key fields marked in schema
# ---------------------------------------------------------------------------


def test_join_key_fields_marked_in_schema() -> None:
    """Join key columns from Join Keys subsection must be marked yes in Fields table."""
    doc = _read_doc()
    for csv_name in EXPECTED_CSVS:
        section = _get_csv_section(doc, csv_name)
        field_rows = _parse_table(section, "### Fields")

        # Extract join key field names (those with Join Key = yes)
        marked_yes = {r["Field"] for r in field_rows if r.get("Join Key", "").strip() == "yes"}

        # Verify at least one join key exists
        assert len(marked_yes) > 0, f"{csv_name}: No fields marked as join keys"

        # Verify join key fields mentioned in the header block are marked yes
        # Extract join key from header: **Join key:** <value>
        join_key_match = re.search(r"\*\*Join key:\*\*\s*(.+)", section)
        if join_key_match:
            join_key_text = join_key_match.group(1).strip()
            # Parse individual column names from the join key text
            # Handle formats like "FROM_BUS + TO_BUS + CKT" and
            # "ELEMENT_FROM_BUS + ELEMENT_TO_BUS + ELEMENT_CKT (for branch), ..."
            key_parts = re.findall(r"[A-Z_]+(?:_[A-Z]+)*", join_key_text)
            # Filter to only actual field names present in the table
            all_fields = {r["Field"] for r in field_rows}
            key_fields_in_table = {k for k in key_parts if k in all_fields}

            for key_field in key_fields_in_table:
                assert key_field in marked_yes, (
                    f"{csv_name}: Join key field '{key_field}' not marked as 'yes' in Fields table"
                )


# ---------------------------------------------------------------------------
# T11: Domain values valid
# ---------------------------------------------------------------------------


def test_domain_values_valid() -> None:
    """Verify Domain values are one of: Transmission, Generation, Market, Outage."""
    doc = _read_doc()

    # Check CSV Overview table
    overview_rows = _parse_table(doc, "## CSV Overview")
    for row in overview_rows:
        domain = row["Domain"].strip()
        assert domain in VALID_DOMAINS, (
            f"Invalid domain '{domain}' in CSV Overview for {row['CSV File']}"
        )

    # Check each CSV header block
    for csv_name in EXPECTED_CSVS:
        section = _get_csv_section(doc, csv_name)
        domain_match = re.search(r"\*\*Domain:\*\*\s*(\w+)", section)
        assert domain_match is not None, f"No Domain found in header block for {csv_name}"
        domain = domain_match.group(1).strip()
        assert domain in VALID_DOMAINS, f"Invalid domain '{domain}' in header block for {csv_name}"


# ---------------------------------------------------------------------------
# T12: Cross-CSV summary has all CSVs and tools
# ---------------------------------------------------------------------------


def test_cross_csv_summary_has_all_csvs_and_tools() -> None:
    """Parse Cross-CSV Summary table: 7 rows, 6 tool columns."""
    doc = _read_doc()
    rows = _parse_table(doc, "## Cross-CSV Summary")

    assert len(rows) == 7, f"Cross-CSV Summary has {len(rows)} rows, expected 7"

    # Verify all CSV names present
    csv_names = {r["CSV"] for r in rows}
    for csv_name in EXPECTED_CSVS:
        assert csv_name in csv_names, f"Missing {csv_name} in Cross-CSV Summary"

    # Verify tool columns present
    if rows:
        actual_cols = list(rows[0].keys())
        for tool in EXPECTED_TOOLS:
            expected_col = f"{tool} N%"
            assert expected_col in actual_cols, (
                f"Missing column '{expected_col}' in Cross-CSV Summary"
            )


# ---------------------------------------------------------------------------
# T13: Extension mechanism table has all tools
# ---------------------------------------------------------------------------


def test_extension_mechanism_table_has_all_tools() -> None:
    """Parse Extension Mechanism Reference table: 6 rows, required columns, all tools."""
    doc = _read_doc()
    rows = _parse_table(doc, "## Extension Mechanisms by Tool")

    assert len(rows) == 6, f"Extension Mechanism table has {len(rows)} rows, expected 6"

    # Verify columns
    if rows:
        actual_cols = list(rows[0].keys())
        for col in EXT_MECH_COLUMNS:
            assert col in actual_cols, f"Missing column '{col}' in Extension Mechanism table"

    # Verify all tools present
    tool_names = {r["Tool"] for r in rows}
    for tool in EXPECTED_TOOLS:
        assert tool in tool_names, f"Tool '{tool}' missing from Extension Mechanism table"


# ---------------------------------------------------------------------------
# T14: Cross-references section exists
# ---------------------------------------------------------------------------


def test_cross_references_section_exists() -> None:
    """Verify section S7 exists with required relative paths."""
    doc = _read_doc()

    # Verify the section exists
    assert "## Cross-References" in doc, "Missing '## Cross-References' section"

    # Find the cross-references section
    cr_match = re.search(r"## Cross-References\s*\n(.*)", doc, re.DOTALL)
    assert cr_match is not None, "Could not parse Cross-References section"
    cr_text = cr_match.group(1)

    required_refs = [
        "intermediate-schema.md",
        "mapping-guide.md",
        "field-criticality-matrix.md",
        "supplemental-csv-representability.md",
        "join_key_report.md",
    ]
    for ref in required_refs:
        assert ref in cr_text, f"Missing reference to '{ref}' in Cross-References section"


# ---------------------------------------------------------------------------
# T15: Classification system section exists
# ---------------------------------------------------------------------------


def test_classification_system_section_exists() -> None:
    """Verify section S2 exists with three tier definitions (N, E, X)."""
    doc = _read_doc()

    assert "## Representability Classification System" in doc, (
        "Missing '## Representability Classification System' section"
    )

    # Find the section
    cs_match = re.search(
        r"## Representability Classification System\s*\n(.*?)(?=\n## [^#]|\Z)",
        doc,
        re.DOTALL,
    )
    assert cs_match is not None, "Could not parse Classification System section"
    cs_text = cs_match.group(1)

    # Verify three tier definitions
    assert "Natively-representable" in cs_text, "Missing 'Natively-representable' definition"
    assert "Extension-representable" in cs_text, "Missing 'Extension-representable' definition"
    assert "Tool-external" in cs_text, "Missing 'Tool-external' definition"

    # Verify tier codes mentioned
    assert "(N)" in cs_text or "**N**" in cs_text or " N " in cs_text, (
        "Tier code 'N' not found in classification system"
    )
    assert "(E)" in cs_text or "**E**" in cs_text or " E " in cs_text, (
        "Tier code 'E' not found in classification system"
    )
    assert "(X)" in cs_text or "**X**" in cs_text or " X " in cs_text, (
        "Tier code 'X' not found in classification system"
    )


# ---------------------------------------------------------------------------
# T16: CSV field counts match actual headers (requires FNM_PATH)
# ---------------------------------------------------------------------------


@pytest.mark.fnm
def test_csv_field_counts_match_actual_headers() -> None:
    """Requires FNM_PATH. Verify field counts match actual CSV headers."""
    fnm_path_str = os.environ.get("FNM_PATH")
    if not fnm_path_str:
        pytest.skip("FNM_PATH not set")

    fnm_path = Path(fnm_path_str)
    doc = _read_doc()

    for csv_name in EXPECTED_CSVS:
        csv_path = fnm_path / csv_name
        if not csv_path.exists():
            pytest.skip(f"CSV file not found: {csv_path}")

        # Read actual header
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            actual_header = next(reader)
        actual_count = len([h.strip() for h in actual_header if h.strip()])

        # Count rows in the Fields table
        section = _get_csv_section(doc, csv_name)
        field_rows = _parse_table(section, "### Fields")
        doc_count = len(field_rows)

        assert actual_count == doc_count, (
            f"{csv_name}: actual CSV has {actual_count} columns but "
            f"Fields table has {doc_count} rows"
        )
