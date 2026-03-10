"""Tests for report/docs/tools-evaluated.mdx (PRD 03/03)."""

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
MDX_PATH = WORKTREE / "report" / "docs" / "tools-evaluated.mdx"
GRADES_PATH = WORKTREE / "report" / "data" / "grades.json"


@pytest.fixture(scope="module")
def mdx_text() -> str:
    return MDX_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def grades_data() -> dict:
    return json.loads(GRADES_PATH.read_text(encoding="utf-8"))


# ── 1. File exists and is not a stub ──────────────────────────────────


def test_tools_evaluated_mdx_exists(mdx_text: str) -> None:
    lines = mdx_text.strip().splitlines()
    assert len(lines) > 100, f"Expected >100 lines, got {len(lines)}"


# ── 2-3. Frontmatter ─────────────────────────────────────────────────


def test_frontmatter_sidebar_position(mdx_text: str) -> None:
    assert re.search(r"sidebar_position:\s*4", mdx_text), "sidebar_position must be 4"


def test_frontmatter_title(mdx_text: str) -> None:
    assert re.search(r'title:\s*"Tools Evaluated"', mdx_text), (
        'title must be "Tools Evaluated"'
    )


# ── 4-7. Card structure ──────────────────────────────────────────────


def test_six_tool_cards_present(mdx_text: str) -> None:
    details = re.findall(r"<details\b", mdx_text)
    assert len(details) == 6, f"Expected 6 <details> elements, got {len(details)}"


TOOL_NAMES = [
    "PyPSA",
    "PowerModels",
    "PowerSimulations",
    "pandapower",
    "GridCal",
    "MATPOWER",
]


def test_all_tool_names_present(mdx_text: str) -> None:
    for name in TOOL_NAMES:
        assert name in mdx_text, f"Tool name '{name}' not found"


def test_pypsa_card_open_by_default(mdx_text: str) -> None:
    # Find the first <details ...> tag and verify it has 'open'
    first_details = re.search(r"<details\b[^>]*>", mdx_text)
    assert first_details, "No <details> found"
    assert "open" in first_details.group(), "First <details> (PyPSA) must have 'open'"


def test_other_cards_collapsed_by_default(mdx_text: str) -> None:
    details_tags = list(re.finditer(r"<details\b[^>]*>", mdx_text))
    assert len(details_tags) >= 6
    # Cards 2-6 (index 1-5) should NOT have 'open'
    for tag in details_tags[1:]:
        assert "open" not in tag.group(), (
            f"Non-PyPSA card should not have 'open': {tag.group()}"
        )


# ── 8. Rank ordering ─────────────────────────────────────────────────


def test_rank_ordering(mdx_text: str) -> None:
    ordered = [
        "PyPSA",
        "PowerModels",
        "PowerSimulations",
        "pandapower",
        "GridCal",
        "MATPOWER",
    ]
    # Find positions of each tool's <summary> heading, not first mention
    positions = []
    for name in ordered:
        # Look for the tool name inside a ### heading (within <summary>)
        pattern = rf"###\s+.*{re.escape(name)}"
        match = re.search(pattern, mdx_text)
        assert match, f"Tool '{name}' heading not found in MDX"
        positions.append(match.start())
    for i in range(len(positions) - 1):
        assert positions[i] < positions[i + 1], (
            f"'{ordered[i]}' (pos {positions[i]}) must appear before "
            f"'{ordered[i + 1]}' (pos {positions[i + 1]})"
        )


# ── 9. Metadata tables ───────────────────────────────────────────────


def test_each_card_has_metadata_table(mdx_text: str) -> None:
    # Split by <details to isolate cards
    cards = re.split(r"<details\b", mdx_text)[1:]  # skip preamble
    assert len(cards) == 6
    required_fields = ["Language", "License", "Maintainer"]
    for i, card in enumerate(cards):
        for field in required_fields:
            assert field in card, f"Card {i + 1} missing metadata field '{field}'"


# ── 10. Grade tables ─────────────────────────────────────────────────

CRITERIA = [
    "Expressiveness",
    "Extensibility",
    "Scalability",
    "Accessibility",
    "Maturity",
    "Supply Chain",
]


def test_each_card_has_grade_table(mdx_text: str) -> None:
    cards = re.split(r"<details\b", mdx_text)[1:]
    assert len(cards) == 6
    for i, card in enumerate(cards):
        for criterion in CRITERIA:
            assert criterion in card, f"Card {i + 1} missing criterion '{criterion}'"


# ── 11. Grade values match grades.json ───────────────────────────────


def test_grade_values_match_grades_json(mdx_text: str, grades_data: dict) -> None:
    # Spot-check at least 6 grades from the JSON
    spot_checks = [
        ("pypsa", "expressiveness", "B+"),
        ("pypsa", "supply_chain", "A"),
        ("pandapower", "expressiveness", "C+"),
        ("powermodels", "extensibility", "A-"),
        ("gridcal", "maturity", "B-"),
        ("powersimulations", "accessibility", "C+"),
    ]
    for tool_id, criterion, expected_letter in spot_checks:
        # Verify the grade exists in grades.json
        matching = [
            g
            for g in grades_data["grades"]
            if g["tool"] == tool_id and g["criterion"] == criterion
        ]
        assert len(matching) == 1, f"Grade not found in JSON: {tool_id}/{criterion}"
        assert matching[0]["letter"] == expected_letter

        # Verify the grade letter appears in the MDX with CSS class
        css_class = "grade-" + expected_letter.lower().replace("+", "-plus").replace(
            "-", "-minus"
        )
        # Handle the special case where "B-" -> "grade-b-minus" but "A-" -> "grade-a-minus"
        # Re-derive properly
        letter = expected_letter
        base = letter[0].lower()
        if letter.endswith("+"):
            css_class = f"grade-{base}-plus"
        elif letter.endswith("-"):
            css_class = f"grade-{base}-minus"
        else:
            css_class = f"grade-{base}"

        assert css_class in mdx_text, (
            f"CSS class '{css_class}' not found for {tool_id}/{criterion}"
        )


# ── 12. Rationale text ───────────────────────────────────────────────


def test_each_card_has_rationale_text(mdx_text: str) -> None:
    """Each criterion row should have non-empty rationale (>=20 chars)."""
    cards = re.split(r"<details\b", mdx_text)[1:]
    assert len(cards) == 6
    for i, card in enumerate(cards):
        # Find grade table rows: | Criterion | <span...>GRADE</span> | summary |
        rows = re.findall(
            r"\|\s*(?:Expressiveness|Extensibility|Scalability|Accessibility"
            r"|Maturity|Supply Chain)\s*\|[^|]+\|([^|]+)\|",
            card,
        )
        assert len(rows) >= 6, (
            f"Card {i + 1}: expected >=6 criterion rows, found {len(rows)}"
        )
        for row_text in rows:
            stripped = row_text.strip()
            assert len(stripped) >= 20, (
                f"Card {i + 1}: rationale too short ({len(stripped)} chars): "
                f"'{stripped[:40]}...'"
            )


# ── 13. MATPOWER reference indicator ─────────────────────────────────


def test_matpower_reference_only_indicator(mdx_text: str) -> None:
    # The MATPOWER card should contain "reference" or "benchmark"
    matpower_section = mdx_text[mdx_text.find("MATPOWER") :]
    assert matpower_section, "MATPOWER section not found"
    lower = matpower_section.lower()
    assert "reference" in lower or "benchmark" in lower, (
        "MATPOWER card must indicate 'reference' or 'benchmark'"
    )


# ── 14. MATPOWER exclusion footnote ──────────────────────────────────


def test_matpower_exclusion_footnote(mdx_text: str) -> None:
    lower = mdx_text.lower()
    assert "matlab" in lower, "Page must mention 'MATLAB'"
    assert "classified" in lower or "authorization" in lower, (
        "Page must mention 'classified' or 'authorization'"
    )


# ── 15. Radar placeholder slots ──────────────────────────────────────


def test_radar_placeholder_slots(mdx_text: str) -> None:
    assert "Tool Comparison Radar" in mdx_text, (
        "Missing 'Tool Comparison Radar' placeholder"
    )
    # At least 1 per-tool radar
    tool_radars = re.findall(r'title="[^"]*Radar"', mdx_text)
    # Should have comparison + at least 1 per-tool = 7 total minimum
    assert len(tool_radars) >= 7, (
        f"Expected >=7 radar placeholders, found {len(tool_radars)}"
    )


# ── 16-17. Uniform presentation ──────────────────────────────────────


def _get_card_text(mdx_text: str, tool_name: str) -> str:
    """Extract the text for a specific tool's card."""
    cards = re.split(r"<details\b", mdx_text)[1:]
    for card in cards:
        if tool_name in card:
            return card
    raise AssertionError(f"Card for '{tool_name}' not found")


def _has_metadata_and_grade_table(card: str) -> tuple[bool, bool]:
    """Check if a card has both metadata table and grade table."""
    has_metadata = all(field in card for field in ["Language", "License", "Maintainer"])
    has_grade = all(criterion in card for criterion in CRITERIA)
    return has_metadata, has_grade


def test_gridcal_uniform_presentation(mdx_text: str) -> None:
    pypsa_card = _get_card_text(mdx_text, "PyPSA")
    gridcal_card = _get_card_text(mdx_text, "GridCal")

    pypsa_meta, pypsa_grade = _has_metadata_and_grade_table(pypsa_card)
    gc_meta, gc_grade = _has_metadata_and_grade_table(gridcal_card)

    assert pypsa_meta and pypsa_grade, "PyPSA reference card missing tables"
    assert gc_meta, "GridCal card missing metadata table"
    assert gc_grade, "GridCal card missing grade table"
    assert "reconstructed" not in gridcal_card.lower(), (
        "GridCal card should not have a 'reconstructed' marker"
    )


def test_powersimulations_uniform_presentation(mdx_text: str) -> None:
    pypsa_card = _get_card_text(mdx_text, "PyPSA")
    psi_card = _get_card_text(mdx_text, "PowerSimulations")

    pypsa_meta, pypsa_grade = _has_metadata_and_grade_table(pypsa_card)
    psi_meta, psi_grade = _has_metadata_and_grade_table(psi_card)

    assert pypsa_meta and pypsa_grade, "PyPSA reference card missing tables"
    assert psi_meta, "PowerSimulations card missing metadata table"
    assert psi_grade, "PowerSimulations card missing grade table"
    assert "reconstructed" not in psi_card.lower(), (
        "PowerSimulations card should not have a 'reconstructed' marker"
    )


# ── 18. Build succeeds ───────────────────────────────────────────────


def test_build_succeeds() -> None:
    # The build test requires the full Docusaurus project with node_modules.
    # Detect whether we are inside the devcontainer (/.dockerenv exists) or on
    # the host. When on the host, use dc-exec; when inside, run npm directly.
    inside_container = Path("/.dockerenv").exists()

    if inside_container:
        # Running inside the container -- use npm directly
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
        # Running on the host -- use dc-exec to reach the container
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
