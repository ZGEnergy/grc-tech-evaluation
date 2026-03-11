"""Tests for report/scripts/validate_content.py (PRD 06/03 — Version Stamp & Placeholder Validator).

18 tests covering version stamp checks, last updated checks, placeholder absence,
permissive mode, config extraction, report properties, integration tests, and exit codes.
"""

from __future__ import annotations

from pathlib import Path

from scripts.validate_content import (
    DEFAULT_PROTOCOL_VERSION,
    PLACEHOLDER_CSS_CLASS,
    PLACEHOLDER_TEXT_MARKER,
    CheckType,
    ContentCheck,
    ContentValidationReport,
    check_last_updated,
    check_placeholder_absence,
    check_version_stamp,
    extract_protocol_version,
    find_doc_pages,
    main,
    validate_content,
    validate_page,
)

# ── Helpers ────────────────────────────────────────────────────────────

GOOD_HTML = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
<footer>Protocol version: v7 | Built with Docusaurus</footer>
<div>Last updated on Jan 1, 2025</div>
</body>
</html>
"""

MISSING_VERSION_HTML = """<!DOCTYPE html>
<html><body>
<div>Last updated on Jan 1, 2025</div>
</body></html>
"""

MISSING_LAST_UPDATED_HTML = """<!DOCTYPE html>
<html><body>
<footer>Protocol version: v7</footer>
</body></html>
"""

PLACEHOLDER_HTML_CSS = f"""<!DOCTYPE html>
<html><body>
<footer>Protocol version: v7</footer>
<div>Last updated on Jan 1, 2025</div>
<div class="{PLACEHOLDER_CSS_CLASS}">placeholder content</div>
</body></html>
"""

PLACEHOLDER_HTML_TEXT = f"""<!DOCTYPE html>
<html><body>
<footer>Protocol version: v7</footer>
<div>Last updated on Jan 1, 2025</div>
<div>{PLACEHOLDER_TEXT_MARKER}</div>
</body></html>
"""

CONFIG_JS = """
const config = {
  title: 'Test',
  customFields: {
    protocolVersion: 'v8',
  },
};
module.exports = config;
"""

CONFIG_JS_NO_VERSION = """
const config = {
  title: 'Test',
  customFields: {},
};
module.exports = config;
"""


def _write_html(path: Path, content: str = GOOD_HTML) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _make_build_dir(tmp_path: Path, pages: dict[str, str] | None = None) -> Path:
    """Create a build directory with HTML pages."""
    build = tmp_path / "build"
    build.mkdir()
    if pages is None:
        pages = {"index.html": GOOD_HTML, "docs/intro/index.html": GOOD_HTML}
    for rel_path, content in pages.items():
        _write_html(build / rel_path, content)
    return build


def _make_config(tmp_path: Path, content: str = CONFIG_JS) -> Path:
    config = tmp_path / "docusaurus.config.js"
    config.write_text(content, encoding="utf-8")
    return config


# ── T-D6.03-01: check_version_stamp detects version present ──────────


def test_version_stamp_present() -> None:
    assert check_version_stamp(GOOD_HTML, "v7") is True


# ── T-D6.03-02: check_version_stamp detects version missing ──────────


def test_version_stamp_missing() -> None:
    assert check_version_stamp(MISSING_VERSION_HTML, "v7") is False


# ── T-D6.03-03: check_version_stamp with different version ───────────


def test_version_stamp_wrong_version() -> None:
    assert check_version_stamp(GOOD_HTML, "v99") is False


# ── T-D6.03-04: check_last_updated detects timestamp present ─────────


def test_last_updated_present() -> None:
    assert check_last_updated(GOOD_HTML) is True


# ── T-D6.03-05: check_last_updated detects timestamp missing ─────────


def test_last_updated_missing() -> None:
    assert check_last_updated(MISSING_LAST_UPDATED_HTML) is False


# ── T-D6.03-06: check_placeholder_absence clean page ─────────────────


def test_placeholder_absence_clean() -> None:
    assert check_placeholder_absence(GOOD_HTML) is True


# ── T-D6.03-07: check_placeholder_absence detects CSS class ──────────


def test_placeholder_detected_css_class() -> None:
    assert check_placeholder_absence(PLACEHOLDER_HTML_CSS) is False


# ── T-D6.03-08: check_placeholder_absence detects text marker ────────


def test_placeholder_detected_text_marker() -> None:
    assert check_placeholder_absence(PLACEHOLDER_HTML_TEXT) is False


# ── T-D6.03-09: extract_protocol_version from config ─────────────────


def test_extract_protocol_version(tmp_path: Path) -> None:
    config = _make_config(tmp_path, CONFIG_JS)
    assert extract_protocol_version(config) == "v8"


# ── T-D6.03-10: extract_protocol_version falls back to default ───────


def test_extract_protocol_version_fallback(tmp_path: Path) -> None:
    config = _make_config(tmp_path, CONFIG_JS_NO_VERSION)
    assert extract_protocol_version(config) == DEFAULT_PROTOCOL_VERSION


# ── T-D6.03-11: find_doc_pages excludes 404 and asset files ──────────


def test_find_doc_pages_excludes_non_docs(tmp_path: Path) -> None:
    build = tmp_path / "build"
    build.mkdir()
    _write_html(build / "index.html")
    _write_html(build / "404.html")
    _write_html(build / "assets" / "page.html")
    _write_html(build / "search" / "index.html")
    _write_html(build / "docs" / "intro" / "index.html")
    pages = find_doc_pages(build)
    names = [str(p.relative_to(build)) for p in pages]
    assert "index.html" in names
    assert "docs/intro/index.html" in names
    assert "404.html" not in names
    assert "assets/page.html" not in names
    assert "search/index.html" not in names


# ── T-D6.03-12: validate_page returns three checks per page ──────────


def test_validate_page_returns_three_checks(tmp_path: Path) -> None:
    page = _write_html(tmp_path / "page.html", GOOD_HTML)
    checks = validate_page(page, "v7", allow_placeholders=False)
    assert len(checks) == 3
    types = {c.check_type for c in checks}
    assert types == {
        CheckType.VERSION_STAMP,
        CheckType.LAST_UPDATED,
        CheckType.PLACEHOLDER_ABSENCE,
    }


# ── T-D6.03-13: permissive mode passes placeholder check ─────────────


def test_permissive_mode_passes_placeholder(tmp_path: Path) -> None:
    page = _write_html(tmp_path / "page.html", PLACEHOLDER_HTML_TEXT)
    checks = validate_page(page, "v7", allow_placeholders=True)
    placeholder_checks = [
        c for c in checks if c.check_type == CheckType.PLACEHOLDER_ABSENCE
    ]
    assert len(placeholder_checks) == 1
    assert placeholder_checks[0].passed is True
    assert placeholder_checks[0].detail == "Placeholder found (allowed)"


# ── T-D6.03-14: ContentValidationReport.passed property ──────────────


def test_report_passed_property() -> None:
    report = ContentValidationReport(pages_scanned=1)
    report.checks = [
        ContentCheck(Path("a.html"), CheckType.VERSION_STAMP, True, None),
        ContentCheck(Path("a.html"), CheckType.LAST_UPDATED, True, None),
    ]
    assert report.passed is True


# ── T-D6.03-15: ContentValidationReport.failures property ────────────


def test_report_failures_property() -> None:
    fail = ContentCheck(Path("a.html"), CheckType.VERSION_STAMP, False, "missing")
    ok = ContentCheck(Path("a.html"), CheckType.LAST_UPDATED, True, None)
    report = ContentValidationReport(pages_scanned=1, checks=[fail, ok])
    assert len(report.failures) == 1
    assert report.failures[0] is fail


# ── T-D6.03-16: ContentValidationReport.summary output ───────────────


def test_report_summary_content() -> None:
    fail = ContentCheck(Path("a.html"), CheckType.VERSION_STAMP, False, "missing v7")
    report = ContentValidationReport(pages_scanned=2, checks=[fail])
    summary = report.summary()
    assert "0/1 checks passed" in summary
    assert "2 pages scanned" in summary
    assert "FAIL" in summary
    assert "missing v7" in summary


# ── T-D6.03-17: integration — validate_content full pipeline ─────────


def test_validate_content_integration(tmp_path: Path) -> None:
    build = _make_build_dir(tmp_path)
    config = _make_config(tmp_path, CONFIG_JS.replace("v8", "v7"))
    report = validate_content(build, config, allow_placeholders=False)
    assert report.pages_scanned == 2
    assert report.passed is True
    assert len(report.checks) == 6  # 3 checks * 2 pages


# ── T-D6.03-18: CLI exit codes ───────────────────────────────────────


class TestCLIExitCodes:
    def test_exit_2_missing_build_dir(self, tmp_path: Path) -> None:
        """Exit code 2 when build dir does not exist."""
        result = main(
            [str(tmp_path / "nonexistent"), "--config", str(tmp_path / "c.js")]
        )
        assert result == 2

    def test_exit_0_all_pass(self, tmp_path: Path) -> None:
        """Exit code 0 when all checks pass."""
        build = _make_build_dir(tmp_path)
        config = _make_config(tmp_path, CONFIG_JS.replace("v8", "v7"))
        result = main([str(build), "--config", str(config)])
        assert result == 0

    def test_exit_1_failures(self, tmp_path: Path) -> None:
        """Exit code 1 when failures are found."""
        build = _make_build_dir(tmp_path, {"index.html": MISSING_VERSION_HTML})
        config = _make_config(tmp_path)
        result = main([str(build), "--config", str(config)])
        assert result == 1
