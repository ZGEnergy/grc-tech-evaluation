"""Structural validation tests for the per-unit conventions reference document.

Tests verify that data/fnm/docs/per-unit-conventions.md contains all required
sections, worked examples, pitfalls coverage, and cross-references as specified
in PRD 02/03.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DOC_PATH = REPO_ROOT / "data" / "fnm" / "docs" / "per-unit-conventions.md"

DOMAIN_HEADINGS = [
    "1. System MVA Base",
    "2. Bus Base Voltage",
    "3. Branch (AC Line) Impedance",
    "4. Two-Winding Transformer Impedance",
    "5. Two-Winding Transformer Tap Ratios",
    "6. Three-Winding Transformer Per-Unit Bases",
    "7. Shunt Admittance",
    "8. Generator Capability",
    "9. Load Representation",
]

TOOL_NAMES = ["MATPOWER", "pandapower", "PyPSA", "GridCal", "PowerModels", "PowerSimulations"]


@pytest.fixture(scope="module")
def doc_text() -> str:
    """Read the per-unit conventions document and return its full text."""
    assert DOC_PATH.exists(), f"Document not found at {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


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


def _find_section(sections: dict[str, str], prefix: str) -> str:
    """Find a section whose heading starts with the given prefix.

    Returns the section body text, or empty string if not found.
    """
    for heading, body in sections.items():
        if heading.startswith(prefix):
            return body
    return ""


def _has_section(sections: dict[str, str], prefix: str) -> bool:
    """Check whether a section whose heading starts with *prefix* exists."""
    return any(h.startswith(prefix) for h in sections)


# ---------------------------------------------------------------------------
# Document structure tests (T01-T04)
# ---------------------------------------------------------------------------


@pytest.mark.docs
class TestDocumentStructure:
    """T01-T04: Verify the document has all required sections."""

    def test_document_exists_at_expected_path(self) -> None:
        """T01: Verify the document exists at the expected path."""
        assert DOC_PATH.exists(), f"Expected per-unit conventions document at {DOC_PATH}"

    def test_all_nine_domain_sections_present(self, doc_sections: dict[str, str]) -> None:
        """T02: All nine numbered domain sections are present."""
        for heading in DOMAIN_HEADINGS:
            assert _has_section(doc_sections, heading), f"Missing domain section: '## {heading}'"

    def test_required_subsections_per_domain(self, doc_sections: dict[str, str]) -> None:
        """T03: Each domain has required subsections."""
        for heading in DOMAIN_HEADINGS:
            section_text = _find_section(doc_sections, heading)
            subsection_headings = re.findall(r"^### (.+)$", section_text, re.MULTILINE)

            # Every domain needs Worked Example and Common Pitfalls
            assert any("Worked Example" in h for h in subsection_headings), (
                f"Domain '{heading}' missing '### Worked Example' subsection"
            )
            assert any("Common Pitfalls" in h for h in subsection_headings), (
                f"Domain '{heading}' missing '### Common Pitfalls' subsection"
            )

            # Every domain needs at least one substantive subsection beyond
            # Worked Example and Common Pitfalls (e.g., Definition, Base
            # Impedance Formula, CW/CZ modes, Fixed/Switched Shunts, etc.)
            non_example_subsections = [
                h for h in subsection_headings if h not in ("Worked Example", "Common Pitfalls")
            ]
            has_definition = len(non_example_subsections) > 0
            assert has_definition, (
                f"Domain '{heading}' missing a definition-type subsection "
                "(e.g., '### Definition' or '### Base Impedance Formula')"
            )

            # Domains 4 and 5 need CZ/CW mode subsections
            if "4." in heading:
                for cz in ["CZ=1", "CZ=2", "CZ=3"]:
                    assert any(cz in h for h in subsection_headings), (
                        f"Domain '{heading}' missing subsection for {cz}"
                    )
            if "5." in heading:
                for cw in ["CW=1", "CW=2", "CW=3"]:
                    assert any(cw in h for h in subsection_headings), (
                        f"Domain '{heading}' missing subsection for {cw}"
                    )

    def test_summary_table_present(self, doc_text: str) -> None:
        """T04: Summary Table section exists with 9+ data rows."""
        assert "## Summary Table" in doc_text, "Missing '## Summary Table' section"

        # Extract the summary table section
        summary_start = doc_text.index("## Summary Table")
        # Find the next ## section or end of file
        next_section = doc_text.find("\n## ", summary_start + 1)
        if next_section == -1:
            summary_section = doc_text[summary_start:]
        else:
            summary_section = doc_text[summary_start:next_section]

        # Count table rows (lines starting with |, excluding header separator)
        table_lines = [
            line.strip()
            for line in summary_section.splitlines()
            if line.strip().startswith("|") and not re.match(r"^\|[-\s|]+\|$", line.strip())
        ]
        # First line is the header, rest are data rows
        data_rows = [line for line in table_lines[1:] if line.startswith("|")]
        assert len(data_rows) >= 9, (
            f"Summary table has {len(data_rows)} data rows, expected at least 9"
        )

        # Verify expected columns
        header = table_lines[0] if table_lines else ""
        for col in ["Domain", "PSS/E Fields", "Unit", "Per-Unit Base", "Conversion"]:
            assert col.lower() in header.lower(), f"Summary table missing expected column: '{col}'"


# ---------------------------------------------------------------------------
# Worked example tests (T05-T07)
# ---------------------------------------------------------------------------


@pytest.mark.docs
class TestWorkedExamples:
    """T05-T07: Verify worked examples use realistic values and both directions."""

    def test_worked_examples_use_realistic_values(self, doc_sections: dict[str, str]) -> None:
        """T05: Worked examples use transmission-scale values."""
        for heading in DOMAIN_HEADINGS:
            section_text = _find_section(doc_sections, heading)
            # Extract the Worked Example subsection
            example_match = re.search(
                r"### Worked Example\s*\n(.*?)(?=\n### |\Z)",
                section_text,
                re.DOTALL,
            )
            assert example_match, f"Could not extract Worked Example from '{heading}'"
            example_text = example_match.group(1)

            # Extract all numeric values from the example
            numbers = [float(m) for m in re.findall(r"(?<!\w)(\d+\.?\d*)", example_text)]

            # Check for at least one voltage-scale value (69-500 kV)
            has_voltage = any(69 <= n <= 500 for n in numbers)
            # Check for at least one power-scale value (10-2000 MW/MVAR)
            has_power = any(10 <= n <= 2000 for n in numbers)
            # Check for at least one impedance-scale value (0.0001-1.0 pu)
            has_impedance = any(0.0001 <= n <= 1.0 for n in numbers)

            assert has_voltage or has_power or has_impedance, (
                f"Domain '{heading}' worked example lacks realistic "
                "transmission-scale values (expected voltage 69-500 kV, "
                "power 10-2000 MW/MVAR, or impedance 0.0001-1.0 pu)"
            )

    def test_worked_examples_show_both_directions(self, doc_sections: dict[str, str]) -> None:
        """T06: Each worked example shows both pu-to-physical and physical-to-pu."""
        pu_to_phys_patterns = [
            r"[Pp]er.unit to physical",
            r"pu\s*(?:to|->|-->|→)\s*(?:kV|ohm|MW|MVAR|siemens|A)",
            r"[Pp]er-unit to physical",
            r"_pu\s*\*",
            r"_pu \*",
            r"_ohm\s*=",  # Calculating physical ohms from per-unit
            r"_kV\s*=",  # Calculating physical kV from per-unit
            r"_MW\s*=",  # Calculating physical MW from per-unit
        ]
        phys_to_pu_patterns = [
            r"[Pp]hysical to per.unit",
            r"(?:kV|ohm|MW|MVAR|siemens|A)\s*(?:to|->|-->|→)\s*pu",
            r"[Pp]hysical to per-unit",
            r"/ (?:S_base|Z_base|BASKV|SBASE|V_base)",
            r"_pu\s*=\s*\d",
            r"_pu,\w+\s*=\s*\d",  # e.g. R_pu,system = 0.001750
            r"_system\s*=\s*\d",  # e.g. X12_system = 0.01417
        ]

        for heading in DOMAIN_HEADINGS:
            section_text = _find_section(doc_sections, heading)
            example_match = re.search(
                r"### Worked Example\s*\n(.*?)(?=\n### |\Z)",
                section_text,
                re.DOTALL,
            )
            assert example_match, f"No Worked Example in '{heading}'"
            example_text = example_match.group(1)

            has_pu_to_phys = any(re.search(p, example_text) for p in pu_to_phys_patterns)
            has_phys_to_pu = any(re.search(p, example_text) for p in phys_to_pu_patterns)

            assert has_pu_to_phys, (
                f"Domain '{heading}' worked example missing per-unit to physical conversion"
            )
            assert has_phys_to_pu, (
                f"Domain '{heading}' worked example missing physical to per-unit conversion"
            )

    def test_cz_mode_examples_cover_all_three_modes(self, doc_sections: dict[str, str]) -> None:
        """T07: 2W transformer impedance section covers CZ=1, CZ=2, CZ=3."""
        heading = "4. Two-Winding Transformer Impedance"
        section_text = _find_section(doc_sections, heading)
        assert section_text, f"Missing section '{heading}'"

        for cz_mode in ["CZ=1", "CZ=2", "CZ=3"]:
            # Find the CZ mode subsection or worked example referencing it
            assert cz_mode in section_text, f"Section '{heading}' does not mention {cz_mode}"
            # Verify there is at least one numeric calculation for each mode
            # Find text around each CZ mention and check for numbers
            cz_positions = [m.start() for m in re.finditer(cz_mode, section_text)]
            has_calculation = False
            for pos in cz_positions:
                surrounding = section_text[max(0, pos - 200) : pos + 500]
                numbers = re.findall(r"\d+\.\d+", surrounding)
                if len(numbers) >= 2:  # At least 2 numeric values = a calculation
                    has_calculation = True
                    break
            assert has_calculation, f"No numeric calculation found for {cz_mode} in '{heading}'"


# ---------------------------------------------------------------------------
# Pitfalls and tool coverage tests (T08-T10)
# ---------------------------------------------------------------------------


@pytest.mark.docs
class TestPitfallsAndToolCoverage:
    """T08-T10: Verify pitfalls sections and tool coverage."""

    def test_pitfalls_reference_at_least_three_tools(self, doc_sections: dict[str, str]) -> None:
        """T08: Each Common Pitfalls subsection mentions at least 3 tools."""
        for heading in DOMAIN_HEADINGS:
            section_text = _find_section(doc_sections, heading)
            pitfalls_match = re.search(
                r"### Common Pitfalls\s*\n(.*?)(?=\n### |\Z)",
                section_text,
                re.DOTALL,
            )
            assert pitfalls_match, f"No Common Pitfalls subsection in '{heading}'"
            pitfalls_text = pitfalls_match.group(1)
            pitfalls_lower = pitfalls_text.lower()

            tool_count = sum(1 for tool in TOOL_NAMES if tool.lower() in pitfalls_lower)
            assert tool_count >= 3, (
                f"Domain '{heading}' pitfalls mention only {tool_count} tools, "
                f"expected at least 3. Tools found: "
                f"{[t for t in TOOL_NAMES if t.lower() in pitfalls_lower]}"
            )

    def test_pitfalls_include_diagnostic_signature(self, doc_sections: dict[str, str]) -> None:
        """T09: At least 6/9 pitfalls sections contain diagnostic signature language."""
        diagnostic_patterns = [
            r"off by a factor",
            r"scaled by",
            r"differs by",
            r"consistent ratio",
            r"symptom",
            r"diagnostic signature",
            r"factor of",
            r"consistently scaled",
        ]

        domains_with_diagnostic = 0
        for heading in DOMAIN_HEADINGS:
            section_text = _find_section(doc_sections, heading)
            pitfalls_match = re.search(
                r"### Common Pitfalls\s*\n(.*?)(?=\n### |\Z)",
                section_text,
                re.DOTALL,
            )
            if not pitfalls_match:
                continue
            pitfalls_text = pitfalls_match.group(1).lower()
            if any(re.search(p, pitfalls_text) for p in diagnostic_patterns):
                domains_with_diagnostic += 1

        assert domains_with_diagnostic >= 6, (
            f"Only {domains_with_diagnostic}/9 pitfalls sections contain "
            "diagnostic signature language, expected at least 6"
        )

    def test_all_six_tools_mentioned_in_document(self, doc_text: str) -> None:
        """T10: All six tool names appear at least once in the document."""
        for tool in TOOL_NAMES:
            assert tool in doc_text, f"Tool '{tool}' not mentioned anywhere in the document"


# ---------------------------------------------------------------------------
# Cross-reference and notation tests (T11-T12)
# ---------------------------------------------------------------------------


@pytest.mark.docs
class TestCrossReferencesAndNotation:
    """T11-T12: Verify notation and cross-reference sections."""

    def test_notation_conventions_section_present(self, doc_text: str) -> None:
        """T11: Notation Conventions section defines S_base, V_base, Z_base, Y_base."""
        assert "## Notation Conventions" in doc_text, "Missing '## Notation Conventions' section"
        # Extract the section
        start = doc_text.index("## Notation Conventions")
        next_section = doc_text.find("\n## ", start + 1)
        if next_section == -1:
            notation_text = doc_text[start:]
        else:
            notation_text = doc_text[start:next_section]

        for symbol in ["S_base", "V_base", "Z_base", "Y_base"]:
            assert symbol in notation_text, (
                f"Notation Conventions section missing definition of '{symbol}'"
            )

    def test_cross_references_section_present(self, doc_text: str) -> None:
        """T12: Cross-References section references D7, PRD 01, PRD 04."""
        assert "## Cross-References" in doc_text, "Missing '## Cross-References' section"
        start = doc_text.index("## Cross-References")
        xref_text = doc_text[start:]

        # Check for D7 reference
        assert "D7" in xref_text, "Cross-References missing reference to Phase 1 D7"
        # Check for PRD 01 reference
        assert re.search(r"PRD[- ]01", xref_text), "Cross-References missing reference to PRD 01"
        # Check for PRD 04 reference
        assert re.search(r"PRD[- ]04", xref_text), "Cross-References missing reference to PRD 04"
