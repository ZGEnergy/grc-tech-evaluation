"""Tests for Protocol v5 Amendment — Suite G (FNM Ingestion).

Validates that the amended Phase1_Test_Protocol.md contains all required
structural elements, content, grade mappings, and preserves existing content.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_PATH = REPO_ROOT / "evaluation_guides" / "Phase1_Test_Protocol.md"

pytestmark = pytest.mark.docs


@pytest.fixture(scope="module")
def protocol_text() -> str:
    """Load the full protocol markdown text."""
    return PROTOCOL_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Helper: extract text between two section headings
# ---------------------------------------------------------------------------


def _section_text(
    full: str, heading_pattern: str, next_heading_level: str = "###"
) -> str:
    """Return text from a heading matching *heading_pattern* to the next same-level heading."""
    m = re.search(rf"^{next_heading_level}\s+{heading_pattern}", full, re.MULTILINE)
    if not m:
        return ""
    start = m.start()
    rest = full[m.end() :]
    m2 = re.search(rf"^{next_heading_level}\s+", rest, re.MULTILINE)
    end = m.end() + m2.start() if m2 else len(full)
    return full[start:end]


# ===== Structural Integrity Tests (T01-T07) =====


class TestStructuralIntegrity:
    """T01-T07: structural presence of required sections and elements."""

    def test_suite_g_section_exists(self, protocol_text: str) -> None:
        """T01: Suite G heading exists, after Suite F and before Phase 2 Readiness."""
        suite_g_match = re.search(
            r"^### Test Suite G: FNM Ingestion", protocol_text, re.MULTILINE
        )
        assert suite_g_match is not None, "Suite G heading not found"

        suite_f_match = re.search(r"^### Test Suite F:", protocol_text, re.MULTILINE)
        assert suite_f_match is not None, "Suite F heading not found"

        phase2_match = re.search(
            r"^### Phase 2 Readiness Findings", protocol_text, re.MULTILINE
        )
        assert phase2_match is not None, "Phase 2 Readiness Findings heading not found"

        assert suite_f_match.start() < suite_g_match.start() < phase2_match.start(), (
            "Suite G must appear after Suite F and before Phase 2 Readiness Findings"
        )

    def test_all_5_test_cases_present(self, protocol_text: str) -> None:
        """T02: All 5 test case IDs in a table with correct columns."""
        suite_g = _section_text(protocol_text, r"Test Suite G: FNM Ingestion")
        assert suite_g, "Suite G section not found"

        for test_id in ["G-FNM-1", "G-FNM-2", "G-FNM-3", "G-FNM-4", "G-FNM-5"]:
            assert test_id in suite_g, f"Test case {test_id} not found in Suite G"

        # Check table header columns
        assert "| ID |" in suite_g, "Table missing ID column"
        assert "| Test |" in suite_g or "Test |" in suite_g, "Table missing Test column"
        assert "Inputs" in suite_g, "Table missing Inputs column"
        assert "Procedure" in suite_g, "Table missing Procedure column"
        assert "Pass Condition" in suite_g, "Table missing Pass Condition column"
        assert "References" in suite_g, "Table missing References column"

    def test_fnm_path_gating_in_general_rules(self, protocol_text: str) -> None:
        """T03: General Rules section contains FNM_PATH gating rule."""
        general_rules = _section_text(protocol_text, r"General Rules")
        assert general_rules, "General Rules section not found"
        assert "FNM_PATH" in general_rules, "FNM_PATH not mentioned in General Rules"
        assert "Suite G" in general_rules or "FNM Ingestion" in general_rules, (
            "General Rules FNM_PATH rule does not mention Suite G"
        )

    def test_reference_networks_table_has_large(self, protocol_text: str) -> None:
        """T04: Reference Networks table has LARGE row with FNM."""
        # Find the Reference Networks table area
        ref_net_section = _section_text(protocol_text, r"Reference Networks")
        assert ref_net_section, "Reference Networks section not found"

        # Look for a table row with LARGE
        large_rows = [
            line
            for line in ref_net_section.splitlines()
            if "LARGE" in line and "|" in line
        ]
        assert large_rows, "No LARGE row in Reference Networks table"

        large_row = large_rows[0]
        assert "FNM Annual S01" in large_row, "LARGE row missing 'FNM Annual S01'"
        assert "FNM_PATH" in large_row, "LARGE row missing 'FNM_PATH' reference"

    def test_results_recording_has_fnm_ingestion(self, protocol_text: str) -> None:
        """T05: Results Recording has fnm_ingestion/ directory with G-FNM files."""
        results_section = _section_text(
            protocol_text, r"Results Recording", next_heading_level="##"
        )
        assert results_section, "Results Recording section not found"
        assert "fnm_ingestion/" in results_section, (
            "fnm_ingestion/ directory not in Results"
        )

        for test_id in ["G-FNM-1", "G-FNM-2", "G-FNM-3", "G-FNM-4", "G-FNM-5"]:
            assert test_id in results_section, (
                f"{test_id} not listed in Results Recording fnm_ingestion directory"
            )

    def test_revision_history_has_v5(self, protocol_text: str) -> None:
        """T06: Revision History table has v5 row mentioning Suite G and FNM."""
        rev_section = _section_text(
            protocol_text, r"Revision History", next_heading_level="##"
        )
        assert rev_section, "Revision History section not found"

        # Find v5 row in table
        v5_rows = [
            line
            for line in rev_section.splitlines()
            if re.search(r"\|\s*v5\s*\|", line)
        ]
        assert v5_rows, "No v5 row in Revision History table"

        v5_row = v5_rows[0]
        assert "Suite G" in v5_row, "v5 row does not mention 'Suite G'"
        assert "FNM" in v5_row, "v5 row does not mention 'FNM'"

    def test_protocol_version_note_updated(self, protocol_text: str) -> None:
        """T07: Results Recording contains v5 protocol version guidance."""
        results_section = _section_text(
            protocol_text, r"Results Recording", next_heading_level="##"
        )
        assert results_section, "Results Recording section not found"
        assert (
            'protocol_version: "v5"' in results_section
            or "protocol_version" in results_section
        )
        assert (
            "mixed-version" in results_section.lower()
            or "Mixed-version" in results_section
        ), "Results Recording missing mixed-version guidance"


# ===== Content Completeness Tests (T08-T12) =====


class TestContentCompleteness:
    """T08-T12: verify content details of each G-FNM test case."""

    def test_g_fnm_1_is_gate_test(self, protocol_text: str) -> None:
        """T08: G-FNM-1 is identified as the gate test."""
        suite_g = _section_text(protocol_text, r"Test Suite G: FNM Ingestion")
        assert suite_g, "Suite G section not found"

        # Check for gate test language
        gate_indicators = [
            "gate test" in suite_g.lower(),
            "G-FNM-1" in suite_g and "gate" in suite_g.lower(),
        ]
        assert any(gate_indicators), "G-FNM-1 not identified as gate test"

        # Check that failure skips G-FNM-2 through G-FNM-5
        assert re.search(r"G-FNM-2\s+through\s+G-FNM-5\s+(are\s+)?skipped", suite_g), (
            "No language about G-FNM-2 through G-FNM-5 being skipped on G-FNM-1 failure"
        )

    def test_g_fnm_2_references_criticality_matrix(self, protocol_text: str) -> None:
        """T09: G-FNM-2 references field-criticality-matrix.md."""
        suite_g = _section_text(protocol_text, r"Test Suite G: FNM Ingestion")
        assert suite_g, "Suite G section not found"
        assert "field-criticality-matrix.md" in suite_g, (
            "G-FNM-2 missing reference to field-criticality-matrix.md"
        )

    def test_g_fnm_3_references_pass_conditions(self, protocol_text: str) -> None:
        """T10: G-FNM-3 references pass_conditions.json and dcpf/ directory."""
        suite_g = _section_text(protocol_text, r"Test Suite G: FNM Ingestion")
        assert suite_g, "Suite G section not found"
        assert "pass_conditions.json" in suite_g, (
            "G-FNM-3 missing reference to pass_conditions.json"
        )
        assert "data/fnm/reference/dcpf/" in suite_g, (
            "G-FNM-3 missing reference to data/fnm/reference/dcpf/"
        )

    def test_g_fnm_4_references_pass_conditions(self, protocol_text: str) -> None:
        """T11: G-FNM-4 references pass_conditions.json and acpf/ directory."""
        suite_g = _section_text(protocol_text, r"Test Suite G: FNM Ingestion")
        assert suite_g, "Suite G section not found"
        assert "pass_conditions.json" in suite_g, (
            "G-FNM-4 missing reference to pass_conditions.json"
        )
        assert "data/fnm/reference/acpf/" in suite_g, (
            "G-FNM-4 missing reference to data/fnm/reference/acpf/"
        )

    def test_g_fnm_5_references_supplemental_csv_docs(self, protocol_text: str) -> None:
        """T12: G-FNM-5 references supplemental-csvs.md and all 7 CSV names."""
        suite_g = _section_text(protocol_text, r"Test Suite G: FNM Ingestion")
        assert suite_g, "Suite G section not found"
        assert "supplemental-csvs.md" in suite_g, (
            "G-FNM-5 missing reference to supplemental-csvs.md"
        )

        csv_names = [
            "LINE_AND_TRANSFORMER.csv",
            "TRADING_HUB.csv",
            "GEN_DISTRIBUTION_FACTOR.csv",
            "CONTINGENCY.csv",
            "INTERFACE.csv",
            "INTERFACE_ELEMENT.csv",
            "OUTAGE.csv",
        ]
        for csv_name in csv_names:
            assert csv_name in suite_g, f"G-FNM-5 missing CSV name: {csv_name}"


# ===== Grade Mapping Tests (T13-T14) =====


class TestGradeMapping:
    """T13-T14: verify Suite G grade mapping in 'From Test Results to Grades'."""

    def test_suite_g_in_grades_section(self, protocol_text: str) -> None:
        """T13: Grades section has Suite G mapping to Expressiveness and Extensibility."""
        grades_section = _section_text(
            protocol_text, r"From Test Results to Grades", next_heading_level="##"
        )
        assert grades_section, "'From Test Results to Grades' section not found"

        # Check for Suite G or FNM Ingestion mention
        has_suite_g = "Suite G" in grades_section or "FNM Ingestion" in grades_section
        assert has_suite_g, "Grades section missing Suite G / FNM Ingestion reference"

        # Check for both Expressiveness and Extensibility mappings
        assert "Expressiveness" in grades_section, (
            "Grades section Suite G item missing Expressiveness mapping"
        )
        assert "Extensibility" in grades_section, (
            "Grades section Suite G item missing Extensibility mapping"
        )

    def test_grades_section_references_rubric_v4(self, protocol_text: str) -> None:
        """T14: Suite G grades mapping references rubric v4."""
        grades_section = _section_text(
            protocol_text, r"From Test Results to Grades", next_heading_level="##"
        )
        assert grades_section, "'From Test Results to Grades' section not found"

        has_rubric_v4_ref = (
            "rubric v4" in grades_section.lower()
            or "v4 grading note" in grades_section.lower()
        )
        assert has_rubric_v4_ref, (
            "Grades section Suite G item missing rubric v4 reference"
        )


# ===== Preservation Tests (T15-T16) =====


class TestPreservation:
    """T15-T16: verify existing content is preserved."""

    def test_existing_suites_preserved(self, protocol_text: str) -> None:
        """T15: All existing section headings still present."""
        required_headings = [
            "### Gate Test: Data Ingestion",
            "### Test Suite A: Problem Expressiveness",
            "### Test Suite B: Extensibility",
            "### Test Suite C: Scalability",
            "### Test Suite D: Workforce Accessibility",
            "### Test Suite E: Maturity & Sustainability",
            "### Test Suite F: Supply Chain, Inspectability & Licensing Risk",
            "### Phase 2 Readiness Findings",
        ]
        for heading in required_headings:
            assert heading in protocol_text, f"Missing existing heading: {heading}"

    def test_existing_revision_history_preserved(self, protocol_text: str) -> None:
        """T16: Revision History still has v1, v2, v3, v4 rows."""
        rev_section = _section_text(
            protocol_text, r"Revision History", next_heading_level="##"
        )
        assert rev_section, "Revision History section not found"

        for version in ["v1", "v2", "v3", "v4"]:
            v_rows = [
                line
                for line in rev_section.splitlines()
                if re.search(rf"\|\s*{version}\s*\|", line)
            ]
            assert v_rows, f"Revision History missing {version} row"
