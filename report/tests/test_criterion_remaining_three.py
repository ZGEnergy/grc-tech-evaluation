"""Tests for remaining three criterion pages: Accessibility, Maturity, Supply Chain (PRD 05/04)."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

WORKTREE = Path(
    os.environ.get("WORKTREE_ROOT", Path(__file__).resolve().parent.parent.parent)
)
RESULTS_DIR = WORKTREE / "report" / "docs" / "results"

TOOL_NAMES = [
    "PyPSA",
    "PowerModels",
    "pandapower",
    "GridCal",
    "PowerSimulations",
    "MATPOWER",
]


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def accessibility_text() -> str:
    return (RESULTS_DIR / "accessibility.mdx").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def maturity_text() -> str:
    return (RESULTS_DIR / "maturity.mdx").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def supply_chain_text() -> str:
    return (RESULTS_DIR / "supply-chain.mdx").read_text(encoding="utf-8")


# ── 1. Accessibility: page exists and is not a stub ─────────────────────


def test_accessibility_page_exists(accessibility_text: str) -> None:
    assert len(accessibility_text) > 1000, (
        f"Accessibility page too short ({len(accessibility_text)} chars); likely still a stub"
    )


# ── 2. Accessibility: six tool sections ─────────────────────────────────


def test_accessibility_six_tool_sections(accessibility_text: str) -> None:
    details = re.findall(
        r"<details\b[^>]*className=[\"']eval-details[\"']", accessibility_text
    )
    assert len(details) == 6, f"Expected 6 eval-details sections, got {len(details)}"


# ── 3. Accessibility: Suite D test references ───────────────────────────


def test_accessibility_suite_d_tests(accessibility_text: str) -> None:
    d_tests = re.findall(r"D-\d", accessibility_text)
    assert len(d_tests) >= 1, (
        "Accessibility page must reference at least one Suite D test ID"
    )


# ── 4. Accessibility: all tools present ─────────────────────────────────


def test_accessibility_all_tools_present(accessibility_text: str) -> None:
    for name in TOOL_NAMES:
        assert name in accessibility_text, (
            f"Tool '{name}' not found in Accessibility page"
        )


# ── 5. Maturity: page exists and is not a stub ──────────────────────────


def test_maturity_page_exists(maturity_text: str) -> None:
    assert len(maturity_text) > 1000, (
        f"Maturity page too short ({len(maturity_text)} chars); likely still a stub"
    )


# ── 6. Maturity: six tool sections ──────────────────────────────────────


def test_maturity_six_tool_sections(maturity_text: str) -> None:
    details = re.findall(
        r"<details\b[^>]*className=[\"']eval-details[\"']", maturity_text
    )
    assert len(details) == 6, f"Expected 6 eval-details sections, got {len(details)}"


# ── 7. Maturity: probe-025 reference ────────────────────────────────────


def test_maturity_probe_025_reference(maturity_text: str) -> None:
    # Find the PowerSimulations detail section and check for probe-025 or coverage
    # The section is inside a <details> card with PowerSimulations in the summary
    psi_start = maturity_text.find("PowerSimulations")
    assert psi_start >= 0, "PowerSimulations not found in Maturity page"
    # Search the rest of the page from this point
    psi_section = maturity_text[psi_start:]
    has_probe = "probe-025" in psi_section
    has_coverage = "coverage" in psi_section.lower()
    assert has_probe or has_coverage, (
        "Maturity page must reference probe-025 or coverage for PowerSimulations"
    )


# ── 8. Maturity: theme T13 reference ───────────────────────────────────


def test_maturity_sustainability_risk_reference(maturity_text: str) -> None:
    lower = maturity_text.lower()
    has_bus_factor = "bus factor" in lower
    has_sustainability = "sustainability" in lower
    has_contributor = "contributor" in lower
    assert has_bus_factor or has_sustainability or has_contributor, (
        "Maturity page must reference bus factor, sustainability, or contributor risk"
    )


# ── 9. Maturity: Suite E test references ────────────────────────────────


def test_maturity_suite_e_tests(maturity_text: str) -> None:
    e_tests = re.findall(r"E-\d", maturity_text)
    assert len(e_tests) >= 1, (
        "Maturity page must reference at least one Suite E test ID"
    )


# ── 10. Supply Chain: page exists and is not a stub ─────────────────────


def test_supply_chain_page_exists(supply_chain_text: str) -> None:
    assert len(supply_chain_text) > 800, (
        f"Supply Chain page too short ({len(supply_chain_text)} chars); likely still a stub"
    )


# ── 11. Supply Chain: six tool sections ─────────────────────────────────


def test_supply_chain_six_tool_sections(supply_chain_text: str) -> None:
    details = re.findall(
        r"<details\b[^>]*className=[\"']eval-details[\"']", supply_chain_text
    )
    assert len(details) == 6, f"Expected 6 eval-details sections, got {len(details)}"


# ── 12. Supply Chain: all tools passed ──────────────────────────────────


def test_supply_chain_all_pass(supply_chain_text: str) -> None:
    lower = supply_chain_text.lower()
    has_all_passed = (
        "all 6 tools passed" in lower
        or "all six tools passed" in lower
        or "all passed" in lower
    )
    assert has_all_passed, "Supply Chain page must indicate all tools passed the gate"


# ── 13. Supply Chain: license table ─────────────────────────────────────


def test_supply_chain_license_table(supply_chain_text: str) -> None:
    # Check for a table header containing "License"
    assert re.search(r"\|\s*License\s*\|", supply_chain_text), (
        "Supply Chain page must contain a table with 'License' column"
    )
    assert "MPL-2.0" in supply_chain_text, "License table must mention MPL-2.0"
    assert "MIT" in supply_chain_text, "License table must mention MIT"


# ── 14. Supply Chain: MPL/copyleft note ─────────────────────────────────


def test_supply_chain_mpl_note(supply_chain_text: str) -> None:
    lower = supply_chain_text.lower()
    has_mpl = "mpl" in lower
    has_mozilla = "mozilla" in lower
    has_copyleft = "copyleft" in lower
    assert has_mpl or has_mozilla or has_copyleft, (
        "Supply Chain page must reference MPL, Mozilla, or copyleft in GridCal context"
    )
