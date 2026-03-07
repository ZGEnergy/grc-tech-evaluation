"""Structural validation tests for the 3-winding transformer reference document.

Tests verify that data/fnm/docs/three-winding-transformers.md contains all required
sections, field coverage, topology diagrams, impedance formulas, tool handling
documentation, and worked examples as specified in PRD 02/04.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants and fixtures
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DOC_PATH = REPO_ROOT / "data" / "fnm" / "docs" / "three-winding-transformers.md"

REQUIRED_H2_SECTIONS = [
    "Purpose",
    "Audience",
    "PSS/E v31 Record Structure",
    "Star-Bus Equivalent Topology",
    "Winding Parameters",
    "Intermediate Format Representation",
    "Tool Handling",
    "Worked Example",
    "Common Pitfalls",
    "Cross-References",
]

# All 83 PSS/E v31 3-winding transformer field names
DATA_LINE_1_FIELDS = [
    "I",
    "J",
    "K",
    "CKT",
    "CW",
    "CZ",
    "CM",
    "MAG1",
    "MAG2",
    "NMETR",
    "NAME",
    "STAT",
    "O1",
    "F1",
    "O2",
    "F2",
    "O3",
    "F3",
    "O4",
    "F4",
    "VECGRP",
]

DATA_LINE_2_FIELDS = [
    "R1-2",
    "X1-2",
    "SBASE1-2",
    "R2-3",
    "X2-3",
    "SBASE2-3",
    "R3-1",
    "X3-1",
    "SBASE3-1",
    "VMSTAR",
    "ANSTAR",
]

WINDING_FIELDS_TEMPLATE = [
    "WINDV{n}",
    "NOMV{n}",
    "ANG{n}",
    "RATA{n}",
    "RATB{n}",
    "RATC{n}",
    "COD{n}",
    "CONT{n}",
    "RMA{n}",
    "RMI{n}",
    "VMA{n}",
    "VMI{n}",
    "NTP{n}",
    "TAB{n}",
    "CR{n}",
    "CX{n}",
    "CNXA{n}",
]

ALL_83_FIELDS: list[str] = list(DATA_LINE_1_FIELDS) + list(DATA_LINE_2_FIELDS)
for winding_num in (1, 2, 3):
    ALL_83_FIELDS.extend(f.format(n=winding_num) for f in WINDING_FIELDS_TEMPLATE)

TOOL_NAMES = ["PyPSA", "pandapower", "GridCal", "PowerModels", "PowerSimulations", "MATPOWER"]


@pytest.fixture(scope="module")
def doc_text() -> str:
    """Read the 3-winding transformer document and return its full text."""
    assert DOC_PATH.exists(), f"Document not found at {DOC_PATH}"
    text = DOC_PATH.read_text(encoding="utf-8")
    assert len(text) > 0, "Document is empty"
    return text


@pytest.fixture(scope="module")
def doc_sections(doc_text: str) -> dict[str, str]:
    """Split the document into top-level (##) sections keyed by heading."""
    sections: dict[str, str] = {}
    current_heading = ""
    current_lines: list[str] = []
    for line in doc_text.splitlines():
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


def _find_section(sections: dict[str, str], substring: str) -> str:
    """Find a section whose heading contains the given substring (case-insensitive).

    Returns the section body text, or empty string if not found.
    """
    sub_lower = substring.lower()
    for heading, body in sections.items():
        if sub_lower in heading.lower():
            return body
    return ""


# ---------------------------------------------------------------------------
# Document structure tests -- T01-T03
# ---------------------------------------------------------------------------


@pytest.mark.docs
class TestDocumentStructure:
    """T01-T03: Verify the document has all required sections."""

    def test_document_exists_at_expected_path(self) -> None:
        """T01: Verify document exists at data/fnm/docs/three-winding-transformers.md."""
        assert DOC_PATH.exists(), f"Expected document at {DOC_PATH}"
        content = DOC_PATH.read_text(encoding="utf-8")
        assert len(content) > 0, "Document exists but is empty"

    def test_required_top_level_sections_present(self, doc_sections: dict[str, str]) -> None:
        """T02: All required H2 sections exist."""
        for section_name in REQUIRED_H2_SECTIONS:
            found = any(section_name.lower() in heading.lower() for heading in doc_sections)
            assert found, (
                f"Missing required H2 section: '## {section_name}'. "
                f"Found sections: {list(doc_sections.keys())}"
            )

    def test_data_line_subsections_present(self, doc_sections: dict[str, str]) -> None:
        """T03: Within PSS/E v31 Record Structure, subsections for all 5 data lines."""
        record_section = _find_section(doc_sections, "PSS/E v31 Record Structure")
        assert record_section, "Could not find 'PSS/E v31 Record Structure' section"

        for line_num in range(1, 6):
            patterns = [
                f"Data Line {line_num}",
                f"Line {line_num}",
            ]
            found = any(p in record_section for p in patterns)
            assert found, (
                f"Missing subsection for Data Line {line_num} in 'PSS/E v31 Record Structure'"
            )


# ---------------------------------------------------------------------------
# Field coverage tests -- T04-T06
# ---------------------------------------------------------------------------


@pytest.mark.docs
class TestFieldCoverage:
    """T04-T06: Verify all 83 fields are documented."""

    def test_all_83_fields_documented(self, doc_text: str) -> None:
        """T04: All 83 PSS/E field names appear at least once in the document."""
        missing_fields: list[str] = []
        for field in ALL_83_FIELDS:
            # Check for backtick-delimited or plain occurrence
            if f"`{field}`" not in doc_text and field not in doc_text:
                missing_fields.append(field)
        assert not missing_fields, (
            f"Missing {len(missing_fields)} of 83 fields in the document: {missing_fields}"
        )

    def test_all_three_windings_covered(self, doc_text: str) -> None:
        """T05: Per-winding fields documented for all three windings."""
        winding_field_families = {
            "WINDV": ["WINDV1", "WINDV2", "WINDV3"],
            "COD": ["COD1", "COD2", "COD3"],
            "RATA": ["RATA1", "RATA2", "RATA3"],
            "NTP": ["NTP1", "NTP2", "NTP3"],
        }
        for family, fields in winding_field_families.items():
            for field in fields:
                assert field in doc_text, (
                    f"Winding field '{field}' (family '{family}') not found in document"
                )

    def test_field_count_summary_states_83(self, doc_text: str) -> None:
        """T06: Document contains a field count summary stating 83 fields total."""
        pattern = re.compile(r"83\s*(?:fields|total\s*fields)", re.IGNORECASE)
        alt_pattern = re.compile(r"total[:\s]*83", re.IGNORECASE)
        assert pattern.search(doc_text) or alt_pattern.search(doc_text), (
            "Document does not contain a field count summary stating '83 fields' or 'total: 83'"
        )


# ---------------------------------------------------------------------------
# Topology and formula tests -- T07-T08
# ---------------------------------------------------------------------------


@pytest.mark.docs
class TestTopologyAndFormulas:
    """T07-T08: Verify star-bus diagram and impedance conversion formulas."""

    def test_star_bus_diagram_present(self, doc_sections: dict[str, str]) -> None:
        """T07: Star-Bus Equivalent Topology section contains a topology diagram."""
        topology_section = _find_section(doc_sections, "Star-Bus Equivalent Topology")
        assert topology_section, "Could not find 'Star-Bus Equivalent Topology' section"

        # Check for a fenced code block or indented block with key elements
        diagram_elements = [
            ("Bus I", "Winding 1"),
            ("Bus J", "Winding 2"),
            ("Bus K", "Winding 3"),
            ("Star", "star bus"),
        ]

        matches = 0
        for primary, alt in diagram_elements:
            if primary in topology_section or alt in topology_section:
                matches += 1

        assert matches >= 3, (
            f"Topology diagram should contain at least 3 of the 4 key elements "
            f"(Bus I/Winding 1, Bus J/Winding 2, Bus K/Winding 3, Star/star bus). "
            f"Found {matches}."
        )

        # Verify there is a fenced code block (```) in the section
        assert "```" in topology_section, (
            "Topology section should contain a fenced code block for the diagram"
        )

    def test_impedance_conversion_formulas_present(self, doc_text: str) -> None:
        """T08: All three star-leg impedance conversion formulas are present."""
        # Z1 = (Z1-2 + Z3-1 - Z2-3) / 2  (or equivalent notation)
        # Z2 = (Z1-2 + Z2-3 - Z3-1) / 2
        # Z3 = (Z2-3 + Z3-1 - Z1-2) / 2

        # Flexible patterns to match various notations:
        # Z_1, Z1, Z_12, Z12, Z1-2, etc.
        z1_pattern = re.compile(
            r"Z_?1\s*=\s*\(.*(Z_?1[-_]?2|Z_?12).*"
            r"(Z_?3[-_]?1|Z_?31).*"
            r"(Z_?2[-_]?3|Z_?23).*\)\s*/\s*2",
            re.IGNORECASE,
        )
        z2_pattern = re.compile(
            r"Z_?2\s*=\s*\(.*(Z_?1[-_]?2|Z_?12).*"
            r"(Z_?2[-_]?3|Z_?23).*"
            r"(Z_?3[-_]?1|Z_?31).*\)\s*/\s*2",
            re.IGNORECASE,
        )
        z3_pattern = re.compile(
            r"Z_?3\s*=\s*\(.*(Z_?2[-_]?3|Z_?23).*"
            r"(Z_?3[-_]?1|Z_?31).*"
            r"(Z_?1[-_]?2|Z_?12).*\)\s*/\s*2",
            re.IGNORECASE,
        )

        assert z1_pattern.search(doc_text), (
            "Missing Z1 star-leg impedance formula: Z1 = (Z1-2 + Z3-1 - Z2-3) / 2"
        )
        assert z2_pattern.search(doc_text), (
            "Missing Z2 star-leg impedance formula: Z2 = (Z1-2 + Z2-3 - Z3-1) / 2"
        )
        assert z3_pattern.search(doc_text), (
            "Missing Z3 star-leg impedance formula: Z3 = (Z2-3 + Z3-1 - Z1-2) / 2"
        )


# ---------------------------------------------------------------------------
# Tool handling test -- T09
# ---------------------------------------------------------------------------


@pytest.mark.docs
class TestToolHandling:
    """T09: Verify all six tools are documented in the Tool Handling section."""

    def test_all_six_tools_documented(self, doc_sections: dict[str, str]) -> None:
        """T09: All six tool names appear in the Tool Handling section."""
        tool_section = _find_section(doc_sections, "Tool Handling")
        assert tool_section, "Could not find 'Tool Handling' section"

        tool_section_lower = tool_section.lower()
        missing_tools: list[str] = []
        for tool in TOOL_NAMES:
            if tool.lower() not in tool_section_lower:
                missing_tools.append(tool)

        assert not missing_tools, f"Missing tools in 'Tool Handling' section: {missing_tools}"


# ---------------------------------------------------------------------------
# Worked example test -- T10
# ---------------------------------------------------------------------------


@pytest.mark.docs
class TestWorkedExample:
    """T10: Verify worked example uses realistic values."""

    def test_worked_example_uses_realistic_values(self, doc_sections: dict[str, str]) -> None:
        """T10: Worked Example section contains realistic transmission-scale values."""
        example_section = _find_section(doc_sections, "Worked Example")
        assert example_section, "Could not find 'Worked Example' section"

        # Extract numeric values from the section
        numbers = [float(m) for m in re.findall(r"(?<!\w)(\d+\.?\d*)", example_section)]

        # Check for at least one voltage in the 69-500 kV range
        has_voltage = any(69 <= n <= 500 for n in numbers)
        assert has_voltage, (
            "Worked example missing voltage in 69-500 kV range "
            "(expected typical HV/MV/LV winding voltages)"
        )

        # Check for at least one MVA rating in the 50-1000 range
        has_mva = any(50 <= n <= 1000 for n in numbers)
        assert has_mva, "Worked example missing MVA rating in 50-1000 range"

        # Check for at least one impedance value in the 0.0001-1.0 per-unit range
        has_impedance = any(0.0001 <= n <= 1.0 for n in numbers)
        assert has_impedance, "Worked example missing impedance value in 0.0001-1.0 per-unit range"
