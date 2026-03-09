"""Structural validation tests for the rubric v4 amendment justification document.

Tests verify that data/fnm/docs/rubric-v4-justification.md contains all required
sections, covers all required arguments, respects grading boundary constraints,
and documents the FNM_PATH gating contract as specified in PRD 04/05.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DOC_PATH = REPO_ROOT / "data" / "fnm" / "docs" / "rubric-v4-justification.md"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_document() -> str:
    """Load the justification document as a string."""
    return DOC_PATH.read_text(encoding="utf-8")


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Split a markdown document into (header, body) tuples by H2 headers.

    The first tuple has an empty header string and contains content before the
    first H2.  Subsequent tuples use the H2 text (without ``## ``) as header.
    """
    parts = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
    sections: list[tuple[str, str]] = []
    # parts[0] is content before first H2
    sections.append(("", parts[0]))
    # remaining parts alternate: header, body, header, body, ...
    for i in range(1, len(parts), 2):
        header = parts[i].strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        sections.append((header, body))
    return sections


def _find_section(sections: list[tuple[str, str]], *keywords: str) -> tuple[str, str] | None:
    """Find the first section whose header contains any of the keywords (case-insensitive)."""
    for header, body in sections:
        for kw in keywords:
            if kw.lower() in header.lower():
                return header, body
    return None


def _get_executive_summary(text: str, sections: list[tuple[str, str]]) -> str:
    """Extract the executive summary content.

    The executive summary is either the content before the first H2 (if it
    contains substantive text) or the first H2 section if the pre-H2 content
    is just a title / front-matter.
    """
    # Content before first H2 (excluding leading H1 title line)
    pre_h2 = sections[0][1]
    # Strip the H1 title line(s) and any blank lines
    lines = pre_h2.strip().splitlines()
    content_lines = [ln for ln in lines if not ln.startswith("# ")]
    content = "\n".join(content_lines).strip()
    if len(content) > 100:
        return content
    # Fall back to first H2 section
    if len(sections) > 1:
        return sections[1][1]
    return content


def _count_sentences(text: str) -> int:
    """Count sentences in text by splitting on sentence-ending punctuation."""
    # Remove markdown table rows and blank lines
    lines = [ln for ln in text.strip().splitlines() if not ln.strip().startswith("|")]
    prose = " ".join(ln.strip() for ln in lines if ln.strip())
    # Split on period/question-mark/exclamation followed by space or end of string
    sentences = re.split(r"(?<=[.?!])\s+", prose)
    return len([s for s in sentences if len(s.strip()) > 10])


# ---------------------------------------------------------------------------
# Structural validation tests
# ---------------------------------------------------------------------------


@pytest.mark.docs
class TestStructuralValidation:
    """T01-T04: Structural completeness tests."""

    def test_document_exists(self) -> None:
        """T01: Verify the justification document exists and is non-empty."""
        assert DOC_PATH.exists(), f"Document not found at {DOC_PATH}"
        content = _load_document()
        assert len(content.strip()) > 0, "Document is empty"

    def test_all_required_sections_present(self) -> None:
        """T02: Verify all 8 required sections exist by matching H2 headers.

        Required sections (by key phrases in H2 headers):
        - S1: Executive summary (content before first H2 or first H2)
        - S2: "Phase 1" or "Data Model Fidelity"
        - S3: "Evidence" or "Synthetic"
        - S4: "Precedent"
        - S5: "Grading Impact"
        - S6: "Gating" or "FNM_PATH"
        - S7: "Fail" or "Asymmetry"
        - S8: "Cross-Reference"
        """
        text = _load_document()
        sections = _split_sections(text)

        # S1: executive summary -- either pre-H2 content or first H2
        exec_summary = _get_executive_summary(text, sections)
        assert len(exec_summary.strip()) > 100, (
            "S1 (Executive Summary): no substantive content found before or at first H2"
        )

        # S2-S8: check H2 headers by key phrases
        section_checks = {
            "S2 (Data Model Fidelity)": ("Phase 1", "Data Model Fidelity"),
            "S3 (FNM vs Synthetic Evidence)": ("Evidence", "Synthetic"),
            "S4 (Precedent)": ("Precedent",),
            "S5 (Grading Impact)": ("Grading Impact",),
            "S6 (FNM_PATH Gating)": ("Gating", "FNM_PATH"),
            "S7 (Failure Asymmetry)": ("Fail", "Asymmetry"),
            "S8 (Cross-References)": ("Cross-Reference",),
        }

        missing = []
        for label, keywords in section_checks.items():
            result = _find_section(sections, *keywords)
            if result is None:
                missing.append(label)

        assert not missing, f"Missing required sections: {', '.join(missing)}"

    def test_executive_summary_is_concise(self) -> None:
        """T03: Verify executive summary is between 3 and 10 sentences."""
        text = _load_document()
        sections = _split_sections(text)
        exec_summary = _get_executive_summary(text, sections)
        sentence_count = _count_sentences(exec_summary)
        assert 3 <= sentence_count <= 10, (
            f"Executive summary has {sentence_count} sentences, expected 3-10"
        )

    def test_document_word_count_in_range(self) -> None:
        """T04: Verify total document word count is between 1,500 and 5,000."""
        text = _load_document()
        word_count = len(text.split())
        assert 1500 <= word_count <= 5000, f"Document has {word_count} words, expected 1,500-5,000"


# ---------------------------------------------------------------------------
# Argument coverage tests
# ---------------------------------------------------------------------------


@pytest.mark.docs
class TestArgumentCoverage:
    """T05-T07: Argument coverage tests."""

    def test_record_type_gap_table_present(self) -> None:
        """T05: Verify S3 contains a markdown table with key record types.

        The table must have at least 5 data rows and mention both
        '3-winding' and 'switched shunt' (case-insensitive).
        """
        text = _load_document()
        sections = _split_sections(text)
        result = _find_section(sections, "Evidence", "Synthetic")
        assert result is not None, "S3 section not found"
        _, body = result

        # Find markdown table rows (lines starting with |, excluding header separator)
        table_rows = [
            ln
            for ln in body.strip().splitlines()
            if ln.strip().startswith("|") and not re.match(r"^\|[\s\-:|]+\|$", ln.strip())
        ]
        # Exclude header rows (first row of each table)
        # Heuristic: data rows contain at least one non-title-case cell
        data_rows = [
            r for r in table_rows if not all(c.strip().istitle() for c in r.split("|")[1:-1])
        ]
        assert len(data_rows) >= 5, (
            f"S3 record type gap table has {len(data_rows)} data rows, expected >= 5"
        )

        body_lower = body.lower()
        assert "3-winding" in body_lower, (
            "S3 table must mention '3-winding' or '3-Winding' transformers"
        )
        assert "switched shunt" in body_lower, (
            "S3 table must mention 'switched shunt' or 'Switched Shunt'"
        )

    def test_field_coverage_gap_referenced(self) -> None:
        """T06: Verify S3 references field-level coverage analysis.

        Must contain either:
        (a) a markdown table with 'DCPF-critical' and a numeric value, or
        (b) prose with both 'DCPF-critical' and 'field' in the same paragraph.
        """
        text = _load_document()
        sections = _split_sections(text)
        result = _find_section(sections, "Evidence", "Synthetic")
        assert result is not None, "S3 section not found"
        _, body = result

        # Check for table with DCPF-critical and a number
        has_table = False
        for line in body.splitlines():
            if "DCPF-critical" in line and re.search(r"\d+", line):
                has_table = True
                break

        # Check for prose with both terms in same paragraph
        has_prose = False
        paragraphs = re.split(r"\n\s*\n", body)
        for para in paragraphs:
            if "DCPF-critical" in para and "field" in para.lower():
                has_prose = True
                break

        assert has_table or has_prose, (
            "S3 must reference field-level coverage with 'DCPF-critical' "
            "in either a table with numeric values or prose with 'field'"
        )

    def test_v2_precedent_cited(self) -> None:
        """T07: Verify S4 cites the rubric v2 precedent specifically.

        Must contain all of:
        - 'sub-question' or 'sub-questions'
        - 'SCOPF'
        - 'inform' or 'readiness indicator'
        """
        text = _load_document()
        sections = _split_sections(text)
        result = _find_section(sections, "Precedent")
        assert result is not None, "S4 (Precedent) section not found"
        _, body = result

        body_lower = body.lower()

        assert "sub-question" in body_lower or "sub-questions" in body_lower, (
            "S4 must mention 'sub-question' or 'sub-questions' (the v2 additions)"
        )
        assert "scopf" in body_lower, (
            "S4 must mention 'SCOPF' (the most significant v2 sub-question)"
        )
        assert "inform" in body_lower or "readiness indicator" in body_lower, (
            "S4 must contain 'inform' or 'readiness indicator' (grading mechanism language)"
        )


# ---------------------------------------------------------------------------
# Boundary and constraint tests
# ---------------------------------------------------------------------------


@pytest.mark.docs
class TestBoundaryConstraints:
    """T08-T10: Boundary and constraint validation tests."""

    def test_no_threshold_changes_claimed(self) -> None:
        """T08: Verify S5 confirms grade boundaries are unchanged.

        At least one sentence must contain both a negation word and a
        grade-boundary term.
        """
        text = _load_document()
        sections = _split_sections(text)
        result = _find_section(sections, "Grading Impact")
        assert result is not None, "S5 (Grading Impact) section not found"
        _, body = result

        negation_words = {"no", "not", "unchanged", "unaffected", "invariant"}
        boundary_terms = {"threshold", "boundary", "a/b/c", "grade boundary", "grade boundaries"}

        # Check sentence by sentence
        sentences = re.split(r"(?<=[.?!])\s+", body)
        found = False
        for sentence in sentences:
            sentence_lower = sentence.lower()
            has_negation = any(
                re.search(rf"\b{re.escape(w)}\b", sentence_lower) for w in negation_words
            )
            has_boundary = any(term in sentence_lower for term in boundary_terms)
            if has_negation and has_boundary:
                found = True
                break

        assert found, (
            "S5 must contain at least one sentence with both a negation word "
            "(no/not/unchanged/unaffected/invariant) and a grade-boundary term "
            "(threshold/boundary/A/B/C/grade boundary)"
        )

    def test_fnm_path_gating_documented(self) -> None:
        """T09: Verify S6 documents the FNM_PATH gating contract.

        Must contain all of:
        - 'FNM_PATH'
        - 'skip' or 'skipped'
        - 'additive' or 'complete grades' or 'without FNM'
        """
        text = _load_document()
        sections = _split_sections(text)
        result = _find_section(sections, "Gating", "FNM_PATH")
        assert result is not None, "S6 (FNM_PATH Gating) section not found"
        _, body = result

        body_lower = body.lower()

        assert "fnm_path" in body_lower, "S6 must mention 'FNM_PATH'"
        assert "skip" in body_lower or "skipped" in body_lower, (
            "S6 must mention 'skip' or 'skipped'"
        )
        assert (
            "additive" in body_lower
            or "complete grades" in body_lower
            or "without fnm" in body_lower
        ), "S6 must mention 'additive', 'complete grades', or 'without FNM'"

    def test_no_tool_rankings_or_recommendations(self) -> None:
        """T10: Verify the document contains no tool-ranking language.

        The justification must be tool-agnostic and not contain any patterns
        that rank, recommend, or compare tools by quality.
        """
        text = _load_document()
        text_lower = text.lower()

        forbidden_patterns = [
            "best tool",
            "worst tool",
            "recommended tool",
            "winning tool",
            "ranks higher",
            "ranks lower",
            "should choose",
            "should select",
        ]

        found = [p for p in forbidden_patterns if p in text_lower]
        assert not found, (
            f"Document contains tool-ranking language: {found}. "
            "The justification must be tool-agnostic."
        )
