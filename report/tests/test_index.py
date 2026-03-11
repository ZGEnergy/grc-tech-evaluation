"""Tests for report/docs/index.mdx (PRD 03/01 — Home Page Content)."""

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
MDX_PATH = WORKTREE / "report" / "docs" / "index.mdx"
RISK_JSON_PATH = WORKTREE / "report" / "data" / "risk-register.json"

STUB_MARKER = "Content will be added in Phase 3"


@pytest.fixture(scope="module")
def mdx_text() -> str:
    return MDX_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def risk_data() -> dict:
    return json.loads(RISK_JSON_PATH.read_text(encoding="utf-8"))


# ── 1. File exists and is not a stub ────────────────────────────────


def test_index_mdx_exists(mdx_text: str) -> None:
    assert len(mdx_text.strip().splitlines()) > 20, (
        "index.mdx appears to still be a stub"
    )
    assert STUB_MARKER not in mdx_text, (
        "index.mdx still contains the Phase 1 stub marker"
    )


# ── 2. Frontmatter sidebar_position and slug ────────────────────────


def test_frontmatter_sidebar_position(mdx_text: str) -> None:
    assert re.search(r"sidebar_position:\s*1\b", mdx_text), "sidebar_position must be 1"
    assert re.search(r'slug:\s*["\']?/["\']?\s*$', mdx_text, re.MULTILINE), (
        'slug must be "/"'
    )


# ── 3. Frontmatter title ────────────────────────────────────────────


def test_frontmatter_title(mdx_text: str) -> None:
    match = re.search(r"title:\s*\"([^\"]+)\"", mdx_text)
    assert match, "Frontmatter must contain a title field"
    assert len(match.group(1).strip()) > 0, "Title must be non-empty"


# ── 4. Executive summary — PyPSA within first 500 chars ─────────────


def test_executive_summary_present(mdx_text: str) -> None:
    # Strip frontmatter to find content start
    body = re.sub(r"^---.*?---", "", mdx_text, count=1, flags=re.DOTALL).strip()
    first_500 = body[:500]
    assert "PyPSA" in first_500, (
        "PyPSA must appear within the first 500 characters of page content"
    )


# ── 5. Recommendation keyword ───────────────────────────────────────


def test_recommendation_keyword_present(mdx_text: str) -> None:
    assert re.search(r"recommend", mdx_text, re.IGNORECASE), (
        "Page must contain 'recommend' in some form"
    )


# ── 6. Heatmap placeholder or image ─────────────────────────────────


def test_heatmap_placeholder_or_image(mdx_text: str) -> None:
    has_placeholder = bool(
        re.search(r"<Placeholder[^>]*title\s*=\s*\"[^\"]*Heatmap[^\"]*\"", mdx_text)
    )
    has_image = bool(re.search(r"<img[^>]*heatmap_grades", mdx_text))
    assert has_placeholder or has_image, (
        "Page must contain a Heatmap Placeholder or an <img> referencing heatmap_grades"
    )


# ── 7. Why PyPSA section with 3 points ──────────────────────────────


def test_why_pypsa_section_exists(mdx_text: str) -> None:
    assert re.search(r"(?i)why\s+pypsa", mdx_text), (
        "Page must contain a 'Why PyPSA' section"
    )
    # Find at least 3 numbered list items (1. 2. 3.) or bullet points after the heading
    why_match = re.search(r"(?i)(#+\s*why\s+pypsa.*)", mdx_text, re.DOTALL)
    assert why_match, "Could not locate 'Why PyPSA' heading"
    section_text = why_match.group(1)
    # Count numbered items like "1." "2." "3." at start of line
    numbered = re.findall(r"^\d+\.", section_text, re.MULTILINE)
    assert len(numbered) >= 3, (
        f"Expected >=3 numbered rationale points, found {len(numbered)}"
    )


# ── 8. Risk Register collapsible ────────────────────────────────────


def test_risk_register_collapsible(mdx_text: str) -> None:
    assert re.search(r"<details\b", mdx_text), "Page must contain a <details> element"
    assert re.search(r"<summary>[^<]*Risk Register[^<]*</summary>", mdx_text), (
        "Page must have a <summary> containing 'Risk Register'"
    )


# ── 9. Risk Register has 4 items ────────────────────────────────────


def test_risk_register_four_items(mdx_text: str) -> None:
    # Extract the risk register section (between Risk Register summary and next </details>)
    risk_section_match = re.search(
        r"<summary>[^<]*Risk Register[^<]*</summary>(.*?)</details>",
        mdx_text,
        re.DOTALL,
    )
    assert risk_section_match, "Could not find Risk Register section"
    section = risk_section_match.group(1)

    # Count the 4 known risk keywords
    keywords_found = 0
    for keyword in ["SCUC", "stochastic", "PWL", "Linopy"]:
        if re.search(keyword, section, re.IGNORECASE):
            keywords_found += 1
    assert keywords_found == 4, (
        f"Expected 4 distinct risk items (SCUC, stochastic, PWL, Linopy), found {keywords_found}"
    )


# ── 10. Risk severity labels ────────────────────────────────────────


def test_risk_severity_labels(mdx_text: str) -> None:
    risk_section_match = re.search(
        r"<summary>[^<]*Risk Register[^<]*</summary>(.*?)</details>",
        mdx_text,
        re.DOTALL,
    )
    assert risk_section_match, "Could not find Risk Register section"
    section = risk_section_match.group(1)

    high_count = len(re.findall(r"\bHIGH\b", section))
    med_count = len(re.findall(r"\bMED\b", section))
    assert high_count >= 2, f"Expected >=2 HIGH severity items, found {high_count}"
    assert med_count >= 2, f"Expected >=2 MED severity items, found {med_count}"


# ── 11. Phase 2 roadmap collapsible ─────────────────────────────────


def test_phase2_roadmap_collapsible(mdx_text: str) -> None:
    pattern = r"<summary>[^<]*(?:Phase 2|Development|Roadmap)[^<]*</summary>"
    assert re.search(pattern, mdx_text), (
        "Page must have a collapsible section for Phase 2 / Development / Roadmap"
    )


# ── 12. Phase 2 roadmap three tables ────────────────────────────────


def test_phase2_roadmap_three_tables(mdx_text: str) -> None:
    # Find the Phase 2 roadmap section
    roadmap_match = re.search(
        r"<summary>[^<]*(?:Phase 2|Development)[^<]*</summary>(.*?)</details>",
        mdx_text,
        re.DOTALL,
    )
    assert roadmap_match, "Could not find Phase 2 roadmap section"
    section = roadmap_match.group(1)

    # Count markdown table headers (lines that start with |---|)
    table_separators = re.findall(r"^\|[-| :]+\|$", section, re.MULTILINE)
    assert len(table_separators) >= 3, (
        f"Expected >=3 markdown tables in Phase 2 roadmap, found {len(table_separators)}"
    )


# ── 13. Sensitivity link to results ─────────────────────────────────


def test_sensitivity_link_to_results(mdx_text: str) -> None:
    # Look for a markdown link pointing to the results page
    assert re.search(r"\[.*?\]\(.*?results.*?\)", mdx_text), (
        "Page must contain a markdown link to the Results page"
    )


# ── 14. Radar placeholder slot ──────────────────────────────────────


def test_radar_placeholder_slot(mdx_text: str) -> None:
    assert re.search(r"<Placeholder[^>]*title\s*=\s*\"[^\"]*Radar[^\"]*\"", mdx_text), (
        "Page must contain a Placeholder with 'Radar' in the title"
    )


# ── 15. Runner-up mentioned ─────────────────────────────────────────


def test_runner_up_mentioned(mdx_text: str) -> None:
    assert "PowerModels" in mdx_text, "Page must mention PowerModels as the runner-up"


# ── 16. Build succeeds ──────────────────────────────────────────────


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
