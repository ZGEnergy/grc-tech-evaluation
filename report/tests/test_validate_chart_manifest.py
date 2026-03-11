"""Tests for validate_chart_manifest.py — bidirectional chart-manifest cross-reference."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_chart_manifest import (
    CHART_FILENAME_PATTERN,
    ChartEntry,
    ChartReference,
    ManifestIssue,
    ManifestValidationReport,
    Severity,
    load_manifest,
    main,
    scan_mdx_chart_references,
    validate_chart_manifest,
    validate_forward,
    validate_reverse,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_manifest(path: Path, charts: list[dict]) -> Path:
    """Write a chart-manifest.json with the given charts list."""
    manifest = {
        "generated_at": "2026-01-01T00:00:00Z",
        "generator_version": "0.1.0",
        "charts": charts,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2))
    return path


def _make_chart_entry(
    chart_id: str = "radar_overall",
    chart_type: str = "radar",
    subject: str = "overall_scores",
    title: str = "Overall Scores",
) -> dict:
    """Create a single manifest chart entry dict."""
    return {
        "id": chart_id,
        "type": chart_type,
        "subject": subject,
        "files": {
            "svg": f"img/{chart_type}_{subject}.svg",
            "png": f"img/{chart_type}_{subject}.png",
        },
        "data_source": "evaluation_results",
        "title": title,
    }


def _write_mdx(docs_dir: Path, name: str, content: str) -> Path:
    """Write an MDX file under docs_dir."""
    docs_dir.mkdir(parents=True, exist_ok=True)
    mdx_file = docs_dir / name
    mdx_file.write_text(content)
    return mdx_file


def _touch_chart_file(static_dir: Path, rel_path: str) -> Path:
    """Create an empty chart file at static_dir / rel_path."""
    full = static_dir / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(b"")
    return full


# ---------------------------------------------------------------------------
# T-D6.02-01: CHART_FILENAME_PATTERN matches valid chart filenames
# ---------------------------------------------------------------------------


class TestChartFilenamePattern:
    """T-D6.02-01: Pattern matches chart naming convention."""

    @pytest.mark.parametrize(
        "filename",
        [
            "radar_overall_scores.svg",
            "bar_expressiveness_grades.png",
            "heatmap_tool_comparison.svg",
            "scatter_perf_vs_accuracy.png",
            "line_scalability_trend.svg",
            "grouped_bar_dim_scores.svg",
            "stacked_bar_composition.png",
            "lollipop_ranking.svg",
            "table_summary_data.png",
        ],
    )
    def test_valid_filenames_match(self, filename: str) -> None:
        assert CHART_FILENAME_PATTERN.match(filename) is not None

    @pytest.mark.parametrize(
        "filename",
        [
            "chart-manifest.json",
            "logo.svg",
            "screenshot.png",
            "radar.svg",  # no underscore after type
            "unknown_type_scores.svg",  # not a recognized chart type
            "radar_scores.txt",  # wrong extension
        ],
    )
    def test_non_chart_filenames_rejected(self, filename: str) -> None:
        assert CHART_FILENAME_PATTERN.match(filename) is None


# ---------------------------------------------------------------------------
# T-D6.02-02: load_manifest reads manifest correctly
# ---------------------------------------------------------------------------


class TestLoadManifest:
    """T-D6.02-02: load_manifest parses chart-manifest.json."""

    def test_load_valid_manifest(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "chart-manifest.json"
        _write_manifest(
            manifest_path,
            [_make_chart_entry("radar_overall", "radar", "overall_scores", "Overall")],
        )
        result = load_manifest(manifest_path)
        assert "radar_overall_scores.svg" in result
        assert "radar_overall_scores.png" in result
        entry = result["radar_overall_scores.svg"]
        assert entry.key == "radar_overall"
        assert entry.chart_type == "radar"
        assert entry.title == "Overall"
        assert isinstance(entry, ChartEntry)

    def test_load_manifest_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_manifest(tmp_path / "nonexistent.json")

    def test_load_manifest_invalid_json(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json")
        with pytest.raises(json.JSONDecodeError):
            load_manifest(bad)

    def test_load_manifest_missing_charts_key(self, tmp_path: Path) -> None:
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps({"version": "1.0"}))
        with pytest.raises(ValueError, match="charts"):
            load_manifest(p)

    def test_load_manifest_empty_charts(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "chart-manifest.json"
        _write_manifest(manifest_path, [])
        result = load_manifest(manifest_path)
        assert result == {}


# ---------------------------------------------------------------------------
# T-D6.02-03: scan_mdx_chart_references finds markdown image references
# ---------------------------------------------------------------------------


class TestScanMdxMarkdownImages:
    """T-D6.02-03: Markdown image syntax detected."""

    def test_markdown_image_detected(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        _write_mdx(docs, "page.mdx", "![Alt text](/img/radar_overall_scores.svg)\n")
        refs = scan_mdx_chart_references(docs)
        assert len(refs) == 1
        assert refs[0].filename == "radar_overall_scores.svg"
        assert refs[0].image_path == "/img/radar_overall_scores.svg"
        assert refs[0].line_number == 1


# ---------------------------------------------------------------------------
# T-D6.02-04: scan_mdx_chart_references finds HTML img tag references
# ---------------------------------------------------------------------------


class TestScanMdxHtmlImages:
    """T-D6.02-04: HTML img src syntax detected."""

    def test_html_img_detected(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        _write_mdx(
            docs,
            "page.mdx",
            '<img src="/img/bar_expressiveness_grades.png" alt="grades" />\n',
        )
        refs = scan_mdx_chart_references(docs)
        assert len(refs) == 1
        assert refs[0].filename == "bar_expressiveness_grades.png"
        assert refs[0].line_number == 1


# ---------------------------------------------------------------------------
# T-D6.02-05: scan ignores non-chart image references
# ---------------------------------------------------------------------------


class TestScanIgnoresNonChart:
    """T-D6.02-05: Non-chart images are ignored."""

    def test_non_chart_images_ignored(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        _write_mdx(
            docs,
            "page.mdx",
            "![Logo](/img/logo.svg)\n![Photo](/img/screenshot.png)\n",
        )
        refs = scan_mdx_chart_references(docs)
        assert len(refs) == 0


# ---------------------------------------------------------------------------
# T-D6.02-06: scan recurses into subdirectories
# ---------------------------------------------------------------------------


class TestScanRecurses:
    """T-D6.02-06: Scans nested directories."""

    def test_nested_mdx_found(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        sub = docs / "results"
        sub.mkdir(parents=True)
        _write_mdx(sub, "detail.mdx", "![Chart](/img/heatmap_tool_comparison.svg)\n")
        refs = scan_mdx_chart_references(docs)
        assert len(refs) == 1
        assert refs[0].filename == "heatmap_tool_comparison.svg"


# ---------------------------------------------------------------------------
# T-D6.02-07: scan returns empty list for missing docs dir
# ---------------------------------------------------------------------------


class TestScanMissingDocsDir:
    """T-D6.02-07: No error on missing docs directory."""

    def test_missing_docs_returns_empty(self, tmp_path: Path) -> None:
        refs = scan_mdx_chart_references(tmp_path / "nonexistent")
        assert refs == []


# ---------------------------------------------------------------------------
# T-D6.02-08: validate_forward — all references valid
# ---------------------------------------------------------------------------


class TestForwardAllValid:
    """T-D6.02-08: No issues when all references have manifest + disk file."""

    def test_all_valid(self, tmp_path: Path) -> None:
        static = tmp_path / "static"
        _touch_chart_file(static, "img/radar_overall_scores.svg")
        manifest = {
            "radar_overall_scores.svg": ChartEntry(
                key="radar_overall",
                filename="radar_overall_scores.svg",
                chart_type="radar",
                title="Overall",
            )
        }
        refs = [
            ChartReference(
                source_file=Path("page.mdx"),
                image_path="/img/radar_overall_scores.svg",
                filename="radar_overall_scores.svg",
                line_number=5,
            )
        ]
        issues = validate_forward(refs, manifest, static)
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# T-D6.02-09: validate_forward — missing manifest entry (error)
# ---------------------------------------------------------------------------


class TestForwardMissingManifest:
    """T-D6.02-09: Error when MDX references chart not in manifest."""

    def test_missing_manifest_entry(self, tmp_path: Path) -> None:
        static = tmp_path / "static"
        _touch_chart_file(static, "img/bar_missing.svg")
        refs = [
            ChartReference(
                source_file=Path("page.mdx"),
                image_path="/img/bar_missing.svg",
                filename="bar_missing.svg",
                line_number=10,
            )
        ]
        issues = validate_forward(refs, {}, static)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) >= 1
        assert "bar_missing.svg" in errors[0].message
        assert "no manifest entry" in errors[0].message


# ---------------------------------------------------------------------------
# T-D6.02-10: validate_forward — missing file on disk (error)
# ---------------------------------------------------------------------------


class TestForwardMissingFile:
    """T-D6.02-10: Error when chart file does not exist on disk."""

    def test_missing_file_on_disk(self, tmp_path: Path) -> None:
        static = tmp_path / "static"
        static.mkdir(parents=True)
        manifest = {
            "radar_ghost.svg": ChartEntry(
                key="radar_ghost",
                filename="radar_ghost.svg",
                chart_type="radar",
                title="Ghost",
            )
        }
        refs = [
            ChartReference(
                source_file=Path("page.mdx"),
                image_path="/img/radar_ghost.svg",
                filename="radar_ghost.svg",
                line_number=3,
            )
        ]
        issues = validate_forward(refs, manifest, static)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) >= 1
        assert "not found on disk" in errors[0].message


# ---------------------------------------------------------------------------
# T-D6.02-11: validate_reverse — all entries referenced
# ---------------------------------------------------------------------------


class TestReverseAllReferenced:
    """T-D6.02-11: No warnings when all manifest entries are in MDX."""

    def test_all_referenced(self) -> None:
        manifest = {
            "radar_scores.svg": ChartEntry(
                key="r1", filename="radar_scores.svg", chart_type="radar", title="T"
            )
        }
        refs = [
            ChartReference(
                source_file=Path("p.mdx"),
                image_path="/img/radar_scores.svg",
                filename="radar_scores.svg",
                line_number=1,
            )
        ]
        issues = validate_reverse(manifest, refs)
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# T-D6.02-12: validate_reverse — orphaned manifest entry (warning)
# ---------------------------------------------------------------------------


class TestReverseOrphaned:
    """T-D6.02-12: Warning for manifest entries not referenced by MDX."""

    def test_orphaned_entry(self) -> None:
        manifest = {
            "radar_orphan.svg": ChartEntry(
                key="orphan", filename="radar_orphan.svg", chart_type="radar", title="O"
            )
        }
        issues = validate_reverse(manifest, [])
        assert len(issues) == 1
        assert issues[0].severity == Severity.WARNING
        assert "not referenced" in issues[0].message


# ---------------------------------------------------------------------------
# T-D6.02-13: validate_chart_manifest end-to-end — clean pass
# ---------------------------------------------------------------------------


class TestE2ECleanPass:
    """T-D6.02-13: Full validation with everything consistent."""

    def test_clean_pass(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        static = tmp_path / "static"
        manifest_path = static / "img" / "chart-manifest.json"

        _write_manifest(
            manifest_path,
            [_make_chart_entry("radar_overall", "radar", "overall_scores", "Overall")],
        )
        _touch_chart_file(static, "img/radar_overall_scores.svg")
        _touch_chart_file(static, "img/radar_overall_scores.png")
        _write_mdx(
            docs,
            "results.mdx",
            (
                "# Results\n"
                "![Radar](/img/radar_overall_scores.svg)\n"
                '<img src="/img/radar_overall_scores.png" />\n'
            ),
        )

        report = validate_chart_manifest(docs, static, manifest_path)
        assert report.passed is True
        assert report.forward_checked == 2
        assert report.reverse_checked == 2  # svg + png entries
        assert len(report.errors) == 0
        assert len(report.warnings) == 0


# ---------------------------------------------------------------------------
# T-D6.02-14: validate_chart_manifest end-to-end — mixed errors and warnings
# ---------------------------------------------------------------------------


class TestE2EMixed:
    """T-D6.02-14: Errors and warnings together."""

    def test_mixed_issues(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        static = tmp_path / "static"
        manifest_path = static / "img" / "chart-manifest.json"

        # Manifest has radar_overall (svg+png) and bar_orphan (svg+png)
        _write_manifest(
            manifest_path,
            [
                _make_chart_entry(
                    "radar_overall", "radar", "overall_scores", "Overall"
                ),
                _make_chart_entry("bar_orphan", "bar", "orphan_data", "Orphan"),
            ],
        )
        # Only radar svg exists on disk
        _touch_chart_file(static, "img/radar_overall_scores.svg")

        # MDX references radar svg (ok) and radar png (missing on disk)
        _write_mdx(
            docs,
            "results.mdx",
            (
                "![Radar](/img/radar_overall_scores.svg)\n"
                "![Radar PNG](/img/radar_overall_scores.png)\n"
            ),
        )

        report = validate_chart_manifest(docs, static, manifest_path)
        assert report.passed is False
        # radar png missing on disk = error
        assert len(report.errors) >= 1
        # bar_orphan svg+png not referenced = warnings
        assert len(report.warnings) >= 1


# ---------------------------------------------------------------------------
# T-D6.02-15: ManifestValidationReport.summary() output
# ---------------------------------------------------------------------------


class TestReportSummary:
    """T-D6.02-15: summary() returns human-readable text."""

    def test_summary_pass(self) -> None:
        report = ManifestValidationReport(
            forward_checked=3, reverse_checked=2, issues=[]
        )
        s = report.summary()
        assert "PASS" in s
        assert "Forward references checked: 3" in s
        assert "Reverse manifest entries checked: 2" in s

    def test_summary_fail(self) -> None:
        report = ManifestValidationReport(
            forward_checked=1,
            reverse_checked=1,
            issues=[
                ManifestIssue(
                    severity=Severity.ERROR,
                    message="test error",
                    source_file=None,
                    chart_key=None,
                    filename=None,
                ),
                ManifestIssue(
                    severity=Severity.WARNING,
                    message="test warning",
                    source_file=None,
                    chart_key=None,
                    filename=None,
                ),
            ],
        )
        s = report.summary()
        assert "FAIL" in s
        assert "Errors: 1" in s
        assert "Warnings: 1" in s


# ---------------------------------------------------------------------------
# T-D6.02-16: CLI exit codes
# ---------------------------------------------------------------------------


class TestCLIExitCodes:
    """T-D6.02-16: CLI returns correct exit codes."""

    def test_exit_0_on_pass(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        static = tmp_path / "static"
        manifest_path = static / "img" / "chart-manifest.json"
        _write_manifest(manifest_path, [])
        docs.mkdir(parents=True)

        rc = main(
            [
                "--docs-dir",
                str(docs),
                "--static-dir",
                str(static),
                "--manifest",
                str(manifest_path),
            ]
        )
        assert rc == 0

    def test_exit_1_on_errors(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        static = tmp_path / "static"
        manifest_path = static / "img" / "chart-manifest.json"
        _write_manifest(
            manifest_path,
            [_make_chart_entry("radar_overall", "radar", "overall_scores", "Overall")],
        )
        # MDX references a chart whose file is missing on disk
        _write_mdx(docs, "page.mdx", "![Chart](/img/radar_overall_scores.svg)\n")
        # Don't create the actual file on disk

        rc = main(
            [
                "--docs-dir",
                str(docs),
                "--static-dir",
                str(static),
                "--manifest",
                str(manifest_path),
            ]
        )
        assert rc == 1

    def test_exit_2_on_missing_manifest(self, tmp_path: Path) -> None:
        rc = main(
            [
                "--docs-dir",
                str(tmp_path),
                "--static-dir",
                str(tmp_path),
                "--manifest",
                str(tmp_path / "nonexistent.json"),
            ]
        )
        assert rc == 2

    def test_exit_2_on_invalid_json(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{broken")
        rc = main(
            [
                "--docs-dir",
                str(tmp_path),
                "--static-dir",
                str(tmp_path),
                "--manifest",
                str(bad),
            ]
        )
        assert rc == 2
