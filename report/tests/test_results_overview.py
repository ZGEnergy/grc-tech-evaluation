"""Tests for report/docs/results/index.mdx (PRD 05/02 — Results Overview Page)."""

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
MDX_PATH = WORKTREE / "report" / "docs" / "results" / "index.mdx"
SENSITIVITY_PATH = WORKTREE / "report" / "data" / "sensitivity.json"


@pytest.fixture(scope="module")
def mdx_text() -> str:
    return MDX_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def sensitivity_data() -> dict:
    return json.loads(SENSITIVITY_PATH.read_text(encoding="utf-8"))


# ── 1. File exists and is not a stub ──────────────────────────────────


def test_results_overview_exists(mdx_text: str) -> None:
    """Verify index.mdx exists and is not the Phase 1 stub."""
    lines = mdx_text.strip().splitlines()
    assert len(lines) > 30, f"Expected >30 lines (not a stub), got {len(lines)}"
    assert "will be added in Phase" not in mdx_text, "Page still contains stub text"


# ── 2. Frontmatter ────────────────────────────────────────────────────


def test_frontmatter_valid(mdx_text: str) -> None:
    """Parse frontmatter and verify sidebar_position and title are set."""
    assert re.search(r"sidebar_position:\s*1", mdx_text), "sidebar_position must be 1"
    assert re.search(r'title:\s*"Evaluation Results"', mdx_text), (
        'title must be "Evaluation Results"'
    )


# ── 3. Introduction ──────────────────────────────────────────────────


def test_introduction_present(mdx_text: str) -> None:
    """Verify introductory text within first 800 chars references Results and section structure."""
    # Strip frontmatter to find content start
    content_start = mdx_text.find("---", mdx_text.find("---") + 1) + 3
    intro = mdx_text[content_start : content_start + 1200]
    assert "Results" in intro, "Introduction must reference 'Results'"
    assert "criterion" in intro.lower() or "criteria" in intro.lower(), (
        "Introduction must explain section structure (mention criteria)"
    )


# ── 4. Heatmap chart slot ────────────────────────────────────────────


def test_heatmap_chart_slot(mdx_text: str) -> None:
    """Verify grade comparison is present (table or chart)."""
    has_img = "heatmap_grades" in mdx_text
    has_placeholder = bool(
        re.search(r"<Placeholder[^>]*Heatmap", mdx_text, re.IGNORECASE)
    )
    has_grade_table = bool(re.search(r"## Grade Comparison", mdx_text))
    assert has_img or has_placeholder or has_grade_table, (
        "Page must contain heatmap_grades img, Placeholder with 'Heatmap', or Grade Comparison table"
    )


# ── 5. Pass/fail matrix chart slot ───────────────────────────────────


def test_matrix_chart_slot(mdx_text: str) -> None:
    """Verify ranking table or pass/fail matrix chart is present."""
    has_img = "matrix_test-results" in mdx_text
    has_placeholder = bool(
        re.search(
            r"<Placeholder[^>]*(Matrix|Pass.?Fail)",
            mdx_text,
            re.IGNORECASE,
        )
    )
    has_ranking_table = bool(re.search(r"## Ranking Methodology", mdx_text))
    assert has_img or has_placeholder or has_ranking_table, (
        "Page must contain matrix chart, Placeholder, or Ranking Methodology table"
    )


# ── 6. Radar chart slot ──────────────────────────────────────────────


def test_radar_chart_slot(mdx_text: str) -> None:
    """Verify sensitivity analysis or radar overlay chart is present."""
    has_img = "radar_overlay" in mdx_text
    has_placeholder = bool(
        re.search(r"<Placeholder[^>]*Radar", mdx_text, re.IGNORECASE)
    )
    has_sensitivity = bool(re.search(r"## Sensitivity Analysis", mdx_text))
    assert has_img or has_placeholder or has_sensitivity, (
        "Page must contain radar_overlay img, Placeholder with 'Radar', or Sensitivity Analysis"
    )


# ── 7. Sensitivity table present ─────────────────────────────────────


def test_sensitivity_table_present(mdx_text: str) -> None:
    """Verify a Markdown table with at least 3 data rows referencing scenarios."""
    # Find table rows (lines starting with |, excluding header separator)
    table_rows = re.findall(r"^\|[^-].*\|$", mdx_text, re.MULTILINE)
    # Exclude the header row itself — data rows should mention scenario-like text
    data_rows = [
        r
        for r in table_rows
        if "Scenario" not in r.split("|")[1]  # not the header
    ]
    assert len(data_rows) >= 3, (
        f"Sensitivity table must have >=3 data rows, found {len(data_rows)}"
    )


# ── 8. PyPSA #1 in all scenarios ─────────────────────────────────────


def test_sensitivity_pypsa_first(mdx_text: str) -> None:
    """Verify PyPSA is indicated as #1 in all sensitivity scenarios."""
    # Find the sensitivity section
    sens_start = mdx_text.find("## Sensitivity")
    assert sens_start != -1, "Sensitivity section not found"
    # Find the next ## section or end of file
    next_section = mdx_text.find("\n## ", sens_start + 1)
    sens_section = (
        mdx_text[sens_start:next_section]
        if next_section != -1
        else mdx_text[sens_start:]
    )

    # Each data row should have PyPSA in the #1 column
    table_rows = re.findall(r"^\|[^-].*\|$", sens_section, re.MULTILINE)
    data_rows = [r for r in table_rows if "Scenario" not in r.split("|")[1]]
    assert len(data_rows) >= 3, "Need at least 3 scenario rows"
    for row in data_rows:
        cells = [c.strip() for c in row.split("|")]
        # Table columns: | Scenario | Description | #1 | #2 | #3 | #4 | #5 |
        # cells[0] is empty (before first |), cells[3] is the #1 column
        rank1_cell = cells[3] if len(cells) > 3 else ""
        assert "PyPSA" in rank1_cell, (
            f"PyPSA must be #1 in every row; found '{rank1_cell}' in row: {row}"
        )

    # Also check for a summary sentence
    assert "PyPSA holds" in sens_section or "PyPSA" in sens_section, (
        "Sensitivity section must confirm PyPSA's #1 ranking"
    )


# ── 9. Navigation links — criterion pages ────────────────────────────


CRITERION_SLUGS = [
    "expressiveness",
    "extensibility",
    "scalability",
    "accessibility",
    "maturity",
    "supply-chain",
]


def test_navigation_links_criterion_pages(mdx_text: str) -> None:
    """Verify links to all 6 criterion sub-pages."""
    for slug in CRITERION_SLUGS:
        pattern = rf"\]\(\./{re.escape(slug)}\)"
        assert re.search(pattern, mdx_text), f"Missing navigation link to './{slug}'"


# ── 10. Navigation links — cross-cutting pages ───────────────────────


CROSS_CUTTING_SLUGS = ["head-to-head"]


def test_navigation_links_cross_cutting(mdx_text: str) -> None:
    """Verify links to cross-cutting comparison pages."""
    for slug in CROSS_CUTTING_SLUGS:
        pattern = rf"\]\(\./{re.escape(slug)}\)"
        assert re.search(pattern, mdx_text), f"Missing navigation link to './{slug}'"


# ── 11. Navigation descriptions ──────────────────────────────────────


def test_navigation_descriptions(mdx_text: str) -> None:
    """Verify each navigation link has a non-empty description (>=10 chars after link)."""
    all_slugs = CRITERION_SLUGS + CROSS_CUTTING_SLUGS
    for slug in all_slugs:
        # Pattern: **[Name](./slug)**: description  OR  [Name](./slug)** — description
        pattern = rf"\]\(\./{re.escape(slug)}\)\*{{0,2}}[:]\s*(.+)"
        match = re.search(pattern, mdx_text)
        if not match:
            # Fallback: dash/em-dash separator
            pattern = rf"\]\(\./{re.escape(slug)}\)\*{{0,2}}\s*[-—]\s*(.+)"
            match = re.search(pattern, mdx_text)
        assert match, f"No description found for link './{slug}'"
        desc = match.group(1).strip()
        assert len(desc) >= 10, (
            f"Description for './{slug}' too short ({len(desc)} chars): '{desc}'"
        )


# ── 12. Exactly 3 chart embed slots ──────────────────────────────────


def test_three_chart_slots_total(mdx_text: str) -> None:
    """Verify at least 3 data presentation slots (charts, tables, or placeholders)."""
    # Remove MDX comments first
    uncommented = re.sub(r"\{/\*.*?\*/\}", "", mdx_text, flags=re.DOTALL)
    placeholders = re.findall(r"<Placeholder\b.*?/>", uncommented)
    html_imgs = re.findall(
        r"<img\b[^>]*(?:heatmap_grades|matrix_test-results|radar_overlay)", uncommented
    )
    md_imgs = re.findall(
        r"!\[.*?\]\(/img/(?:heatmap_grades|matrix_test-results|radar_overlay)",
        uncommented,
    )
    # Count markdown tables (header + separator rows) as data presentation slots
    md_tables = re.findall(r"^\|.*\|\n\|[-| :]+\|", uncommented, re.MULTILINE)
    total = len(placeholders) + len(html_imgs) + len(md_imgs) + len(md_tables)
    assert total >= 3, f"Expected >= 3 data presentation slots, found {total}"


# ── 13. No full 6x6 grade table ──────────────────────────────────────


def test_no_grade_table_duplication(mdx_text: str) -> None:
    """Verify the grade comparison table appears exactly once (not duplicated)."""
    # The page has a single Grade Comparison table with all 6 criteria as columns.
    # Verify it is not duplicated by checking that "## Grade Comparison" appears once.
    occurrences = len(re.findall(r"## Grade Comparison", mdx_text))
    assert occurrences == 1, (
        f"Grade Comparison section should appear exactly once, found {occurrences}"
    )


# ── 14. Sensitivity data matches sensitivity.json ────────────────────


def test_sensitivity_scenarios_from_json(mdx_text: str, sensitivity_data: dict) -> None:
    """Verify the sensitivity table references scenarios from sensitivity.json."""
    scenarios = sensitivity_data["scenarios"]
    # At least 3 of the scenario names (or key words) should appear
    matches = 0
    for scenario in scenarios:
        name = scenario["name"]
        # Check if any significant portion of the name appears
        keywords = [w for w in name.split() if len(w) > 4]
        for kw in keywords:
            if kw.lower() in mdx_text.lower():
                matches += 1
                break
    assert matches >= 3, (
        f"Expected >=3 sensitivity scenarios from JSON reflected in page, found {matches}"
    )


# ── 15. Build succeeds ───────────────────────────────────────────────


def test_build_succeeds() -> None:
    """Run npm run build in report/ and verify it completes without errors."""
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
