"""Tests for the Record-Type Mapping Guide (PRD 02/02).

Validates the structural integrity and content consistency of the mapping guide
markdown document at ``data/fnm/docs/mapping-guide.md``.

Tests T01-T11 are pure markdown parsing tests using only ``pathlib``, ``re``,
and ``pytest``.  Test T12 requires ``FNM_PATH`` and is marked ``@pytest.mark.fnm``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MAPPING_GUIDE = REPO_ROOT / "data" / "fnm" / "docs" / "mapping-guide.md"

ALL_17_RECORD_TYPES: list[str] = [
    "Bus",
    "Load",
    "Fixed Shunt",
    "Generator",
    "Branch",
    "Transformer",
    "Area",
    "Two-Terminal DC",
    "VSC DC",
    "Impedance Correction",
    "Multi-Terminal DC",
    "Multi-Section Line",
    "Zone",
    "Interarea Transfer",
    "Owner",
    "FACTS",
    "Switched Shunt",
]

SIX_TOOLS: list[str] = [
    "PyPSA",
    "pandapower",
    "GridCal",
    "PowerModels.jl",
    "PowerSimulations.jl",
    "MATPOWER",
]

VALID_SUPPORT_VALUES = {"Y", "P", "N", "--"}

TIER1_ESSENTIAL: set[str] = {"Bus", "Load", "Generator", "Branch", "Transformer"}

TIER3_TYPES: set[str] = {"Zone", "Owner", "Interarea Transfer"}

REQUIRED_ABSTRACTIONS: set[str] = {
    "Bus",
    "AC Line",
    "2-Winding Transformer",
    "3-Winding Transformer",
    "Generator",
    "Load",
    "Fixed Shunt",
    "Switched Shunt",
    "Area",
    "Zone",
    "Owner",
    "Two-Terminal HVDC Line",
    "VSC HVDC Line",
    "Multi-Terminal DC",
    "Impedance Correction Table",
    "Multi-Section Line",
    "Interarea Transfer",
    "FACTS Device",
}

CROSS_REF_FILES: list[str] = [
    "intermediate-schema.md",
    "per-unit-conventions.md",
    "three-winding-transformers.md",
    "field-criticality-matrix.md",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_guide() -> str:
    """Read the mapping guide content."""
    return MAPPING_GUIDE.read_text(encoding="utf-8")


def _parse_summary_matrix(text: str) -> list[dict[str, str]]:
    """Parse the S3 summary matrix table into a list of row dicts.

    Returns a list of dicts with keys: '#', 'PSS/E Record Type', 'Abstraction',
    'Tier', 'FNM Status', and each of the six tool names.
    """
    # Find the summary matrix section
    s3_match = re.search(
        r"## S3: Summary Matrix\s*\n(.*?)(?=\n## S[4-9]|\n## S\d{2}|\Z)", text, re.DOTALL
    )
    assert s3_match, "S3: Summary Matrix section not found"
    s3_text = s3_match.group(1)

    # Find all table lines (starting with |, not separator lines)
    table_lines = [
        line.strip()
        for line in s3_text.split("\n")
        if line.strip().startswith("|") and not re.match(r"^\|[-\s|]+\|$", line.strip())
    ]

    assert len(table_lines) >= 2, "Summary matrix table must have header + data rows"

    # Parse header
    header_cells = [c.strip() for c in table_lines[0].split("|")[1:-1]]

    # Parse data rows
    rows: list[dict[str, str]] = []
    for line in table_lines[1:]:
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) == len(header_cells):
            rows.append(dict(zip(header_cells, cells)))

    return rows


def _find_s5_subsections(text: str) -> list[str]:
    """Return the list of record type names found in S5 subsection headers.

    Matches patterns like: ### S5.1: Bus (Section 1)
    """
    pattern = r"### S5\.\d+:\s*(.+?)\s*\(Section \d+\)"
    return re.findall(pattern, text)


def _parse_tool_support_table(subsection_text: str) -> dict[str, str]:
    """Parse a per-record-type tool support table, returning {tool: Y/P/N}."""
    result: dict[str, str] = {}
    # Match table rows with tool name, support value
    # Format: | PyPSA | Y | ... | ... |
    for line in subsection_text.split("\n"):
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) >= 2 and cells[0] in SIX_TOOLS:
            result[cells[0]] = cells[1]
    return result


def _get_s5_subsection_text(text: str, record_type: str) -> str | None:
    """Extract the full text of a single S5 subsection by record type name."""
    # Escape special regex chars in record type name
    escaped = re.escape(record_type)
    pattern = (
        rf"(### S5\.\d+:\s*{escaped}\s*\(Section \d+\).*?)"
        r"(?=### S5\.\d+:|## S6:|\Z)"
    )
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1) if match else None


# ---------------------------------------------------------------------------
# T01-T07: Structural validation tests
# ---------------------------------------------------------------------------


class TestStructuralValidation:
    """Structural validation of the mapping guide markdown document."""

    def test_document_exists(self) -> None:
        """T01: Verify mapping-guide.md exists and is non-empty."""
        assert MAPPING_GUIDE.exists(), f"Mapping guide not found at {MAPPING_GUIDE}"
        content = MAPPING_GUIDE.read_text(encoding="utf-8")
        assert len(content.strip()) > 0, "Mapping guide is empty"

    def test_all_17_record_types_present(self) -> None:
        """T02: All 17 PSS/E v31 record types have subsections in S5."""
        text = _read_guide()
        found = _find_s5_subsections(text)
        found_set = set(found)

        for rt in ALL_17_RECORD_TYPES:
            assert rt in found_set, (
                f"Record type '{rt}' not found in S5 subsection headers. Found: {sorted(found_set)}"
            )
        assert len(found) == 17, f"Expected 17 S5 subsections, found {len(found)}"

    def test_summary_matrix_has_all_rows(self) -> None:
        """T03: Summary matrix has 17 rows, all 6 tool columns, valid cell values."""
        text = _read_guide()
        rows = _parse_summary_matrix(text)

        # Exactly 17 data rows
        assert len(rows) == 17, f"Expected 17 summary matrix rows, found {len(rows)}"

        # All six tool columns present
        for tool in SIX_TOOLS:
            assert all(tool in row for row in rows), (
                f"Tool column '{tool}' missing from summary matrix"
            )

        # Every tool cell is Y, P, N, or --
        for row in rows:
            for tool in SIX_TOOLS:
                val = row[tool]
                assert val in VALID_SUPPORT_VALUES, (
                    f"Invalid support value '{val}' for {tool} in row "
                    f"'{row.get('PSS/E Record Type', '?')}'. "
                    f"Must be one of {VALID_SUPPORT_VALUES}"
                )

    def test_summary_matrix_consistent_with_detail_sections(self) -> None:
        """T04: Y/P/N values in S3 match per-record-type tables in S5."""
        text = _read_guide()
        rows = _parse_summary_matrix(text)

        for row in rows:
            rt = row["PSS/E Record Type"]
            fnm_status = row["FNM Status"]

            # Skip empty record types (no detail tool support table)
            if fnm_status.startswith("Empty"):
                continue

            subsection = _get_s5_subsection_text(text, rt)
            assert subsection is not None, f"S5 subsection not found for '{rt}'"

            detail_support = _parse_tool_support_table(subsection)
            if not detail_support:
                # Transformer has a special combined abstraction, check it exists
                continue

            for tool in SIX_TOOLS:
                matrix_val = row[tool]
                detail_val = detail_support.get(tool)
                if detail_val is not None:
                    assert matrix_val == detail_val, (
                        f"Mismatch for '{rt}' / {tool}: "
                        f"S3 matrix says '{matrix_val}', S5 detail says '{detail_val}'"
                    )

    def test_tier_classification_complete(self) -> None:
        """T05: Every non-empty record type has Tier 1, 2, or 3."""
        text = _read_guide()
        rows = _parse_summary_matrix(text)

        valid_tiers = {"1", "2", "3"}
        for row in rows:
            tier = row.get("Tier", "").strip()
            assert tier in valid_tiers, (
                f"Record type '{row['PSS/E Record Type']}' has invalid tier '{tier}'. "
                f"Must be one of {valid_tiers}"
            )

    def test_abstraction_vocabulary_covers_all_types(self) -> None:
        """T06: S2 abstraction vocabulary covers all record types in S3."""
        text = _read_guide()

        # Parse S2 abstraction vocabulary table
        s2_match = re.search(
            r"## S2: Abstraction Vocabulary\s*\n(.*?)(?=\n## S3:|\Z)",
            text,
            re.DOTALL,
        )
        assert s2_match, "S2: Abstraction Vocabulary section not found"
        s2_text = s2_match.group(1)

        # Extract abstraction names from the table
        abstractions_found: set[str] = set()
        for line in s2_text.split("\n"):
            line = line.strip()
            if line.startswith("|") and not re.match(r"^\|[-\s|]+\|$", line):
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if len(cells) >= 1 and cells[0] not in ("Abstraction", ""):
                    abstractions_found.add(cells[0])

        # Every required abstraction must be present
        for abstraction in REQUIRED_ABSTRACTIONS:
            assert abstraction in abstractions_found, (
                f"Required abstraction '{abstraction}' not found in S2 vocabulary. "
                f"Found: {sorted(abstractions_found)}"
            )

    def test_empty_record_types_marked(self) -> None:
        """T07: Empty record types have 'not present in FNM' and no tool support table."""
        text = _read_guide()
        rows = _parse_summary_matrix(text)

        for row in rows:
            rt = row["PSS/E Record Type"]
            fnm_status = row["FNM Status"]

            if not fnm_status.startswith("Empty"):
                continue

            subsection = _get_s5_subsection_text(text, rt)
            assert subsection is not None, f"S5 subsection not found for empty type '{rt}'"

            # Must contain "not present in FNM" (case-insensitive)
            assert re.search(r"not present in (?:the )?FNM", subsection, re.IGNORECASE), (
                f"Empty record type '{rt}' subsection does not contain 'not present in FNM'"
            )

            # Must NOT contain a tool support table (no "| Tool |" header row)
            has_tool_table = bool(re.search(r"\|\s*Tool\s*\|", subsection))
            assert not has_tool_table, (
                f"Empty record type '{rt}' should not have a tool support table"
            )


# ---------------------------------------------------------------------------
# T08-T10: Content consistency tests
# ---------------------------------------------------------------------------


class TestContentConsistency:
    """Content consistency checks for tier classification and transformer mapping."""

    def test_tier1_contains_essential_types(self) -> None:
        """T08: Bus, Load, Generator, Branch, Transformer are all Tier 1."""
        text = _read_guide()
        rows = _parse_summary_matrix(text)

        rt_to_tier = {row["PSS/E Record Type"]: row["Tier"] for row in rows}

        for rt in TIER1_ESSENTIAL:
            assert rt_to_tier.get(rt) == "1", (
                f"Essential record type '{rt}' must be Tier 1, "
                f"but found Tier {rt_to_tier.get(rt, 'MISSING')}"
            )

    def test_tier3_types_are_non_electrical(self) -> None:
        """T09: Every Tier 3 type is Zone, Owner, or Interarea Transfer."""
        text = _read_guide()
        rows = _parse_summary_matrix(text)

        for row in rows:
            if row["Tier"] == "3":
                rt = row["PSS/E Record Type"]
                assert rt in TIER3_TYPES, (
                    f"Record type '{rt}' is classified as Tier 3 but is not in the "
                    f"expected Tier 3 set {TIER3_TYPES}. Record types with direct "
                    f"electrical effect should not be Tier 3."
                )

    def test_transformer_section_covers_both_abstractions(self) -> None:
        """T10: Transformer subsection mentions both 2-winding and 3-winding, plus K field."""
        text = _read_guide()
        subsection = _get_s5_subsection_text(text, "Transformer")
        assert subsection is not None, "Transformer subsection not found in S5"

        assert "2-Winding Transformer" in subsection, (
            "Transformer subsection must mention '2-Winding Transformer'"
        )
        assert "3-Winding Transformer" in subsection, (
            "Transformer subsection must mention '3-Winding Transformer'"
        )

        # K field as distinguishing criterion
        k_field_mentioned = bool(
            re.search(r"\bK[ -]?field\b|\bK[= ]*0\b|\bK!=0\b|\bK is\b|\bK=0\b", subsection)
        )
        assert k_field_mentioned, (
            "Transformer subsection must mention the K field as the criterion "
            "distinguishing 2-winding from 3-winding transformers"
        )


# ---------------------------------------------------------------------------
# T11-T12: Cross-reference tests
# ---------------------------------------------------------------------------


class TestCrossReferences:
    """Cross-reference validation tests."""

    def test_cross_references_section_exists(self) -> None:
        """T11: S6 exists and references required companion documents."""
        text = _read_guide()

        # S6 section must exist
        assert re.search(r"## S6: Cross-References", text), "S6: Cross-References section not found"

        s6_match = re.search(
            r"## S6: Cross-References\s*\n(.*?)(?=\n## |\Z)",
            text,
            re.DOTALL,
        )
        assert s6_match, "Could not extract S6 content"
        s6_text = s6_match.group(1)

        for ref_file in CROSS_REF_FILES:
            assert ref_file in s6_text, f"Cross-reference to '{ref_file}' not found in S6 section"

    @pytest.mark.fnm
    def test_non_empty_record_types_match_d3(self, require_fnm: Path) -> None:
        """T12: Non-empty record types in S3 match D3 raw record counter output."""
        # Look for raw_counts.json in the intermediate directory
        raw_counts_path = REPO_ROOT / "data" / "fnm" / "intermediate" / "raw_counts.json"
        if not raw_counts_path.exists():
            pytest.skip(f"D3 raw counts file not found at {raw_counts_path}")

        with open(raw_counts_path, encoding="utf-8") as f:
            raw_counts = json.load(f)

        # Extract non-empty sections from D3 output
        d3_non_empty: set[str] = set()
        if "sections" in raw_counts:
            for section in raw_counts["sections"]:
                name = section.get("name", "")
                count = section.get("record_count", 0)
                if count > 0:
                    d3_non_empty.add(name)
        elif "non_empty_sections" in raw_counts:
            d3_non_empty = set(raw_counts["non_empty_sections"])

        # Extract non-empty types from summary matrix
        text = _read_guide()
        rows = _parse_summary_matrix(text)
        matrix_non_empty: set[str] = set()
        for row in rows:
            if row["FNM Status"].startswith("Non-empty"):
                matrix_non_empty.add(row["PSS/E Record Type"])

        assert matrix_non_empty == d3_non_empty, (
            f"Non-empty record types mismatch.\n"
            f"  In S3 matrix but not in D3: {matrix_non_empty - d3_non_empty}\n"
            f"  In D3 but not in S3 matrix: {d3_non_empty - matrix_non_empty}"
        )
