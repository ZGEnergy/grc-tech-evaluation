"""Post-build link and image validation for the Docusaurus report site.

Crawls all .html files in the build directory and verifies that every internal
reference (page links, anchors, static assets) resolves correctly. External URLs
are counted but not fetched.

Usage:
    python report/scripts/validate_links.py [BUILD_DIR]

Exit codes:
    0 — all internal references resolve
    1 — broken references found
    2 — build directory missing or contains no HTML files
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from enum import Enum
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


class RefType(Enum):
    """Classification of a link reference."""

    INTERNAL_PAGE = "internal_page"
    INTERNAL_ANCHOR = "internal_anchor"
    STATIC_ASSET = "static_asset"
    EXTERNAL = "external"


@dataclass(frozen=True)
class LinkReference:
    """A single link or asset reference extracted from an HTML file."""

    source_file: Path
    target: str
    ref_type: RefType
    element_tag: str
    line_number: int | None


@dataclass(frozen=True)
class ValidationResult:
    """The outcome of validating a single reference."""

    reference: LinkReference
    is_valid: bool
    error_message: str | None


@dataclass
class ValidationReport:
    """Aggregated results of validating all references in a build directory."""

    total_references: int = 0
    internal_checked: int = 0
    external_skipped: int = 0
    broken: list[ValidationResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Return True if no broken references were found."""
        return len(self.broken) == 0

    def summary(self) -> str:
        """Return a human-readable summary of the validation results."""
        lines = [
            f"Total references: {self.total_references}",
            f"Internal checked: {self.internal_checked}",
            f"External skipped: {self.external_skipped}",
            f"Broken: {len(self.broken)}",
        ]
        if self.broken:
            lines.append("")
            lines.append("Broken references:")
            for result in self.broken:
                ref = result.reference
                lines.append(
                    f"  [{ref.ref_type.value}] {ref.source_file}:{ref.line_number}"
                    f" -> {ref.target}"
                )
                if result.error_message:
                    lines.append(f"    {result.error_message}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML parsing helpers
# ---------------------------------------------------------------------------

# Tags and attributes that can contain references we care about
_LINK_ATTRS: dict[str, list[str]] = {
    "a": ["href"],
    "img": ["src"],
    "source": ["src", "srcset"],
    "link": ["href"],
    "script": ["src"],
}

# File extensions that indicate a static asset reference
_ASSET_EXTENSIONS: set[str] = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".ico",
    ".pdf",
    ".css",
    ".js",
    ".json",
    ".xml",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".mp4",
    ".webm",
    ".zip",
    ".tar",
    ".gz",
}


class _ReferenceCollector(HTMLParser):
    """HTMLParser subclass that collects link and asset references."""

    def __init__(self, source_file: Path) -> None:
        super().__init__()
        self.source_file = source_file
        self.references: list[LinkReference] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_names = _LINK_ATTRS.get(tag)
        if attr_names is None:
            return
        attr_dict = dict(attrs)
        for attr_name in attr_names:
            value = attr_dict.get(attr_name)
            if value is None or value == "":
                continue
            # For srcset, take the first URL
            if attr_name == "srcset":
                value = value.split(",")[0].strip().split()[0]
            ref_type = classify_reference(
                value, self.source_file, "/grc-tech-evaluation/"
            )
            line = self.getpos()[0]
            self.references.append(
                LinkReference(
                    source_file=self.source_file,
                    target=value,
                    ref_type=ref_type,
                    element_tag=tag,
                    line_number=line,
                )
            )


class _AnchorCollector(HTMLParser):
    """HTMLParser subclass that collects all id attributes."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name == "id" and value:
                self.ids.add(value)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

AnchorIndex = dict[Path, set[str]]


def collect_references(html_file: Path) -> list[LinkReference]:
    """Extract all link and asset references from an HTML file.

    Args:
        html_file: Path to an HTML file.

    Returns:
        A list of LinkReference objects found in the file.
    """
    text = html_file.read_text(encoding="utf-8", errors="replace")
    collector = _ReferenceCollector(html_file)
    collector.feed(text)
    return collector.references


def collect_anchor_ids(html_file: Path) -> set[str]:
    """Extract all element id attributes from an HTML file.

    Args:
        html_file: Path to an HTML file.

    Returns:
        A set of id strings found in the file.
    """
    text = html_file.read_text(encoding="utf-8", errors="replace")
    collector = _AnchorCollector()
    collector.feed(text)
    return collector.ids


def build_anchor_index(build_dir: Path) -> AnchorIndex:
    """Build an index mapping each HTML file to its set of anchor ids.

    Args:
        build_dir: Root of the Docusaurus build output.

    Returns:
        A dict mapping resolved Path -> set of id strings.
    """
    index: AnchorIndex = {}
    for html_file in build_dir.rglob("*.html"):
        resolved = html_file.resolve()
        index[resolved] = collect_anchor_ids(html_file)
    return index


def classify_reference(
    href: str,
    source_file: Path,
    base_url: str = "/grc-tech-evaluation/",
) -> RefType:
    """Classify a reference string into a RefType.

    Args:
        href: The raw href or src attribute value.
        source_file: The HTML file containing the reference.
        base_url: The Docusaurus baseUrl prefix.

    Returns:
        The RefType classification.
    """
    # data: URIs, mailto:, tel:, javascript: are treated as external
    if href.startswith(("data:", "mailto:", "tel:", "javascript:")):
        return RefType.EXTERNAL

    parsed = urlparse(href)

    # External if it has a scheme (http, https, etc.)
    if parsed.scheme in ("http", "https"):
        return RefType.EXTERNAL

    # Fragment-only reference (e.g. #section)
    if href.startswith("#"):
        return RefType.INTERNAL_ANCHOR

    # Strip base_url prefix for path analysis
    path_part = parsed.path
    if base_url and path_part.startswith(base_url):
        path_part = "/" + path_part[len(base_url) :]

    # Check if it has a fragment — page + anchor
    has_fragment = bool(parsed.fragment)

    # Check file extension for asset detection
    decoded = unquote(path_part)
    suffix = Path(decoded.split("?")[0]).suffix.lower()
    if suffix in _ASSET_EXTENSIONS:
        return RefType.STATIC_ASSET

    # Page link (with or without fragment)
    if has_fragment:
        return RefType.INTERNAL_ANCHOR
    return RefType.INTERNAL_PAGE


def resolve_page_path(
    href: str,
    source_file: Path,
    build_dir: Path,
    base_url: str = "/grc-tech-evaluation/",
) -> Path | None:
    """Resolve an href to a file path in the build directory.

    Handles Docusaurus trailing-slash convention: ``/results/`` resolves to
    ``results/index.html``, and paths without extensions get ``.html`` or
    ``/index.html`` appended.

    Args:
        href: The raw href string (path portion only, fragment stripped).
        source_file: The HTML file containing the reference.
        build_dir: Root of the build output.
        base_url: The Docusaurus baseUrl prefix.

    Returns:
        The resolved Path if the target file exists, or None.
    """
    parsed = urlparse(href)
    path_str = unquote(parsed.path)

    # Strip query string
    path_str = path_str.split("?")[0]

    if not path_str:
        return None

    # Determine if absolute or relative
    if path_str.startswith("/"):
        # Absolute path — strip baseUrl prefix
        if base_url and path_str.startswith(base_url):
            path_str = path_str[len(base_url) :]
        elif base_url and path_str == base_url.rstrip("/"):
            path_str = ""
        elif path_str.startswith("/"):
            # Strip leading slash for paths that don't match baseUrl
            path_str = path_str.lstrip("/")
        candidate_base = build_dir
    else:
        # Relative path — resolve from the source file's directory
        candidate_base = source_file.parent

    # Build candidate path
    if path_str == "" or path_str == ".":
        candidate = candidate_base / "index.html"
    else:
        candidate = candidate_base / path_str

    # Try the exact path first
    resolved = candidate.resolve()
    if resolved.is_file():
        return resolved

    # Trailing slash convention: try index.html inside the directory
    index_candidate = candidate / "index.html"
    if index_candidate.resolve().is_file():
        return index_candidate.resolve()

    # Try appending .html
    html_candidate = candidate.parent / (candidate.name + ".html")
    if html_candidate.resolve().is_file():
        return html_candidate.resolve()

    # Try as directory with index.html (without trailing slash)
    dir_index = candidate.with_name(candidate.name) / "index.html"
    if dir_index.resolve().is_file():
        return dir_index.resolve()

    return None


def validate_reference(
    ref: LinkReference,
    build_dir: Path,
    anchor_index: AnchorIndex,
    base_url: str = "/grc-tech-evaluation/",
) -> ValidationResult:
    """Validate a single link reference.

    Args:
        ref: The reference to validate.
        build_dir: Root of the build output.
        anchor_index: Pre-built index of anchors per HTML file.
        base_url: The Docusaurus baseUrl prefix.

    Returns:
        A ValidationResult indicating success or failure.
    """
    if ref.ref_type == RefType.EXTERNAL:
        return ValidationResult(reference=ref, is_valid=True, error_message=None)

    if ref.ref_type == RefType.STATIC_ASSET:
        resolved = resolve_page_path(ref.target, ref.source_file, build_dir, base_url)
        if resolved is not None:
            return ValidationResult(reference=ref, is_valid=True, error_message=None)
        return ValidationResult(
            reference=ref,
            is_valid=False,
            error_message=f"Static asset not found: {ref.target}",
        )

    parsed = urlparse(ref.target)
    fragment = parsed.fragment

    if ref.ref_type == RefType.INTERNAL_ANCHOR and ref.target.startswith("#"):
        # Fragment-only: anchor in the same file
        source_resolved = ref.source_file.resolve()
        ids = anchor_index.get(source_resolved, set())
        if fragment in ids:
            return ValidationResult(reference=ref, is_valid=True, error_message=None)
        return ValidationResult(
            reference=ref,
            is_valid=False,
            error_message=f"Anchor '#{fragment}' not found in {ref.source_file.name}",
        )

    # Page link or page + anchor
    resolved = resolve_page_path(ref.target, ref.source_file, build_dir, base_url)
    if resolved is None:
        return ValidationResult(
            reference=ref,
            is_valid=False,
            error_message=f"Page not found: {ref.target}",
        )

    # If there's a fragment, verify the anchor exists in the target page
    if fragment:
        ids = anchor_index.get(resolved, set())
        if fragment not in ids:
            return ValidationResult(
                reference=ref,
                is_valid=False,
                error_message=(
                    f"Anchor '#{fragment}' not found in"
                    f" {resolved.relative_to(build_dir.resolve())}"
                ),
            )

    return ValidationResult(reference=ref, is_valid=True, error_message=None)


def validate_build(
    build_dir: Path,
    base_url: str = "/grc-tech-evaluation/",
) -> ValidationReport:
    """Validate all internal references in a build directory.

    Args:
        build_dir: Root of the Docusaurus build output.
        base_url: The Docusaurus baseUrl prefix.

    Returns:
        A ValidationReport summarizing all findings.
    """
    report = ValidationReport()
    anchor_index = build_anchor_index(build_dir)

    html_files = sorted(build_dir.rglob("*.html"))
    for html_file in html_files:
        refs = collect_references(html_file)
        for ref in refs:
            report.total_references += 1
            if ref.ref_type == RefType.EXTERNAL:
                report.external_skipped += 1
                continue
            report.internal_checked += 1
            result = validate_reference(ref, build_dir, anchor_index, base_url)
            if not result.is_valid:
                report.broken.append(result)

    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run link validation from the command line.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 = pass, 1 = broken links, 2 = bad build dir.
    """
    parser = argparse.ArgumentParser(
        description="Validate internal links and assets in Docusaurus build output.",
    )
    parser.add_argument(
        "build_dir",
        nargs="?",
        default="report/build",
        help="Path to the build output directory (default: report/build)",
    )
    parser.add_argument(
        "--base-url",
        default="/grc-tech-evaluation/",
        help="Docusaurus baseUrl (default: /grc-tech-evaluation/)",
    )
    args = parser.parse_args(argv)

    build_dir = Path(args.build_dir)
    if not build_dir.is_dir():
        print(f"ERROR: Build directory not found: {build_dir}", file=sys.stderr)
        return 2

    html_files = list(build_dir.rglob("*.html"))
    if not html_files:
        print(f"ERROR: No HTML files found in: {build_dir}", file=sys.stderr)
        return 2

    report = validate_build(build_dir, args.base_url)
    print(report.summary())

    if report.passed:
        print("\nAll internal references are valid.")
        return 0
    else:
        print(f"\nFAILED: {len(report.broken)} broken reference(s) found.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
