"""Tests for report/docs/results/head-to-head.mdx (PRD 05/05)."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

WORKTREE = Path(
    os.environ.get("WORKTREE_ROOT", Path(__file__).resolve().parent.parent.parent)
)
MDX_PATH = WORKTREE / "report" / "docs" / "results" / "head-to-head.mdx"


@pytest.fixture(scope="module")
def mdx_text() -> str:
    return MDX_PATH.read_text(encoding="utf-8")


# ── 1. File exists and is not a stub ──────────────────────────────────


def test_head_to_head_page_exists(mdx_text: str) -> None:
    """Verify head-to-head.mdx exists and is not the Phase 1 stub."""
    lines = mdx_text.strip().splitlines()
    assert len(lines) > 20, f"Expected >20 lines (not a stub), got {len(lines)}"
    assert "Phase 5" not in mdx_text, "Page still contains Phase 1 stub text"


# ── 2. Frontmatter ───────────────────────────────────────────────────


def test_frontmatter_valid(mdx_text: str) -> None:
    """Parse frontmatter and verify sidebar_position and title."""
    assert re.search(r"sidebar_position:\s*8", mdx_text), "sidebar_position must be 8"
    assert re.search(r'title:\s*"Head-to-Head Comparison"', mdx_text), (
        'title must be "Head-to-Head Comparison"'
    )


# ── 3. Introduction evidence caveat ──────────────────────────────────


def test_introduction_describes_ratings(mdx_text: str) -> None:
    """Verify introduction describes the capability rating system."""
    # Extract text before the first ## section after introduction
    intro_end = mdx_text.find("## ", mdx_text.find("# Head-to-Head") + 1)
    assert intro_end > 0, "Second heading not found"
    intro = mdx_text[:intro_end].lower()
    assert "native" in intro, "Introduction must describe 'Native' rating"
    assert "extension" in intro, "Introduction must describe 'Extension' rating"
    assert "gap" in intro, "Introduction must describe 'Gap' rating"


# ── 4. Summary table present ─────────────────────────────────────────


def test_summary_table_present(mdx_text: str) -> None:
    """Verify page contains a summary table with at least 6 data rows."""
    # Find the summary table section
    table_start = mdx_text.find("## Summary Table")
    assert table_start > 0, "Summary Table section not found"
    # Extract until next ## section
    next_section = mdx_text.find("## ", table_start + 1)
    table_section = mdx_text[table_start:next_section]
    # Count table data rows (lines starting with |, excluding header and separator)
    table_lines = [
        line
        for line in table_section.strip().splitlines()
        if line.strip().startswith("|") and "---" not in line
    ]
    # Subtract 1 for header row
    data_rows = len(table_lines) - 1
    assert data_rows >= 6, f"Expected >=6 data rows in summary table, got {data_rows}"


# ── 5. Summary table references all 6 tools ──────────────────────────


def test_summary_table_six_tools(mdx_text: str) -> None:
    """Verify summary table headers reference all 6 tools."""
    table_start = mdx_text.find("## Summary Table")
    next_section = mdx_text.find("## ", table_start + 1)
    table_section = mdx_text[table_start:next_section]
    header_line = [
        line
        for line in table_section.strip().splitlines()
        if line.strip().startswith("|") and "Capability" in line
    ]
    assert len(header_line) == 1, "Expected exactly one header row with 'Capability'"
    header = header_line[0]
    # Check for all 6 tools (PowerSim. is abbreviated form of PowerSimulations)
    tool_patterns = [
        "PyPSA",
        "PowerModels",
        "PowerSim",
        "pandapower",
        "GridCal",
        "MATPOWER",
    ]
    for tool in tool_patterns:
        assert tool in header, f"Tool '{tool}' not found in summary table header"


# ── 6. Six capability sections ───────────────────────────────────────


def test_six_capability_sections(mdx_text: str) -> None:
    """Verify page contains 6 <details> elements with eval-details class."""
    details = re.findall(r'<details\s+className="eval-details"', mdx_text)
    assert len(details) == 6, f"Expected 6 eval-details sections, got {len(details)}"


# ── 7. Capability: SCOPF present ─────────────────────────────────────


def test_capability_scopf_present(mdx_text: str) -> None:
    """Verify one collapsible section's summary contains 'SCOPF'."""
    summaries = re.findall(r"<summary>(.*?)</summary>", mdx_text, re.DOTALL)
    assert any("SCOPF" in s for s in summaries), "No <summary> contains 'SCOPF'"


# ── 8. Capability: Custom Constraints present ────────────────────────


def test_capability_custom_constraints_present(mdx_text: str) -> None:
    """Verify one collapsible section contains Custom Constraints."""
    summaries = re.findall(r"<summary>(.*?)</summary>", mdx_text, re.DOTALL)
    assert any(
        "Custom Constraint" in s or "custom constraint" in s for s in summaries
    ), "No <summary> contains 'Custom Constraints'"


# ── 9. Capability: UC/ED present ─────────────────────────────────────


def test_capability_uc_ed_present(mdx_text: str) -> None:
    """Verify one collapsible section contains UC/ED."""
    summaries = re.findall(r"<summary>(.*?)</summary>", mdx_text, re.DOTALL)
    assert any(
        "UC" in s or "Unit Commitment" in s or "ED" in s or "Economic Dispatch" in s
        for s in summaries
    ), "No <summary> contains UC/ED reference"


# ── 10. Native/Extension/Gap ratings present ─────────────────────────


def test_native_extension_gap_ratings(mdx_text: str) -> None:
    """Verify page contains at least one instance each of Native, Extension, Gap."""
    assert "Native" in mdx_text, "No 'Native' rating found"
    assert "Extension" in mdx_text, "No 'Extension' rating found"
    assert "Gap" in mdx_text, "No 'Gap' rating found"


# ── 11. Insufficient Data cells ──────────────────────────────────────


def test_workaround_and_gap_cells(mdx_text: str) -> None:
    """Verify the page contains both Workaround and Gap ratings."""
    has_workaround = "Workaround" in mdx_text
    has_gap = "Gap" in mdx_text
    assert has_workaround, "Expected at least one 'Workaround' rating"
    assert has_gap, "Expected at least one 'Gap' rating"


# ── 12. Phase 2 relevance explanations ───────────────────────────────


def test_phase2_relevance_explanations(mdx_text: str) -> None:
    """Verify at least 3 capability sections reference Phase 2."""
    # Split by <details to isolate capability sections
    sections = re.split(r"<details\b", mdx_text)[1:]
    phase2_count = sum(1 for s in sections if "Phase 2" in s)
    assert phase2_count >= 3, (
        f"Expected >=3 sections referencing Phase 2, found {phase2_count}"
    )


# ── 13. Evidence test IDs ────────────────────────────────────────────


def test_evidence_test_ids(mdx_text: str) -> None:
    """Verify page references at least 3 specific test IDs."""
    test_ids = set(re.findall(r"\b([ABCGP]\d?-\d+)\b", mdx_text))
    assert len(test_ids) >= 3, (
        f"Expected >=3 distinct test IDs, found {len(test_ids)}: {test_ids}"
    )


# ── 14. Each detail section has all 6 tools ──────────────────────────


def test_each_detail_has_six_tools(mdx_text: str) -> None:
    """Verify each capability detail section mentions all 6 tools."""
    sections = re.split(r"<details\b", mdx_text)[1:]
    tool_names = [
        "PyPSA",
        "PowerModels",
        "PowerSimulations",
        "pandapower",
        "GridCal",
        "MATPOWER",
    ]
    for i, section in enumerate(sections):
        for tool in tool_names:
            assert tool in section, f"Capability section {i + 1} missing tool '{tool}'"


# ── 15. Build succeeds ───────────────────────────────────────────────


def test_build_succeeds() -> None:
    """Run npm run build and verify it completes without errors."""
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
