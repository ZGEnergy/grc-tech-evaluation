"""Tests for the deployment smoke test script.

Covers 14 success criteria (T-D6.05-01 through T-D6.05-14) from the PRD.
All HTTP interactions are mocked — no network calls are made.
"""

from __future__ import annotations

import http.client
import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from scripts.smoke_test import (
    SMOKE_TEST_PAGES,
    PageExpectation,
    SmokeCheckResult,
    SmokeStatus,
    SmokeTestReport,
    build_site_url,
    check_page,
    detect_404_page,
    run_smoke_test,
)

REPORT_DIR = Path(__file__).resolve().parent.parent
MAKEFILE_PATH = REPORT_DIR / "Makefile"
WORKFLOW_PATH = REPORT_DIR.parent / ".github" / "workflows" / "deploy-report.yml"

BASE_URL = "https://example.github.io/repo/"
HOME_PAGE = PageExpectation(
    path="/",
    description="Home page",
    title_fragment="My Site Title",
)


# ---------------------------------------------------------------------------
# Helpers for mocking urllib responses
# ---------------------------------------------------------------------------


def _mock_response(
    body: str = "<html><title>My Site Title</title></html>",
    status: int = 200,
    content_type: str = "text/html; charset=utf-8",
) -> MagicMock:
    """Create a mock urllib response object."""
    resp = MagicMock()
    resp.status = status
    resp.headers = http.client.HTTPMessage()
    resp.headers["Content-Type"] = content_type
    resp.read.return_value = body.encode("utf-8")
    return resp


# ---------------------------------------------------------------------------
# T-D6.05-01: check_page returns PASS for 200 OK with correct content
# ---------------------------------------------------------------------------


class TestCheckPage:
    """Unit tests for check_page."""

    @patch("scripts.smoke_test.urlopen")
    def test_check_page_200_ok(self, mock_urlopen: MagicMock) -> None:
        """T-D6.05-01: 200 with correct content-type and title yields PASS."""
        mock_urlopen.return_value = _mock_response()
        result = check_page(BASE_URL, HOME_PAGE)
        assert result.status == SmokeStatus.PASS
        assert result.http_status == 200
        assert result.detail is None

    @patch("scripts.smoke_test.urlopen")
    def test_check_page_404(self, mock_urlopen: MagicMock) -> None:
        """T-D6.05-02: HTTP 404 yields FAIL_HTTP with http_status=404."""
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(
            url="http://example.com",
            code=404,
            msg="Not Found",
            hdrs=http.client.HTTPMessage(),
            fp=io.BytesIO(b""),
        )
        result = check_page(BASE_URL, HOME_PAGE)
        assert result.status == SmokeStatus.FAIL_HTTP
        assert result.http_status == 404

    @patch("scripts.smoke_test.urlopen")
    def test_check_page_wrong_content_type(self, mock_urlopen: MagicMock) -> None:
        """T-D6.05-03: 200 with application/json yields FAIL_CONTENT_TYPE."""
        mock_urlopen.return_value = _mock_response(content_type="application/json")
        result = check_page(BASE_URL, HOME_PAGE)
        assert result.status == SmokeStatus.FAIL_CONTENT_TYPE

    @patch("scripts.smoke_test.urlopen")
    def test_check_page_missing_title(self, mock_urlopen: MagicMock) -> None:
        """T-D6.05-04: 200 with HTML missing expected title yields FAIL_TITLE."""
        mock_urlopen.return_value = _mock_response(
            body="<html><title>Other</title></html>"
        )
        result = check_page(BASE_URL, HOME_PAGE)
        assert result.status == SmokeStatus.FAIL_TITLE

    @patch("scripts.smoke_test.urlopen")
    def test_check_page_github_404_body(self, mock_urlopen: MagicMock) -> None:
        """T-D6.05-05: 200 with GitHub Pages 404 body yields FAIL_404_PAGE."""
        body = "<html>There isn't a GitHub Pages site here.</html>"
        mock_urlopen.return_value = _mock_response(body=body)
        result = check_page(BASE_URL, HOME_PAGE)
        assert result.status == SmokeStatus.FAIL_404_PAGE

    @patch("scripts.smoke_test.urlopen")
    def test_check_page_connection_error(self, mock_urlopen: MagicMock) -> None:
        """T-D6.05-06: Connection timeout yields FAIL_CONNECTION."""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("timed out")
        result = check_page(BASE_URL, HOME_PAGE)
        assert result.status == SmokeStatus.FAIL_CONNECTION
        assert result.http_status is None


# ---------------------------------------------------------------------------
# T-D6.05-07 / T-D6.05-08: detect_404_page
# ---------------------------------------------------------------------------


class TestDetect404Page:
    """Unit tests for detect_404_page."""

    def test_detect_404_page_positive(self) -> None:
        """T-D6.05-07: Body with GitHub Pages 404 marker returns True."""
        assert detect_404_page("There isn't a GitHub Pages site here.")
        assert detect_404_page("Some prefix 404 - File not found some suffix")

    def test_detect_404_page_negative(self) -> None:
        """T-D6.05-08: Normal HTML body returns False."""
        assert not detect_404_page("<html><title>My Site</title></html>")


# ---------------------------------------------------------------------------
# T-D6.05-09 / T-D6.05-10: SmokeTestReport
# ---------------------------------------------------------------------------


class TestSmokeTestReport:
    """Unit tests for SmokeTestReport.passed property."""

    def test_report_all_pass(self) -> None:
        """T-D6.05-09: Report with all PASS results has passed=True."""
        results = [
            SmokeCheckResult(
                page=HOME_PAGE, status=SmokeStatus.PASS, http_status=200, detail=None
            )
            for _ in range(3)
        ]
        report = SmokeTestReport(site_url=BASE_URL, results=results)
        assert report.passed is True

    def test_report_any_fail(self) -> None:
        """T-D6.05-10: Report with one FAIL_HTTP result has passed=False."""
        results = [
            SmokeCheckResult(
                page=HOME_PAGE, status=SmokeStatus.PASS, http_status=200, detail=None
            ),
            SmokeCheckResult(
                page=HOME_PAGE,
                status=SmokeStatus.FAIL_HTTP,
                http_status=404,
                detail="404 Not Found",
            ),
        ]
        report = SmokeTestReport(site_url=BASE_URL, results=results)
        assert report.passed is False


# ---------------------------------------------------------------------------
# T-D6.05-11: run_smoke_test checks all pages
# ---------------------------------------------------------------------------


class TestRunSmokeTest:
    """Unit tests for run_smoke_test."""

    @patch("scripts.smoke_test.urlopen")
    def test_run_smoke_test_all_pages(self, mock_urlopen: MagicMock) -> None:
        """T-D6.05-11: run_smoke_test returns results for all 5 configured pages."""
        mock_urlopen.return_value = _mock_response(
            body="<html>Phase 1 Technology Evaluation Results "
            "Expressiveness Grid Primer Tools Evaluated</html>"
        )
        report = run_smoke_test(BASE_URL)
        assert len(report.results) == len(SMOKE_TEST_PAGES)
        assert len(report.results) == 5


# ---------------------------------------------------------------------------
# T-D6.05-12: build_site_url from config
# ---------------------------------------------------------------------------


class TestBuildSiteUrl:
    """Unit tests for build_site_url."""

    def test_build_site_url_from_config(self, tmp_path: Path) -> None:
        """T-D6.05-12: Extract URL from docusaurus.config.js."""
        config = tmp_path / "docusaurus.config.js"
        config.write_text(
            "const config = {\n"
            "  url: 'https://zge-energy.github.io',\n"
            "  baseUrl: '/grc-tech-evaluation/',\n"
            "};\n"
        )
        result = build_site_url(config)
        assert result == "https://zge-energy.github.io/grc-tech-evaluation/"


# ---------------------------------------------------------------------------
# T-D6.05-13: Makefile smoke target
# ---------------------------------------------------------------------------


class TestMakefileSmokeTarget:
    """File-check test for the Makefile."""

    def test_makefile_smoke_target_exists(self) -> None:
        """T-D6.05-13: Parse report/Makefile and verify a `smoke` target is defined."""
        text = MAKEFILE_PATH.read_text()
        # Check .PHONY includes smoke
        for line in text.splitlines():
            if line.startswith(".PHONY:"):
                targets = line.split(":", 1)[1].split()
                assert "smoke" in targets, f"smoke not in .PHONY targets: {targets}"
                break
        else:
            pytest.fail(".PHONY declaration not found")

        # Check smoke target definition exists
        assert "\nsmoke:" in text or text.startswith("smoke:"), (
            "smoke target definition not found"
        )


# ---------------------------------------------------------------------------
# T-D6.05-14: workflow has smoke step
# ---------------------------------------------------------------------------


class TestWorkflowSmokeStep:
    """File-check test for deploy-report.yml."""

    def test_workflow_has_smoke_step(self) -> None:
        """T-D6.05-14: deploy-report.yml contains a post-deployment step running make smoke."""
        config = yaml.safe_load(WORKFLOW_PATH.read_text())
        deploy_steps = config["jobs"]["deploy"]["steps"]
        smoke_found = False
        for step in deploy_steps:
            run_cmd = step.get("run", "")
            if "make smoke" in run_cmd:
                smoke_found = True
                break
        assert smoke_found, "No step running 'make smoke' found in deploy job"
