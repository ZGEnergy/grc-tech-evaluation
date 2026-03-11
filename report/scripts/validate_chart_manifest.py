"""Bidirectional chart-manifest cross-reference validator.

Ensures consistency between chart-manifest.json, chart image files on disk,
and MDX source files that embed charts.

Direction 1 (forward): scans MDX files for image references matching chart naming
convention, verifies each has a manifest entry and file on disk.

Direction 2 (reverse): verifies every manifest entry is referenced by at least one
MDX file (orphaned = warning). Missing files = errors; orphaned entries = warnings.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REPORT_DIR = SCRIPT_DIR.parent
DEFAULT_DOCS_DIR = REPORT_DIR / "docs"
DEFAULT_STATIC_DIR = REPORT_DIR / "static"
DEFAULT_MANIFEST_PATH = DEFAULT_STATIC_DIR / "img" / "chart-manifest.json"

CHART_FILENAME_PATTERN = re.compile(
    r"^(radar|bar|heatmap|scatter|line|grouped_bar|stacked_bar|lollipop|table)_[\w]+\.(svg|png)$"
)

# MDX image reference patterns
# Markdown: ![alt text](/img/radar_overall_scores.svg)
_MD_IMG_PATTERN = re.compile(r"!\[[^\]]*\]\((/img/[^)]+)\)")
# HTML: <img src="/img/bar_expressiveness_grades.png" />
_HTML_IMG_PATTERN = re.compile(r'<img\s[^>]*src=["\'](/img/[^"\']+)["\']')


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChartEntry:
    """A single entry from the chart manifest."""

    key: str
    filename: str
    chart_type: str
    title: str


@dataclass(frozen=True)
class ChartReference:
    """An image reference found in an MDX file that matches chart naming."""

    source_file: Path
    image_path: str
    filename: str
    line_number: int


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class ManifestIssue:
    """A single validation issue."""

    severity: Severity
    message: str
    source_file: Path | None
    chart_key: str | None
    filename: str | None


@dataclass
class ManifestValidationReport:
    """Aggregated result of forward + reverse validation."""

    forward_checked: int
    reverse_checked: int
    issues: list[ManifestIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ManifestIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ManifestIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> str:
        lines = [
            f"Forward references checked: {self.forward_checked}",
            f"Reverse manifest entries checked: {self.reverse_checked}",
            f"Errors: {len(self.errors)}",
            f"Warnings: {len(self.warnings)}",
            f"Result: {'PASS' if self.passed else 'FAIL'}",
        ]
        if self.errors:
            lines.append("")
            lines.append("Errors:")
            for issue in self.errors:
                lines.append(f"  - {issue.message}")
        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            for issue in self.warnings:
                lines.append(f"  - {issue.message}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def load_manifest(manifest_path: Path) -> dict[str, ChartEntry]:
    """Load chart-manifest.json and return a dict keyed by filename.

    The manifest structure is::

        {
          "charts": [
            {
              "id": "...",
              "type": "radar",
              "subject": "...",
              "files": {"svg": "img/radar_foo.svg", "png": "img/radar_foo.png"},
              "data_source": "...",
              "title": "..."
            }
          ]
        }

    Each file path in the ``files`` dict produces a ChartEntry keyed by its
    basename (e.g. ``radar_foo.svg``).

    Args:
        manifest_path: Path to chart-manifest.json.

    Returns:
        Dict mapping filename to ChartEntry.

    Raises:
        FileNotFoundError: If manifest_path does not exist.
        json.JSONDecodeError: If manifest is not valid JSON.
        ValueError: If the manifest structure is unexpected.
    """
    with open(manifest_path) as f:
        data = json.load(f)

    if "charts" not in data:
        raise ValueError("Manifest missing required 'charts' key")

    charts = data["charts"]
    if not isinstance(charts, list):
        raise ValueError("'charts' must be a list")

    entries: dict[str, ChartEntry] = {}
    for entry in charts:
        entry_id = entry.get("id", "unknown")
        chart_type = entry.get("type", "unknown")
        title = entry.get("title", "")
        files = entry.get("files", {})
        if not isinstance(files, dict):
            continue
        for _fmt, rel_path in files.items():
            filename = Path(rel_path).name
            entries[filename] = ChartEntry(
                key=entry_id,
                filename=filename,
                chart_type=chart_type,
                title=title,
            )

    return entries


def scan_mdx_chart_references(docs_dir: Path) -> list[ChartReference]:
    """Scan all MDX files under docs_dir for chart image references.

    Recognises two patterns:
    - Markdown images: ``![alt](/img/chart_name.svg)``
    - HTML img tags: ``<img src="/img/chart_name.png" />``

    Only references whose filename matches CHART_FILENAME_PATTERN are returned.

    Args:
        docs_dir: Root directory containing .mdx files.

    Returns:
        List of ChartReference objects.
    """
    references: list[ChartReference] = []

    if not docs_dir.exists():
        return references

    for mdx_file in sorted(docs_dir.rglob("*.mdx")):
        text = mdx_file.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in _MD_IMG_PATTERN.finditer(line):
                image_path = match.group(1)
                filename = Path(image_path).name
                if CHART_FILENAME_PATTERN.match(filename):
                    references.append(
                        ChartReference(
                            source_file=mdx_file,
                            image_path=image_path,
                            filename=filename,
                            line_number=line_number,
                        )
                    )
            for match in _HTML_IMG_PATTERN.finditer(line):
                image_path = match.group(1)
                filename = Path(image_path).name
                if CHART_FILENAME_PATTERN.match(filename):
                    references.append(
                        ChartReference(
                            source_file=mdx_file,
                            image_path=image_path,
                            filename=filename,
                            line_number=line_number,
                        )
                    )

    return references


def validate_forward(
    references: list[ChartReference],
    manifest: dict[str, ChartEntry],
    static_dir: Path,
) -> list[ManifestIssue]:
    """Forward validation: check each MDX chart reference.

    For each chart reference found in MDX:
    1. Verify the filename has a manifest entry (error if missing).
    2. Verify the image file exists on disk (error if missing).

    Args:
        references: Chart references from scan_mdx_chart_references.
        manifest: Loaded manifest from load_manifest.
        static_dir: The report/static/ directory for resolving file paths.

    Returns:
        List of ManifestIssue objects.
    """
    issues: list[ManifestIssue] = []

    for ref in references:
        # Check manifest entry
        if ref.filename not in manifest:
            issues.append(
                ManifestIssue(
                    severity=Severity.ERROR,
                    message=(
                        f"Chart '{ref.filename}' referenced in "
                        f"{ref.source_file.name}:{ref.line_number} "
                        f"has no manifest entry"
                    ),
                    source_file=ref.source_file,
                    chart_key=None,
                    filename=ref.filename,
                )
            )

        # Check file on disk — image_path starts with /img/..., resolve to static_dir
        # Strip leading slash to make relative to static_dir
        rel_path = ref.image_path.lstrip("/")
        file_on_disk = static_dir / rel_path
        if not file_on_disk.exists():
            issues.append(
                ManifestIssue(
                    severity=Severity.ERROR,
                    message=(
                        f"Chart file '{ref.filename}' referenced in "
                        f"{ref.source_file.name}:{ref.line_number} "
                        f"not found on disk at {file_on_disk}"
                    ),
                    source_file=ref.source_file,
                    chart_key=None,
                    filename=ref.filename,
                )
            )

    return issues


def validate_reverse(
    manifest: dict[str, ChartEntry],
    references: list[ChartReference],
) -> list[ManifestIssue]:
    """Reverse validation: check each manifest entry is referenced.

    Every manifest entry that is not referenced by any MDX file produces
    an orphaned-entry warning.

    Args:
        manifest: Loaded manifest from load_manifest.
        references: Chart references from scan_mdx_chart_references.

    Returns:
        List of ManifestIssue objects (warnings only).
    """
    referenced_filenames = {ref.filename for ref in references}
    issues: list[ManifestIssue] = []

    for filename, entry in sorted(manifest.items()):
        if filename not in referenced_filenames:
            issues.append(
                ManifestIssue(
                    severity=Severity.WARNING,
                    message=(
                        f"Manifest entry '{entry.key}' (file: {filename}) "
                        f"is not referenced by any MDX file"
                    ),
                    source_file=None,
                    chart_key=entry.key,
                    filename=filename,
                )
            )

    return issues


def validate_chart_manifest(
    docs_dir: Path,
    static_dir: Path,
    manifest_path: Path,
) -> ManifestValidationReport:
    """Run full bidirectional validation.

    1. Load the manifest.
    2. Scan MDX files for chart references.
    3. Run forward validation (MDX -> manifest + disk).
    4. Run reverse validation (manifest -> MDX).

    Args:
        docs_dir: Root directory containing .mdx files.
        static_dir: The report/static/ directory.
        manifest_path: Path to chart-manifest.json.

    Returns:
        ManifestValidationReport with all issues.
    """
    manifest = load_manifest(manifest_path)
    references = scan_mdx_chart_references(docs_dir)

    forward_issues = validate_forward(references, manifest, static_dir)
    reverse_issues = validate_reverse(manifest, references)

    return ManifestValidationReport(
        forward_checked=len(references),
        reverse_checked=len(manifest),
        issues=forward_issues + reverse_issues,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Returns:
        0 if no errors (warnings OK), 1 if errors found, 2 if manifest
        not found or unparseable.
    """
    parser = argparse.ArgumentParser(
        description="Validate chart-manifest.json against MDX sources and image files."
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=DEFAULT_DOCS_DIR,
        help="Directory containing .mdx files",
    )
    parser.add_argument(
        "--static-dir",
        type=Path,
        default=DEFAULT_STATIC_DIR,
        help="Static assets directory",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help="Path to chart-manifest.json",
    )
    args = parser.parse_args(argv)

    try:
        report = validate_chart_manifest(args.docs_dir, args.static_dir, args.manifest)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except (json.JSONDecodeError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    print(report.summary())
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
