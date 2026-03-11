"""Post-build validation: version stamp presence and placeholder absence.

Checks every HTML doc page in the Docusaurus build output for:
1. Protocol version string (from docusaurus.config.js customFields.protocolVersion)
2. "Last updated" timestamp
3. No rendered <Placeholder /> component output

Exit codes: 0 = pass, 1 = failures found, 2 = build dir missing.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

DEFAULT_PROTOCOL_VERSION = "v7"
PLACEHOLDER_CSS_CLASS = "placeholder-slot"
PLACEHOLDER_TEXT_MARKER = "Interactive version coming soon"
LAST_UPDATED_PATTERN = r"Last updated"


class CheckType(Enum):
    VERSION_STAMP = "version_stamp"
    LAST_UPDATED = "last_updated"
    PLACEHOLDER_ABSENCE = "placeholder_absence"


@dataclass(frozen=True)
class ContentCheck:
    page_path: Path
    check_type: CheckType
    passed: bool
    detail: str | None


@dataclass
class ContentValidationReport:
    pages_scanned: int
    checks: list[ContentCheck] = field(default_factory=list)
    allow_placeholders: bool = False

    @property
    def failures(self) -> list[ContentCheck]:
        return [c for c in self.checks if not c.passed]

    @property
    def passed(self) -> bool:
        return len(self.failures) == 0

    def summary(self) -> str:
        total = len(self.checks)
        failed = len(self.failures)
        passed = total - failed
        lines = [
            f"Content validation: {passed}/{total} checks passed "
            f"({self.pages_scanned} pages scanned)",
        ]
        if self.allow_placeholders:
            lines.append("  (placeholder checks in permissive mode)")
        for f in self.failures:
            lines.append(f"  FAIL {f.check_type.value}: {f.page_path} — {f.detail}")
        if not self.failures:
            lines.append("  All checks passed.")
        return "\n".join(lines)


def extract_protocol_version(config_path: Path) -> str:
    """Extract protocolVersion from docusaurus.config.js customFields."""
    text = config_path.read_text(encoding="utf-8")
    match = re.search(r"""protocolVersion:\s*['"]([^'"]+)['"]""", text)
    if match:
        return match.group(1)
    return DEFAULT_PROTOCOL_VERSION


def find_doc_pages(build_dir: Path) -> list[Path]:
    """Find all HTML doc pages in the build directory.

    Excludes common non-doc pages like 404.html and search/index.html.
    """
    html_files = sorted(build_dir.rglob("*.html"))
    excluded_names = {"404.html"}
    excluded_dirs = {"assets", "search"}
    results = []
    for f in html_files:
        if f.name in excluded_names:
            continue
        rel_parts = f.relative_to(build_dir).parts
        if any(part in excluded_dirs for part in rel_parts):
            continue
        results.append(f)
    return results


def check_version_stamp(html_content: str, protocol_version: str) -> bool:
    """Check whether the HTML content contains the protocol version string."""
    return protocol_version in html_content


def check_last_updated(html_content: str) -> bool:
    """Check whether the HTML content contains a 'Last updated' timestamp."""
    return bool(re.search(LAST_UPDATED_PATTERN, html_content))


def check_placeholder_absence(html_content: str) -> bool:
    """Check that no rendered Placeholder component output exists.

    Returns True if NO placeholder is found (i.e. the page is clean).
    Detects both the CSS class marker and the text content marker.
    """
    if PLACEHOLDER_CSS_CLASS in html_content:
        return False
    if PLACEHOLDER_TEXT_MARKER in html_content:
        return False
    return True


def validate_page(
    page_path: Path,
    protocol_version: str,
    allow_placeholders: bool,
) -> list[ContentCheck]:
    """Run all content checks on a single HTML page."""
    html = page_path.read_text(encoding="utf-8")
    checks: list[ContentCheck] = []

    # Version stamp check
    version_ok = check_version_stamp(html, protocol_version)
    checks.append(
        ContentCheck(
            page_path=page_path,
            check_type=CheckType.VERSION_STAMP,
            passed=version_ok,
            detail=None
            if version_ok
            else f"Missing protocol version '{protocol_version}'",
        )
    )

    # Last updated check
    last_updated_ok = check_last_updated(html)
    checks.append(
        ContentCheck(
            page_path=page_path,
            check_type=CheckType.LAST_UPDATED,
            passed=last_updated_ok,
            detail=None if last_updated_ok else "Missing 'Last updated' timestamp",
        )
    )

    # Placeholder absence check
    placeholder_clean = check_placeholder_absence(html)
    if allow_placeholders:
        # In permissive mode, always pass but note if placeholder found
        checks.append(
            ContentCheck(
                page_path=page_path,
                check_type=CheckType.PLACEHOLDER_ABSENCE,
                passed=True,
                detail=None if placeholder_clean else "Placeholder found (allowed)",
            )
        )
    else:
        checks.append(
            ContentCheck(
                page_path=page_path,
                check_type=CheckType.PLACEHOLDER_ABSENCE,
                passed=placeholder_clean,
                detail=None
                if placeholder_clean
                else "Rendered placeholder component found",
            )
        )

    return checks


def validate_content(
    build_dir: Path,
    config_path: Path,
    allow_placeholders: bool = False,
) -> ContentValidationReport:
    """Validate all doc pages in the build directory."""
    protocol_version = extract_protocol_version(config_path)
    pages = find_doc_pages(build_dir)
    report = ContentValidationReport(
        pages_scanned=len(pages),
        allow_placeholders=allow_placeholders,
    )
    for page in pages:
        page_checks = validate_page(page, protocol_version, allow_placeholders)
        report.checks.extend(page_checks)
    return report


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate built HTML for version stamps and placeholder absence.",
    )
    parser.add_argument(
        "build_dir",
        nargs="?",
        default="report/build",
        help="Path to the Docusaurus build output directory",
    )
    parser.add_argument(
        "--allow-placeholders",
        action="store_true",
        help="Permissive mode: do not fail on placeholder components",
    )
    parser.add_argument(
        "--config",
        default="report/docusaurus.config.js",
        help="Path to docusaurus.config.js",
    )
    args = parser.parse_args(argv)

    build_dir = Path(args.build_dir)
    config_path = Path(args.config)

    if not build_dir.is_dir():
        print(f"ERROR: Build directory not found: {build_dir}", file=sys.stderr)
        return 2

    report = validate_content(build_dir, config_path, args.allow_placeholders)
    print(report.summary())
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
