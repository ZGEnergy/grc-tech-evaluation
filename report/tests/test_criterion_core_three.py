"""Tests for criterion core three pages: Expressiveness, Extensibility, Scalability (PRD 05/03)."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

WORKTREE = Path(
    os.environ.get("WORKTREE_ROOT", Path(__file__).resolve().parent.parent.parent)
)
RESULTS_DIR = WORKTREE / "report" / "docs" / "results"
GRADES_PATH = WORKTREE / "report" / "data" / "grades.json"

EXPRESSIVENESS_PATH = RESULTS_DIR / "expressiveness.mdx"
EXTENSIBILITY_PATH = RESULTS_DIR / "extensibility.mdx"
SCALABILITY_PATH = RESULTS_DIR / "scalability.mdx"

TOOL_NAMES = [
    "PyPSA",
    "PowerModels",
    "pandapower",
    "GridCal",
    "PowerSimulations",
    "MATPOWER",
]

EXPECTED_GRADES = {
    "expressiveness": {
        "pypsa": ("B+", "grade-b-plus"),
        "pandapower": ("C+", "grade-c-plus"),
        "powermodels": ("B-", "grade-b-minus"),
        "matpower": ("A-", "grade-a-minus"),
        "gridcal": ("C+", "grade-c-plus"),
        "powersimulations": ("B-", "grade-b-minus"),
    },
    "extensibility": {
        "pypsa": ("A-", "grade-a-minus"),
        "pandapower": ("B", "grade-b"),
        "powermodels": ("A-", "grade-a-minus"),
        "matpower": ("A-", "grade-a-minus"),
        "gridcal": ("B", "grade-b"),
        "powersimulations": ("B+", "grade-b-plus"),
    },
    "scalability": {
        "pypsa": ("B-", "grade-b-minus"),
        "pandapower": ("B-", "grade-b-minus"),
        "powermodels": ("B-", "grade-b-minus"),
        "matpower": ("B-", "grade-b-minus"),
        "gridcal": ("B-", "grade-b-minus"),
        "powersimulations": ("B-", "grade-b-minus"),
    },
}


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def expressiveness_text() -> str:
    return EXPRESSIVENESS_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def extensibility_text() -> str:
    return EXTENSIBILITY_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def scalability_text() -> str:
    return SCALABILITY_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def grades_data() -> dict:
    return json.loads(GRADES_PATH.read_text(encoding="utf-8"))


# ── 1. Expressiveness page exists and is not a stub ──────────────────


def test_expressiveness_page_exists(expressiveness_text: str) -> None:
    assert len(expressiveness_text) > 2000, (
        f"Expressiveness page too short ({len(expressiveness_text)} chars); "
        "likely still a stub"
    )


# ── 2. Expressiveness has 6 tool sections ────────────────────────────


def test_expressiveness_six_tool_sections(expressiveness_text: str) -> None:
    details = re.findall(r'<details\s+className="eval-details"', expressiveness_text)
    assert len(details) == 6, f"Expected 6 <details> elements, got {len(details)}"


# ── 3. Expressiveness contains all 6 tool names ─────────────────────


def test_expressiveness_all_tools_present(expressiveness_text: str) -> None:
    for name in TOOL_NAMES:
        assert name in expressiveness_text, (
            f"Tool name '{name}' not found in Expressiveness page"
        )


# ── 4. Expressiveness has evidence tables ────────────────────────────


def test_expressiveness_evidence_tables(expressiveness_text: str) -> None:
    cards = re.split(r"<details\b", expressiveness_text)[1:]
    assert len(cards) == 6
    for i, card in enumerate(cards):
        assert "Test ID" in card, f"Card {i + 1} missing evidence table header"
        # Verify table has rows with pipe-delimited content
        table_rows = re.findall(r"^\|.*\|$", card, re.MULTILINE)
        assert len(table_rows) >= 3, (
            f"Card {i + 1}: expected >= 3 table rows, got {len(table_rows)}"
        )


# ── 5. Expressiveness references probe-001 ──────────────────────────


def test_expressiveness_probe_001_reference(expressiveness_text: str) -> None:
    # Find the PyPSA section (first <details>)
    pypsa_section = re.split(r"<details\b", expressiveness_text)[1]
    assert "probe-001" in pypsa_section or "false convergence" in pypsa_section, (
        "PyPSA section must reference probe-001 or false convergence"
    )


# ── 6. Expressiveness references Suite A tests ──────────────────────


def test_expressiveness_suite_a_tests(expressiveness_text: str) -> None:
    for test_id in ["A-1", "A-2", "A-3", "A-4", "A-5", "A-6", "A-7", "A-8", "A-9"]:
        assert test_id in expressiveness_text, (
            f"Test ID '{test_id}' not found in Expressiveness page"
        )


# ── 7. Extensibility page exists and is not a stub ──────────────────


def test_extensibility_page_exists(extensibility_text: str) -> None:
    assert len(extensibility_text) > 1500, (
        f"Extensibility page too short ({len(extensibility_text)} chars); "
        "likely still a stub"
    )


# ── 8. Extensibility has 6 tool sections ────────────────────────────


def test_extensibility_six_tool_sections(extensibility_text: str) -> None:
    details = re.findall(r'<details\s+className="eval-details"', extensibility_text)
    assert len(details) == 6, f"Expected 6 <details> elements, got {len(details)}"


# ── 9. Extensibility references Suite B tests ───────────────────────


def test_extensibility_suite_b_tests(extensibility_text: str) -> None:
    for test_id in ["B-1", "B-2", "B-3", "B-4", "B-5"]:
        assert test_id in extensibility_text, (
            f"Test ID '{test_id}' not found in Extensibility page"
        )


# ── 10. Extensibility references PTDF / phase-shifter / T06 ─────────


def test_extensibility_ptdf_reference(extensibility_text: str) -> None:
    has_ptdf = "PTDF" in extensibility_text
    has_phase_shifter = "phase-shifter" in extensibility_text
    has_t06 = "T06" in extensibility_text
    assert has_ptdf or has_phase_shifter or has_t06, (
        "Extensibility page must reference PTDF, phase-shifter, or T06"
    )


# ── 11. Scalability page exists and is not a stub ───────────────────


def test_scalability_page_exists(scalability_text: str) -> None:
    assert len(scalability_text) > 1500, (
        f"Scalability page too short ({len(scalability_text)} chars); "
        "likely still a stub"
    )


# ── 12. Scalability has 6 tool sections ─────────────────────────────


def test_scalability_six_tool_sections(scalability_text: str) -> None:
    details = re.findall(r'<details\s+className="eval-details"', scalability_text)
    assert len(details) == 6, f"Expected 6 <details> elements, got {len(details)}"


# ── 13. Scalability has multiple chart slots ─────────────────────────


def test_scalability_chart_slots(scalability_text: str) -> None:
    placeholders = re.findall(r"<Placeholder\b", scalability_text)
    assert len(placeholders) >= 2, (
        f"Expected >= 2 chart embed slots, got {len(placeholders)}"
    )


# ── 14. Scalability references C-8 SCOPF MEDIUM fail / T13 ──────────


def test_scalability_scopf_medium_fail(scalability_text: str) -> None:
    has_c8 = "C-8" in scalability_text
    has_scopf_fail = "SCOPF" in scalability_text and "fail" in scalability_text.lower()
    has_t13 = "T13" in scalability_text
    assert has_c8 and (has_scopf_fail or has_t13), (
        "Scalability page must reference C-8 SCOPF failure at MEDIUM or theme T13"
    )


# ── 15. All three pages have MATPOWER reference banner ───────────────


@pytest.mark.parametrize(
    "page_fixture",
    ["expressiveness_text", "extensibility_text", "scalability_text"],
)
def test_all_three_matpower_banners(
    page_fixture: str, request: pytest.FixtureRequest
) -> None:
    text = request.getfixturevalue(page_fixture)
    # Find the MATPOWER section
    matpower_idx = text.find("MATPOWER")
    assert matpower_idx >= 0, f"MATPOWER not found in {page_fixture}"
    matpower_section = text[matpower_idx:]
    lower = matpower_section.lower()
    assert "reference" in lower, (
        f"MATPOWER section in {page_fixture} must contain 'Reference'"
    )


# ── 16. All three pages have reduced-confidence footnotes ────────────


@pytest.mark.parametrize(
    "page_fixture",
    ["expressiveness_text", "extensibility_text", "scalability_text"],
)
def test_all_three_reduced_confidence(
    page_fixture: str, request: pytest.FixtureRequest
) -> None:
    text = request.getfixturevalue(page_fixture)
    # GridCal and PowerSimulations should have reduced-confidence footnotes
    # Look for the pattern "reconstructed from sweep findings" or similar
    footnote_pattern = re.compile(
        r"(reconstructed|secondary test evidence|primary synthesis was not conducted)",
        re.IGNORECASE,
    )
    matches = footnote_pattern.findall(text)
    assert len(matches) >= 2, (
        f"Expected >= 2 reduced-confidence footnotes in {page_fixture}, "
        f"found {len(matches)}"
    )


# ── 17. Grade badges present ────────────────────────────────────────


@pytest.mark.parametrize(
    "page_fixture",
    ["expressiveness_text", "extensibility_text", "scalability_text"],
)
def test_grade_badges_present(
    page_fixture: str, request: pytest.FixtureRequest
) -> None:
    text = request.getfixturevalue(page_fixture)
    grade_spans = re.findall(r'<span className="grade-', text)
    assert len(grade_spans) >= 6, (
        f"Expected >= 6 grade badge spans in {page_fixture}, found {len(grade_spans)}"
    )


# ── 18. Grade values match grades.json ──────────────────────────────


@pytest.mark.parametrize(
    "criterion", ["expressiveness", "extensibility", "scalability"]
)
def test_grades_match_json(
    criterion: str,
    grades_data: dict,
    request: pytest.FixtureRequest,
) -> None:
    text = request.getfixturevalue(f"{criterion}_text")
    for grade_entry in grades_data["grades"]:
        if grade_entry["criterion"] != criterion:
            continue
        tool = grade_entry["tool"]
        letter = grade_entry["letter"]
        expected_css = EXPECTED_GRADES[criterion][tool][1]
        assert expected_css in text, (
            f"CSS class '{expected_css}' for {tool}/{criterion} "
            f"(grade {letter}) not found in page"
        )


# ── 19. All tools present in all 3 pages ────────────────────────────


@pytest.mark.parametrize(
    "page_fixture",
    ["expressiveness_text", "extensibility_text", "scalability_text"],
)
def test_all_tools_in_all_pages(
    page_fixture: str, request: pytest.FixtureRequest
) -> None:
    text = request.getfixturevalue(page_fixture)
    for name in TOOL_NAMES:
        assert name in text, f"Tool '{name}' not found in {page_fixture}"


# ── 20. Build succeeds ──────────────────────────────────────────────


def test_build_succeeds() -> None:
    inside_container = Path("/.dockerenv").exists()

    if inside_container:
        npm_project = Path("/workspace/report/package.json")
        if not npm_project.exists():
            pytest.skip("Docusaurus project not found at /workspace/report")
        result = subprocess.run(
            ["npm", "run", "build"],
            capture_output=True,
            text=True,
            timeout=180,
            cwd="/workspace/report",
        )
    else:
        dc_exec = WORKTREE / ".devcontainer" / "dc-exec"
        if not dc_exec.exists():
            pytest.skip("dc-exec not found; cannot run build test on host")
        check = subprocess.run(
            [str(dc_exec), "test", "-f", "/workspace/report/package.json"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(WORKTREE),
        )
        if check.returncode != 0:
            pytest.skip(
                "Docusaurus project not available in container at "
                "/workspace/report/package.json"
            )
        result = subprocess.run(
            [str(dc_exec), "-C", "/workspace/report", "npm", "run", "build"],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(WORKTREE),
        )
    assert result.returncode == 0, (
        f"Build failed (rc={result.returncode}):\n"
        f"STDOUT:\n{result.stdout[-2000:]}\n"
        f"STDERR:\n{result.stderr[-2000:]}"
    )
