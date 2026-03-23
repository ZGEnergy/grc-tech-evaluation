"""Post-deployment smoke test for the Docusaurus report site on GitHub Pages.

Fetches the root URL and key sub-pages, checking for HTTP 200 responses, correct
content-type headers, presence of expected title fragments, and absence of the
GitHub Pages 404 page. Uses only stdlib (urllib) — no third-party dependencies.

Usage:
    python report/scripts/smoke_test.py [SITE_URL] [--timeout SECONDS]

Environment variables:
    SITE_URL — overrides the positional argument (for CI usage)

Exit codes:
    0 — all smoke checks pass
    1 — one or more pages fail smoke checks
    2 — site URL is unreachable (connection error on root page)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PageExpectation:
    """Defines what to check for a given page.

    Attributes:
        path: URL path relative to base (e.g., "/results/").
        description: Human-readable label for reporting.
        title_fragment: Expected text in response body (None to skip check).
    """

    path: str
    description: str
    title_fragment: str | None


SMOKE_TEST_PAGES: list[PageExpectation] = [
    PageExpectation(
        path="/",
        description="Home page",
        title_fragment="Phase 1 Technology Evaluation",
    ),
    PageExpectation(
        path="/results/",
        description="Results Overview",
        title_fragment="Results",
    ),
    PageExpectation(
        path="/results/expressiveness/",
        description="Expressiveness Results",
        title_fragment="Expressiveness",
    ),
    PageExpectation(
        path="/grid-primer/",
        description="Grid Operations Primer",
        title_fragment="Grid Operations Primer",
    ),
    PageExpectation(
        path="/tools-evaluated/",
        description="Tools Evaluated",
        title_fragment="Tools Evaluated",
    ),
]


class SmokeStatus(Enum):
    """Result status for a single smoke check."""

    PASS = "pass"
    FAIL_HTTP = "fail_http"
    FAIL_CONTENT_TYPE = "fail_content_type"
    FAIL_TITLE = "fail_title"
    FAIL_404_PAGE = "fail_404_page"
    FAIL_CONNECTION = "fail_connection"


@dataclass(frozen=True)
class SmokeCheckResult:
    """Outcome of checking a single page.

    Attributes:
        page: The expectation that was checked.
        status: Pass/fail classification.
        http_status: HTTP status code, or None if the connection failed.
        detail: Error description, or None if the check passed.
    """

    page: PageExpectation
    status: SmokeStatus
    http_status: int | None
    detail: str | None


@dataclass
class SmokeTestReport:
    """Aggregated results from a full smoke test run.

    Attributes:
        site_url: The base URL that was tested.
        results: Per-page check results.
    """

    site_url: str
    results: list[SmokeCheckResult]

    @property
    def passed(self) -> bool:
        """True if every page check passed."""
        return all(r.status == SmokeStatus.PASS for r in self.results)

    def summary(self) -> str:
        """Human-readable summary for CLI output."""
        lines = [f"SMOKE TEST: {self.site_url}", ""]
        for r in self.results:
            if r.status == SmokeStatus.PASS:
                tag = "PASS"
                extra = f"({r.http_status} OK)"
            else:
                tag = "FAIL"
                extra = f"({r.detail})"
            lines.append(f"  [{tag}] {r.page.description:<25s} {extra}")

        passed_count = sum(1 for r in self.results if r.status == SmokeStatus.PASS)
        total = len(self.results)
        verdict = "PASSED" if self.passed else "FAILED"
        lines.append("")
        lines.append(f"Result: {verdict} ({passed_count}/{total} passed)")
        return "\n".join(lines)


# GitHub Pages 404 markers
GITHUB_PAGES_404_MARKERS = [
    "There isn't a GitHub Pages site here.",
    "404 - File not found",
]


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def build_site_url(config_path: Path) -> str:
    """Extract url and baseUrl from docusaurus.config.js and construct the site URL.

    Args:
        config_path: Path to the docusaurus.config.js file.

    Returns:
        The full site URL (e.g., "https://zge-energy.github.io/grc-tech-evaluation/").

    Raises:
        ValueError: If the config file cannot be parsed for url/baseUrl.
    """
    content = config_path.read_text()
    url_match = re.search(r"""url:\s*['"]([^'"]+)['"]""", content)
    base_match = re.search(r"""baseUrl:\s*['"]([^'"]+)['"]""", content)
    if not url_match or not base_match:
        msg = f"Could not extract url/baseUrl from {config_path}"
        raise ValueError(msg)
    url = url_match.group(1).rstrip("/")
    base_url = base_match.group(1)
    return f"{url}{base_url}"


def detect_404_page(response_body: str) -> bool:
    """Check if the response body contains GitHub Pages 404 markers.

    Args:
        response_body: The HTML body text of the response.

    Returns:
        True if any known GitHub Pages 404 marker is found in the body.
    """
    return any(marker in response_body for marker in GITHUB_PAGES_404_MARKERS)


def check_page(
    base_url: str,
    page: PageExpectation,
    timeout: int = 30,
) -> SmokeCheckResult:
    """Perform HTTP GET on a single page and validate the response.

    Uses urllib (stdlib) to avoid requiring requests as a dependency.

    Args:
        base_url: The site base URL (e.g., "https://example.github.io/repo/").
        page: The page expectation to check.
        timeout: HTTP request timeout in seconds.

    Returns:
        A SmokeCheckResult describing the outcome.
    """
    url = base_url.rstrip("/") + page.path
    req = Request(url, headers={"User-Agent": "grc-smoke-test/1.0"})

    try:
        response = urlopen(req, timeout=timeout)  # noqa: S310
    except HTTPError as exc:
        return SmokeCheckResult(
            page=page,
            status=SmokeStatus.FAIL_HTTP,
            http_status=exc.code,
            detail=f"{exc.code} {exc.reason}",
        )
    except (URLError, TimeoutError, OSError):
        return SmokeCheckResult(
            page=page,
            status=SmokeStatus.FAIL_CONNECTION,
            http_status=None,
            detail="Connection error or timeout",
        )

    http_status = response.status
    content_type = response.headers.get("Content-Type", "")
    body = response.read().decode("utf-8", errors="replace")

    # Check content type
    if "text/html" not in content_type:
        return SmokeCheckResult(
            page=page,
            status=SmokeStatus.FAIL_CONTENT_TYPE,
            http_status=http_status,
            detail=f"Expected text/html, got {content_type}",
        )

    # Check for GitHub Pages 404 body
    if detect_404_page(body):
        return SmokeCheckResult(
            page=page,
            status=SmokeStatus.FAIL_404_PAGE,
            http_status=http_status,
            detail="GitHub Pages 404 page detected",
        )

    # Check title fragment
    if page.title_fragment is not None and page.title_fragment not in body:
        return SmokeCheckResult(
            page=page,
            status=SmokeStatus.FAIL_TITLE,
            http_status=http_status,
            detail=f"Expected '{page.title_fragment}' not found in body",
        )

    return SmokeCheckResult(
        page=page,
        status=SmokeStatus.PASS,
        http_status=http_status,
        detail=None,
    )


def run_smoke_test(
    site_url: str,
    pages: list[PageExpectation] | None = None,
    timeout: int = 30,
) -> SmokeTestReport:
    """Run smoke checks against all configured pages.

    Args:
        site_url: The base URL of the deployed site.
        pages: Pages to check. Defaults to SMOKE_TEST_PAGES.
        timeout: HTTP request timeout in seconds per page.

    Returns:
        A SmokeTestReport with results for every page.
    """
    if pages is None:
        pages = SMOKE_TEST_PAGES
    results = [check_page(site_url, page, timeout=timeout) for page in pages]
    return SmokeTestReport(site_url=site_url, results=results)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the smoke test.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 = all pass, 1 = some fail, 2 = root unreachable.
    """
    parser = argparse.ArgumentParser(description="Post-deployment smoke test")
    parser.add_argument(
        "site_url",
        nargs="?",
        default=None,
        help="Base URL of the deployed site",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP request timeout in seconds per page (default: 30)",
    )
    args = parser.parse_args(argv)

    # Priority: env var > CLI arg > derived from config
    site_url = os.environ.get("SITE_URL") or args.site_url
    if not site_url:
        config_path = Path(__file__).resolve().parent.parent / "docusaurus.config.js"
        site_url = build_site_url(config_path)

    report = run_smoke_test(site_url, timeout=args.timeout)
    print(report.summary())  # noqa: T201

    if report.passed:
        return 0
    # Check if root page had a connection error (exit code 2)
    root_results = [r for r in report.results if r.page.path == "/"]
    if root_results and root_results[0].status == SmokeStatus.FAIL_CONNECTION:
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
