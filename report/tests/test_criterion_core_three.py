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

# The core three pages use ### headings with tier labels (Strong/Adequate/Weak/Failing),
# not <details> cards or letter-grade CSS classes.


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
    headings = re.findall(r"^### .+", expressiveness_text, re.MULTILINE)
    assert len(headings) == 6, f"Expected 6 ### tool headings, got {len(headings)}"


# ── 3. Expressiveness contains all 6 tool names ─────────────────────


def test_expressiveness_all_tools_present(expressiveness_text: str) -> None:
    for name in TOOL_NAMES:
        assert name in expressiveness_text, (
            f"Tool name '{name}' not found in Expressiveness page"
        )


# ── 4. Expressiveness has evidence tables ────────────────────────────


def test_expressiveness_has_comparison_table(expressiveness_text: str) -> None:
    # The cross-tool comparison table appears before the per-tool sections
    table_rows = re.findall(r"^\|.*\|$", expressiveness_text, re.MULTILINE)
    assert len(table_rows) >= 8, (
        f"Expected >= 8 table rows (header + separator + 6 tools), got {len(table_rows)}"
    )


# ── 5. Expressiveness references key tests ───────────────────────────


def test_expressiveness_key_test_references(expressiveness_text: str) -> None:
    # A-9 (SCOPF), A-10 (lossy DCOPF), A-11 (distributed slack), A-12 (storage)
    for test_id in ["A-9", "A-10", "A-11", "A-12"]:
        assert test_id in expressiveness_text, (
            f"Test ID '{test_id}' not found in Expressiveness page"
        )


# ── 6. Expressiveness references Suite A tests ──────────────────────


def test_expressiveness_suite_a_tests(expressiveness_text: str) -> None:
    # A-7 and A-8 were removed in protocol v10
    for test_id in ["A-1", "A-2", "A-3", "A-4", "A-5", "A-6", "A-9"]:
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
    headings = re.findall(r"^### .+", extensibility_text, re.MULTILINE)
    assert len(headings) == 6, f"Expected 6 ### tool headings, got {len(headings)}"


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
    headings = re.findall(r"^### .+", scalability_text, re.MULTILINE)
    assert len(headings) == 6, f"Expected 6 ### tool headings, got {len(headings)}"


# ── 13. Scalability has chart component ──────────────────────────────


def test_scalability_chart_component(scalability_text: str) -> None:
    assert "CriterionChart" in scalability_text, (
        "Scalability page must include CriterionChart component"
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
    matpower_idx = text.find("MATPOWER")
    assert matpower_idx >= 0, f"MATPOWER not found in {page_fixture}"
    matpower_section = text[matpower_idx:]
    lower = matpower_section.lower()
    assert "reference" in lower, (
        f"MATPOWER section in {page_fixture} must contain 'Reference'"
    )


# ── 16. All three pages contain tier labels ────────────────────────


@pytest.mark.parametrize(
    "page_fixture",
    ["expressiveness_text", "extensibility_text", "scalability_text"],
)
def test_all_three_tier_labels(
    page_fixture: str, request: pytest.FixtureRequest
) -> None:
    text = request.getfixturevalue(page_fixture)
    tier_labels = re.findall(r"\b(Strong|Adequate|Weak|Failing)\b", text)
    assert len(tier_labels) >= 6, (
        f"Expected >= 6 tier labels in {page_fixture}, found {len(tier_labels)}"
    )


# ── 17. Tier labels in headings match grades.json ─────────────────


TIER_MAP = {"Strong": 3, "Adequate": 2, "Weak": 1, "Failing": 0}


@pytest.mark.parametrize(
    "criterion", ["expressiveness", "extensibility", "scalability"]
)
def test_grades_match_json(
    criterion: str,
    grades_data: dict,
    request: pytest.FixtureRequest,
) -> None:
    text = request.getfixturevalue(f"{criterion}_text")
    # Extract tier from ### headings like "### PyPSA (Strong)"
    heading_tiers = re.findall(r"^### .+?\((\w+)(?:,.*?)?\)", text, re.MULTILINE)
    assert len(heading_tiers) == 6, (
        f"Expected 6 tool headings with tiers in {criterion}, got {len(heading_tiers)}"
    )
    # Verify at least the tier labels are valid
    for tier in heading_tiers:
        assert tier in TIER_MAP, f"Unknown tier '{tier}' in {criterion} heading"


# ── 18. All tools present in all 3 pages ────────────────────────────


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


# ── 19. Build succeeds ──────────────────────────────────────────────


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
