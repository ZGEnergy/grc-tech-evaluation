"""Tests for PRD 04/02 -- Supplemental CSV Representability Summary.

Validates the document at data/fnm/docs/supplemental-csv-representability.md
for structural completeness, internal consistency, and traceability to D1
(supplemental-csvs.md).

Tests T01-T10 are pure markdown parsing tests using pathlib, re, and pytest.
No FNM_PATH required.
"""

from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (relative to repo root)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DOC_PATH = _REPO_ROOT / "fnm" / "docs" / "supplemental-csv-representability.md"
_D1_PATH = _REPO_ROOT / "fnm" / "docs" / "supplemental-csvs.md"

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

VALID_TIERS: set[str] = {"`native`", "`extension`", "`external`"}

KEY_FINDINGS_SUBSECTIONS: list[str] = [
    "### Richest Native Coverage",
    "### Universally Tool-External CSVs",
    "### Most Consequential Gaps for Phase 2",
    "### Tool Landscape Summary",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_doc() -> str:
    """Read the supplemental CSV representability summary document."""
    assert _DOC_PATH.exists(), f"Document not found: {_DOC_PATH}"
    return _DOC_PATH.read_text(encoding="utf-8")


def _read_d1() -> str:
    """Read the D1 supplemental CSV reference document."""
    assert _D1_PATH.exists(), f"D1 document not found: {_D1_PATH}"
    return _D1_PATH.read_text(encoding="utf-8")


def _parse_table(text: str, heading: str) -> list[dict[str, str]]:
    """Parse a markdown table following a given heading into list of row dicts.

    Searches for the heading, then reads the next markdown table found.
    Returns a list of dicts with column headers as keys.
    """
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


def _parse_pct_cell(cell: str) -> tuple[int, int, int]:
    """Parse a cell like '40% native, 60% extension, 0% external' into (n, e, x).

    Also handles bold-wrapped values like '**34% native, 23% extension, 43% external**'.
    """
    # Strip bold markers
    clean = cell.strip().strip("*")
    # Extract all percentage values
    pcts = re.findall(r"(\d+)%", clean)
    assert len(pcts) == 3, f"Expected 3 percentages in cell, got {len(pcts)}: '{cell}'"
    return int(pcts[0]), int(pcts[1]), int(pcts[2])


def _get_d1_field_count(d1_text: str, csv_name: str) -> int:
    """Get the field count for a CSV from D1's Fields table.

    Counts the number of data rows in the Fields table under the CSV's section.
    """
    # Find the CSV section (H2 heading)
    pattern = rf"^## {re.escape(csv_name)}\s*$"
    match = re.search(pattern, d1_text, re.MULTILINE)
    if match is None:
        return -1

    # Extract section text up to next H2
    section_pattern = rf"^## {re.escape(csv_name)}\s*\n(.*?)(?=\n## [^#]|\Z)"
    section_match = re.search(section_pattern, d1_text, re.MULTILINE | re.DOTALL)
    if section_match is None:
        return -1

    section = section_match.group(0)

    # Parse the Fields table
    rows = _parse_table(section, "### Fields")
    return len(rows)


# ---------------------------------------------------------------------------
# T01: test_document_exists
# ---------------------------------------------------------------------------


def test_document_exists() -> None:
    """Verify that data/fnm/docs/supplemental-csv-representability.md exists
    and is non-empty."""
    assert _DOC_PATH.exists(), f"Document not found: {_DOC_PATH}"
    content = _DOC_PATH.read_text(encoding="utf-8")
    assert len(content.strip()) > 0, "Document is empty"


# ---------------------------------------------------------------------------
# T02: test_front_matter_references_d1
# ---------------------------------------------------------------------------


def test_front_matter_references_d1() -> None:
    """Parse the front matter and verify it contains a relative link to
    supplemental-csvs.md (the D1 output document)."""
    doc = _read_doc()
    # Find front matter (text before the first ## heading)
    first_h2 = doc.find("\n## ")
    assert first_h2 > 0, "No ## heading found in document"
    front_matter = doc[:first_h2]
    assert "supplemental-csvs.md" in front_matter, (
        "Front matter does not contain a reference to supplemental-csvs.md"
    )


# ---------------------------------------------------------------------------
# T03: test_tier_definitions_present
# ---------------------------------------------------------------------------


def test_tier_definitions_present() -> None:
    """Verify the document contains a '## Representability Tiers' section
    with all three tier labels (native, extension, external) defined."""
    doc = _read_doc()
    assert "## Representability Tiers" in doc, "Missing '## Representability Tiers' section"

    # Extract the section
    tier_match = re.search(
        r"## Representability Tiers\s*\n(.*?)(?=\n## [^#]|\Z)",
        doc,
        re.DOTALL,
    )
    assert tier_match is not None, "Could not parse Representability Tiers section"
    tier_text = tier_match.group(1)

    for label in ["native", "extension", "external"]:
        assert f"`{label}`" in tier_text, (
            f"Tier label '{label}' not found in Representability Tiers section"
        )


# ---------------------------------------------------------------------------
# T04: test_csv_matrix_has_all_seven_csvs
# ---------------------------------------------------------------------------


def test_csv_matrix_has_all_seven_csvs() -> None:
    """Parse the CSV-Level Representability Matrix table and verify it contains
    exactly 7 data rows (one per supplemental CSV) plus a Totals row. The CSV
    names must match the CSV names used in D1's document."""
    doc = _read_doc()
    rows = _parse_table(doc, "## CSV-Level Representability Matrix")

    # Separate data rows from Totals row
    data_rows = [r for r in rows if "Totals" not in r.get("CSV", "")]
    totals_rows = [r for r in rows if "Totals" in r.get("CSV", "")]

    assert len(data_rows) == 7, f"Expected 7 data rows in CSV-Level Matrix, got {len(data_rows)}"
    assert len(totals_rows) == 1, (
        f"Expected 1 Totals row in CSV-Level Matrix, got {len(totals_rows)}"
    )

    # Verify CSV names match D1
    d1_text = _read_d1()
    for csv_name in EXPECTED_CSVS:
        found = any(csv_name in r.get("CSV", "") for r in data_rows)
        assert found, f"CSV '{csv_name}' not found in CSV-Level Matrix"
        # Also verify D1 has a section for this CSV
        d1_pattern = rf"^## {re.escape(csv_name)}\s*$"
        d1_match = re.search(d1_pattern, d1_text, re.MULTILINE)
        assert d1_match is not None, f"D1 has no section for {csv_name}"


# ---------------------------------------------------------------------------
# T05: test_csv_matrix_has_all_six_tools
# ---------------------------------------------------------------------------


def test_csv_matrix_has_all_six_tools() -> None:
    """Verify the CSV-Level Representability Matrix table has columns for all
    6 tools in the canonical order."""
    doc = _read_doc()
    cols = _get_table_columns(doc, "## CSV-Level Representability Matrix")
    assert len(cols) > 0, "No CSV-Level Matrix table found"

    for tool in EXPECTED_TOOLS:
        assert tool in cols, f"Tool '{tool}' not found in CSV-Level Matrix columns. Got: {cols}"

    # Verify canonical order
    tool_positions = [cols.index(t) for t in EXPECTED_TOOLS]
    assert tool_positions == sorted(tool_positions), (
        f"Tools not in canonical order. Positions: {dict(zip(EXPECTED_TOOLS, tool_positions))}"
    )


# ---------------------------------------------------------------------------
# T06: test_csv_matrix_percentages_sum_to_100
# ---------------------------------------------------------------------------


def test_csv_matrix_percentages_sum_to_100() -> None:
    """For each cell in the CSV-Level Representability Matrix (including the
    Totals row), parse the three percentage values and verify they sum to
    exactly 100%."""
    doc = _read_doc()
    rows = _parse_table(doc, "## CSV-Level Representability Matrix")
    assert len(rows) > 0, "No rows found in CSV-Level Matrix"

    for row in rows:
        csv_label = row.get("CSV", "unknown")
        for tool in EXPECTED_TOOLS:
            if tool in row:
                cell = row[tool]
                n_pct, e_pct, x_pct = _parse_pct_cell(cell)
                total = n_pct + e_pct + x_pct
                assert total == 100, (
                    f"{csv_label}, {tool}: percentages sum to {total}%, "
                    f"expected 100% (native={n_pct}, extension={e_pct}, external={x_pct})"
                )


# ---------------------------------------------------------------------------
# T07: test_csv_matrix_field_counts_match_d1
# ---------------------------------------------------------------------------


def test_csv_matrix_field_counts_match_d1() -> None:
    """For each CSV row in the matrix, verify the 'Fields' column value matches
    the total classifiable field count stated in D1's per-CSV Fields table."""
    doc = _read_doc()
    d1_text = _read_d1()
    rows = _parse_table(doc, "## CSV-Level Representability Matrix")

    data_rows = [r for r in rows if "Totals" not in r.get("CSV", "")]

    for row in data_rows:
        csv_name = row["CSV"].strip()
        fields_str = row["Fields"].strip()
        doc_field_count = int(fields_str)

        d1_field_count = _get_d1_field_count(d1_text, csv_name)
        assert d1_field_count > 0, f"Could not determine D1 field count for {csv_name}"
        assert doc_field_count == d1_field_count, (
            f"{csv_name}: summary says {doc_field_count} fields but "
            f"D1 Fields table has {d1_field_count} rows"
        )


# ---------------------------------------------------------------------------
# T08: test_concept_matrix_tools_match
# ---------------------------------------------------------------------------


def test_concept_matrix_tools_match() -> None:
    """Verify the Concept-Level Representability Matrix has columns for all
    6 tools in the canonical order."""
    doc = _read_doc()
    cols = _get_table_columns(doc, "## Concept-Level Representability Matrix")
    assert len(cols) > 0, "No Concept-Level Matrix table found"

    for tool in EXPECTED_TOOLS:
        assert tool in cols, f"Tool '{tool}' not found in Concept-Level Matrix columns. Got: {cols}"

    # Verify canonical order
    tool_positions = [cols.index(t) for t in EXPECTED_TOOLS]
    assert tool_positions == sorted(tool_positions), (
        "Tools not in canonical order in Concept-Level Matrix"
    )


# ---------------------------------------------------------------------------
# T09: test_concept_matrix_tiers_valid
# ---------------------------------------------------------------------------


def test_concept_matrix_tiers_valid() -> None:
    """For each cell in the Concept-Level Representability Matrix, verify the
    value is one of: `native`, `extension`, `external`."""
    doc = _read_doc()
    rows = _parse_table(doc, "## Concept-Level Representability Matrix")
    assert len(rows) > 0, "No rows found in Concept-Level Matrix"

    for row in rows:
        concept = row.get("Data Concept", "unknown")
        for tool in EXPECTED_TOOLS:
            if tool in row:
                cell = row[tool].strip()
                assert cell in VALID_TIERS, (
                    f"Concept '{concept}', tool '{tool}': "
                    f"invalid tier value '{cell}'. Expected one of {VALID_TIERS}"
                )


# ---------------------------------------------------------------------------
# T10: test_key_findings_subsections_present
# ---------------------------------------------------------------------------


def test_key_findings_subsections_present() -> None:
    """Verify the '## Key Findings' section contains all four required
    subsections."""
    doc = _read_doc()
    assert "## Key Findings" in doc, "Missing '## Key Findings' section"

    # Extract Key Findings section
    kf_match = re.search(
        r"## Key Findings\s*\n(.*?)(?=\n## [^#]|\Z)",
        doc,
        re.DOTALL,
    )
    assert kf_match is not None, "Could not parse Key Findings section"
    kf_text = kf_match.group(1)

    for subsection in KEY_FINDINGS_SUBSECTIONS:
        assert subsection in kf_text, f"Missing subsection '{subsection}' in Key Findings"
