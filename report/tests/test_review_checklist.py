"""Tests for PRD 06/06 — Content Review Checklist & GitHub Issue Template."""

from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CHECKLIST_PATH = REPO_ROOT / "report" / "REVIEW_CHECKLIST.md"
ISSUE_TEMPLATE_PATH = REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "content-review.md"

EXPECTED_PAGES: list[str] = [
    "Home",
    "Methodology",
    "Use Cases & Criteria",
    "Tools Evaluated",
    "Results Overview",
    "Expressiveness",
    "Extensibility",
    "Scalability",
    "Accessibility",
    "Maturity",
    "Supply Chain",
    "Grid Primer",
    "Grid Primer — Transmission",
    "Grid Primer — Modeling",
]

CHECKBOXES_PER_PAGE = 7
SUMMARY_CHECKBOXES = 4
TOTAL_CHECKBOXES = len(EXPECTED_PAGES) * CHECKBOXES_PER_PAGE + SUMMARY_CHECKBOXES  # 102


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _count_checkboxes(text: str) -> int:
    return len(re.findall(r"^- \[ \] ", text, re.MULTILINE))


def _extract_summary_section(text: str) -> str:
    """Return the text between the Summary Sign-Off heading and the next '---' or '##'."""
    m = re.search(
        r"## Summary Sign-Off\s*\n(.*?)(?=\n---|\n## )",
        text,
        re.DOTALL,
    )
    assert m, "Summary Sign-Off section not found"
    return m.group(1)


def _extract_page_section(text: str, page_name: str) -> str:
    """Return the text of a single page review section (### heading to next ### or ---)."""
    # The heading is like: ### Home (`/`) or ### Grid Primer — Transmission (...)
    escaped = re.escape(page_name)
    pattern = rf"### {escaped}\s*\(.*?\)\s*\n(.*?)(?=\n###|\n---|\Z)"
    m = re.search(pattern, text, re.DOTALL)
    assert m, f"Page section for '{page_name}' not found"
    return m.group(1)


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Parse YAML frontmatter delimited by --- lines."""
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    assert m, "YAML frontmatter not found"
    result: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestChecklist:
    """Tests for report/REVIEW_CHECKLIST.md."""

    def test_checklist_file_exists(self) -> None:
        """T-D6.06-01: Verify that report/REVIEW_CHECKLIST.md exists."""
        assert CHECKLIST_PATH.is_file(), f"{CHECKLIST_PATH} does not exist"

    def test_checklist_has_all_14_pages(self) -> None:
        """T-D6.06-03: Parse the checklist and verify all 14 page names appear."""
        text = _read(CHECKLIST_PATH)
        for page in EXPECTED_PAGES:
            assert f"### {page}" in text, f"Missing page heading: {page}"

    def test_checklist_seven_checkboxes_per_page(self) -> None:
        """T-D6.06-04: Each page section has exactly 7 checkboxes."""
        text = _read(CHECKLIST_PATH)
        for page in EXPECTED_PAGES:
            section = _extract_page_section(text, page)
            count = _count_checkboxes(section)
            assert count == CHECKBOXES_PER_PAGE, (
                f"Page '{page}' has {count} checkboxes, expected {CHECKBOXES_PER_PAGE}"
            )

    def test_checklist_summary_section_exists(self) -> None:
        """T-D6.06-05: Verify the checklist contains a summary/sign-off section."""
        text = _read(CHECKLIST_PATH)
        assert "## Summary Sign-Off" in text

    def test_checklist_summary_has_four_checkboxes(self) -> None:
        """T-D6.06-06: Verify the summary section contains exactly 4 checkboxes."""
        text = _read(CHECKLIST_PATH)
        summary = _extract_summary_section(text)
        count = _count_checkboxes(summary)
        assert count == SUMMARY_CHECKBOXES, (
            f"Summary has {count} checkboxes, expected {SUMMARY_CHECKBOXES}"
        )

    def test_checklist_total_checkboxes(self) -> None:
        """T-D6.06-07: Total checkbox count is 102 (14*7 + 4)."""
        text = _read(CHECKLIST_PATH)
        count = _count_checkboxes(text)
        assert count == TOTAL_CHECKBOXES, (
            f"Total checkboxes: {count}, expected {TOTAL_CHECKBOXES}"
        )

    def test_checklist_mentions_make_validate(self) -> None:
        """T-D6.06-08: Summary references `make validate`."""
        text = _read(CHECKLIST_PATH)
        summary = _extract_summary_section(text)
        assert "make validate" in summary

    def test_checklist_mentions_smoke_test(self) -> None:
        """T-D6.06-09: Summary references the smoke test (`make smoke`)."""
        text = _read(CHECKLIST_PATH)
        summary = _extract_summary_section(text)
        assert "make smoke" in summary

    def test_checklist_mentions_responsive(self) -> None:
        """T-D6.06-10: Summary includes a responsive/mobile viewport check."""
        text = _read(CHECKLIST_PATH)
        summary = _extract_summary_section(text)
        assert (
            "mobile" in summary.lower()
            or "responsive" in summary.lower()
            or "768" in summary
        )

    def test_checklist_reviewer_signoff_section(self) -> None:
        """T-D6.06-14: Checklist has reviewer sign-off with name and date fields."""
        text = _read(CHECKLIST_PATH)
        assert "## Reviewer Sign-Off" in text
        assert "Reviewer name" in text
        assert "Date" in text


class TestIssueTemplate:
    """Tests for .github/ISSUE_TEMPLATE/content-review.md."""

    def test_issue_template_exists(self) -> None:
        """T-D6.06-02: Verify issue template exists."""
        assert ISSUE_TEMPLATE_PATH.is_file(), f"{ISSUE_TEMPLATE_PATH} does not exist"

    def test_issue_template_has_frontmatter(self) -> None:
        """T-D6.06-11: Issue template has YAML frontmatter with name, about, title."""
        text = _read(ISSUE_TEMPLATE_PATH)
        fm = _parse_frontmatter(text)
        assert "name" in fm, "Frontmatter missing 'name'"
        assert "about" in fm, "Frontmatter missing 'about'"
        assert "title" in fm, "Frontmatter missing 'title'"

    def test_issue_template_has_labels(self) -> None:
        """T-D6.06-12: Issue template frontmatter includes labels."""
        text = _read(ISSUE_TEMPLATE_PATH)
        fm = _parse_frontmatter(text)
        assert "labels" in fm, "Frontmatter missing 'labels'"

    def test_issue_template_body_matches_checklist(self) -> None:
        """T-D6.06-13: Issue template body contains all 14 page headings + summary."""
        text = _read(ISSUE_TEMPLATE_PATH)
        # Strip frontmatter
        body = re.sub(r"^---.*?---\s*", "", text, count=1, flags=re.DOTALL)
        assert "## Summary Sign-Off" in body
        for page in EXPECTED_PAGES:
            assert f"### {page}" in body, f"Issue template missing page heading: {page}"
