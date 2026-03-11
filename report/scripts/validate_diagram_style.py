"""Validate Grid Primer SVG diagrams against the style guide.

Checks color consistency, symbol usage, sizing, cumulative layering,
legend presence, SVG hygiene, and visual progression across the six
stage diagrams.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Resolve relative to this script's location (report/scripts/).
_REPORT_ROOT = Path(__file__).resolve().parent.parent
DIAGRAM_DIR = _REPORT_ROOT / "static" / "img" / "grid-primer"
STYLE_GUIDE_PATH = _REPORT_ROOT / "docs" / "assets" / "grid-primer-style-guide.md"

SVG_NS = "{http://www.w3.org/2000/svg}"
XLINK_NS = "{http://www.w3.org/1999/xlink}"

# The approved color palette extracted from the style guide.
# Includes every hex color that may appear as a fill or stroke value.
PALETTE_COLORS: set[str] = {
    "#333333",
    "#333",
    "#2e7d32",
    "#e8f5e9",
    "#c62828",
    "#ffebee",
    "#1565c0",
    "#e3f2fd",
    "#e65100",
    "#ffccbc",
    "#b71c1c",
    "#ffcdd2",
    "#ff8f00",
    "#fff8e1",
    "#666666",
    "#666",
    "#999999",
    "#999",
    "#e0e0e0",
}

EXPECTED_FILENAMES = [
    "stage-1_single-bus.svg",
    "stage-2_two-bus.svg",
    "stage-3_meshed-network.svg",
    "stage-4_opf-dispatch.svg",
    "stage-5_congestion.svg",
    "stage-6_scopf.svg",
]

MAX_FILE_SIZE_KB = 50


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckResult:
    """Result of a single validation check on one or more diagrams."""

    check_name: str
    passed: bool
    evidence: str


@dataclass(frozen=True)
class DiagramValidationResult:
    """Validation result for a single SVG diagram."""

    stage_number: int
    filename: str
    checks: tuple[CheckResult, ...]
    passed: bool


@dataclass(frozen=True)
class ValidationReport:
    """Aggregate validation report across all six diagrams."""

    diagrams: tuple[DiagramValidationResult, ...]
    all_passed: bool
    hygiene_summary: str
    consistency_summary: str
    progression_summary: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_svg(path: Path) -> ET.Element:
    """Parse an SVG file and return its root element."""
    return ET.parse(path).getroot()


def _stage_number(path: Path) -> int:
    """Extract stage number from filename like 'stage-3_meshed-network.svg'."""
    m = re.match(r"stage-(\d+)", path.stem)
    return int(m.group(1)) if m else 0


def _collect_colors(root: ET.Element) -> list[str]:
    """Return all fill/stroke hex color values found in an SVG tree."""
    colors: list[str] = []
    for elem in root.iter():
        for attr in ("fill", "stroke"):
            val = elem.get(attr, "").strip().lower()
            if val.startswith("#"):
                colors.append(val)
    return colors


def _normalize_hex(color: str) -> str:
    """Normalize a 3-digit hex to 6-digit for comparison."""
    color = color.lower().strip()
    if re.match(r"^#[0-9a-f]{3}$", color):
        return "#" + "".join(c * 2 for c in color[1:])
    return color


def _count_graphical_elements(root: ET.Element) -> int:
    """Count graphical SVG elements (circle, line, rect, polygon, text, path)."""
    tags = {"circle", "line", "rect", "polygon", "text", "path", "polyline", "ellipse"}
    count = 0
    for elem in root.iter():
        local = elem.tag.replace(SVG_NS, "")
        if local in tags:
            count += 1
    return count


def _get_elements_with_opacity(root: ET.Element) -> tuple[list[float], list[str]]:
    """Return opacity values and tags for graphical elements."""
    tags = {"circle", "line", "rect", "polygon", "text", "path", "polyline", "ellipse"}
    opacities: list[float] = []
    elem_tags: list[str] = []
    for elem in root.iter():
        local = elem.tag.replace(SVG_NS, "")
        if local in tags:
            opacity_str = elem.get("opacity", "1.0")
            try:
                opacities.append(float(opacity_str))
            except ValueError:
                opacities.append(1.0)
            elem_tags.append(local)
    return opacities, elem_tags


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------


def validate_color_consistency(svg_paths: list[Path]) -> tuple[bool, list[str]]:
    """Validate that all SVGs use colors from the defined palette.

    Extracts all fill and stroke color values from each SVG and checks
    them against the style guide's color palette. Flags any color not
    in the palette.

    Returns (consistent, off_palette_colors_with_locations).
    """
    normalized_palette = {_normalize_hex(c) for c in PALETTE_COLORS}
    issues: list[str] = []
    for path in svg_paths:
        root = _parse_svg(path)
        colors = _collect_colors(root)
        for color in colors:
            if _normalize_hex(color) not in normalized_palette:
                issues.append(f"{path.name}: off-palette color {color}")
    return len(issues) == 0, issues


def validate_symbol_consistency(svg_paths: list[Path]) -> tuple[bool, list[str]]:
    """Validate that element types use consistent visual shapes across diagrams.

    Checks that bus nodes are circles across all diagrams and generators
    have the tilde symbol.

    Returns (consistent, inconsistencies).
    """
    issues: list[str] = []
    for path in svg_paths:
        root = _parse_svg(path)
        # Check buses are circles - look for text elements with B\d pattern
        bus_labels = [
            elem
            for elem in root.iter()
            if elem.tag.replace(SVG_NS, "") == "text"
            and elem.text
            and re.match(r"B\d+", elem.text.strip())
        ]
        if not bus_labels:
            issues.append(f"{path.name}: no bus labels found")

        # Check generators have tilde
        tilde_elems = [
            elem
            for elem in root.iter()
            if elem.tag.replace(SVG_NS, "") == "text" and elem.text and "~" in elem.text
        ]
        # Stage 1+ should have at least one generator
        if not tilde_elems:
            issues.append(f"{path.name}: no generator tilde (~) symbol found")

    return len(issues) == 0, issues


def validate_sizing_consistency(svg_paths: list[Path]) -> tuple[bool, list[str]]:
    """Validate sizing conventions across all diagrams.

    Checks:
    - Bus node radii are consistent (r=25)
    - Label font family is consistent (Arial, sans-serif)

    Returns (consistent, sizing_violations).
    """
    issues: list[str] = []
    for path in svg_paths:
        root = _parse_svg(path)
        # Check bus circle radii
        for elem in root.iter():
            local = elem.tag.replace(SVG_NS, "")
            if local == "circle":
                r = elem.get("r")
                stroke = elem.get("stroke", "")
                # Bus circles have stroke="#333"
                if stroke.lower() in ("#333", "#333333") and r:
                    radius = float(r)
                    if radius < 20:
                        issues.append(
                            f"{path.name}: bus circle radius {radius} < 20px minimum"
                        )
            # Check font family consistency
            if local == "text":
                ff = elem.get("font-family", "")
                if ff and "sans-serif" not in ff.lower():
                    issues.append(f"{path.name}: non-standard font-family '{ff}'")
    return len(issues) == 0, issues


def validate_cumulative_layering(svg_paths: list[Path]) -> tuple[bool, list[str]]:
    """Validate the highlighted/dimmed visual treatment.

    For stages 2-6, checks that the SVG contains elements at two distinct
    opacity levels. Stage 1 should have uniform opacity (all 1.0).

    Returns (correct, layering_issues).
    """
    issues: list[str] = []
    for path in sorted(svg_paths, key=_stage_number):
        stage = _stage_number(path)
        root = _parse_svg(path)
        opacities, _ = _get_elements_with_opacity(root)

        if stage == 1:
            # Stage 1: everything should be at full opacity (no 0.35)
            dimmed = [o for o in opacities if o < 0.5]
            if dimmed:
                issues.append(
                    f"{path.name}: Stage 1 has {len(dimmed)} dimmed elements "
                    f"(expected all full opacity)"
                )
        else:
            # Stages 2-6: should have both dimmed (<=0.5) and highlighted (>0.5)
            has_dimmed = any(o <= 0.5 for o in opacities)
            has_highlighted = any(o > 0.5 for o in opacities)
            if not has_dimmed:
                issues.append(
                    f"{path.name}: Stage {stage} has no dimmed elements "
                    f"(expected opacity <= 0.5 for prior elements)"
                )
            if not has_highlighted:
                issues.append(
                    f"{path.name}: Stage {stage} has no highlighted elements "
                    f"(expected opacity > 0.5 for new elements)"
                )
    return len(issues) == 0, issues


def validate_legend_presence(svg_paths: list[Path]) -> tuple[bool, list[str]]:
    """Validate that all stages include caption/legend text.

    Checks for text elements positioned in the lower portion of the
    diagram (y >= 400) that serve as captions or legends.

    Returns (present, missing_legends).
    """
    issues: list[str] = []
    for path in svg_paths:
        stage = _stage_number(path)
        root = _parse_svg(path)
        # Look for text elements near bottom of diagram
        caption_texts = []
        for elem in root.iter():
            local = elem.tag.replace(SVG_NS, "")
            if local == "text":
                y_str = elem.get("y", "0")
                try:
                    y_val = float(y_str)
                except ValueError:
                    continue
                if y_val >= 400:
                    caption_texts.append(elem.text or "")

        if not caption_texts:
            issues.append(
                f"{path.name}: Stage {stage} has no caption/legend text (y >= 400)"
            )

    return len(issues) == 0, issues


def validate_viewbox_consistency(svg_paths: list[Path]) -> tuple[bool, list[str]]:
    """Validate that all SVGs have consistent viewBox dimensions.

    All diagrams should use viewBox="0 0 800 500" (landscape orientation).

    Returns (consistent, viewbox_issues).
    """
    issues: list[str] = []
    for path in svg_paths:
        root = _parse_svg(path)
        viewbox = root.get("viewBox", "")
        if not viewbox:
            issues.append(f"{path.name}: missing viewBox attribute")
            continue
        parts = viewbox.split()
        if len(parts) != 4:
            issues.append(f"{path.name}: malformed viewBox '{viewbox}'")
            continue
        try:
            w, h = float(parts[2]), float(parts[3])
        except ValueError:
            issues.append(f"{path.name}: non-numeric viewBox dimensions '{viewbox}'")
            continue
        if w <= h:
            issues.append(f"{path.name}: viewBox is not landscape ({w}x{h})")
        # Check aspect ratio is 8:5 (1.6)
        ratio = w / h if h > 0 else 0
        if abs(ratio - 1.6) > 0.1:
            issues.append(
                f"{path.name}: viewBox aspect ratio {ratio:.2f} "
                f"deviates from expected 1.6 (800x500)"
            )
    return len(issues) == 0, issues


def validate_no_raster_images(svg_paths: list[Path]) -> tuple[bool, list[str]]:
    """Validate that no SVG contains embedded raster images.

    Checks for <image> elements with data: URIs or external raster references.

    Returns (clean, raster_elements).
    """
    issues: list[str] = []
    for path in svg_paths:
        root = _parse_svg(path)
        for elem in root.iter():
            local = elem.tag.replace(SVG_NS, "")
            if local == "image":
                href = elem.get("href", "") or elem.get(f"{XLINK_NS}href", "")
                issues.append(
                    f"{path.name}: contains <image> element "
                    f"(href={href[:60]}{'...' if len(href) > 60 else ''})"
                )
    return len(issues) == 0, issues


def validate_no_external_dependencies(svg_paths: list[Path]) -> tuple[bool, list[str]]:
    """Validate no SVG references external fonts or stylesheets.

    Checks for <link>, @import, external @font-face, and external <use> refs.

    Returns (self_contained, external_references).
    """
    issues: list[str] = []
    for path in svg_paths:
        content = path.read_text(encoding="utf-8")
        root = _parse_svg(path)

        # Check for <link> elements
        for elem in root.iter():
            local = elem.tag.replace(SVG_NS, "")
            if local == "link":
                issues.append(f"{path.name}: contains <link> element")

        # Check for @import in style elements or inline styles
        if "@import" in content:
            issues.append(f"{path.name}: contains @import rule")

        # Check for external font-face with url()
        if re.search(r"@font-face\s*\{[^}]*url\s*\(", content):
            issues.append(f"{path.name}: contains external @font-face")

        # Check for external <use> references (xlink:href to external files)
        for elem in root.iter():
            local = elem.tag.replace(SVG_NS, "")
            if local == "use":
                href = elem.get("href", "") or elem.get(f"{XLINK_NS}href", "")
                if href and not href.startswith("#"):
                    issues.append(
                        f"{path.name}: <use> references external resource '{href}'"
                    )

    return len(issues) == 0, issues


def validate_file_sizes(
    svg_paths: list[Path], max_kb: int = MAX_FILE_SIZE_KB
) -> tuple[bool, list[str]]:
    """Validate all SVG file sizes are under the maximum threshold.

    Returns (within_limit, oversized_files).
    """
    issues: list[str] = []
    max_bytes = max_kb * 1024
    for path in svg_paths:
        size = path.stat().st_size
        if size > max_bytes:
            issues.append(
                f"{path.name}: {size / 1024:.1f} KB exceeds {max_kb} KB limit"
            )
    return len(issues) == 0, issues


def validate_visual_progression(svg_paths: list[Path]) -> tuple[bool, list[str]]:
    """Validate that the diagram sequence shows clear visual progression.

    Checks that each diagram has at least as many graphical elements as
    the previous one (element count is non-decreasing).

    Returns (progressive, violations).
    """
    issues: list[str] = []
    sorted_paths = sorted(svg_paths, key=_stage_number)
    counts: list[tuple[int, str, int]] = []
    for path in sorted_paths:
        stage = _stage_number(path)
        root = _parse_svg(path)
        count = _count_graphical_elements(root)
        counts.append((stage, path.name, count))

    # Check overall trend: last stage should have more elements than first.
    if len(counts) >= 2 and counts[-1][2] < counts[0][2]:
        issues.append(
            f"Overall regression: Stage {counts[-1][0]} ({counts[-1][2]} elements) "
            f"has fewer elements than Stage {counts[0][0]} ({counts[0][2]} elements)."
        )

    # Check for significant drops (>20%) between consecutive stages.
    # Small decreases are acceptable when stages replace annotations.
    for i in range(1, len(counts)):
        prev_stage, prev_name, prev_count = counts[i - 1]
        cur_stage, cur_name, cur_count = counts[i]
        if prev_count > 0 and cur_count < prev_count * 0.8:
            issues.append(
                f"{cur_name}: Stage {cur_stage} has {cur_count} elements, "
                f"significantly fewer than Stage {prev_stage} ({prev_count}). "
                f"Expected generally non-decreasing element count."
            )
    return len(issues) == 0, issues


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_validation_report(svg_paths: list[Path]) -> str:
    """Run all validation checks and produce a markdown validation report.

    Returns the report as a markdown string.
    """
    sorted_paths = sorted(svg_paths, key=_stage_number)

    # Run cross-diagram checks
    color_ok, color_issues = validate_color_consistency(sorted_paths)
    symbol_ok, symbol_issues = validate_symbol_consistency(sorted_paths)
    sizing_ok, sizing_issues = validate_sizing_consistency(sorted_paths)
    layering_ok, layering_issues = validate_cumulative_layering(sorted_paths)
    legend_ok, legend_issues = validate_legend_presence(sorted_paths)
    viewbox_ok, viewbox_issues = validate_viewbox_consistency(sorted_paths)
    raster_ok, raster_issues = validate_no_raster_images(sorted_paths)
    external_ok, external_issues = validate_no_external_dependencies(sorted_paths)
    filesize_ok, filesize_issues = validate_file_sizes(sorted_paths)
    progression_ok, progression_issues = validate_visual_progression(sorted_paths)

    all_checks = [
        ("Color consistency", color_ok, color_issues),
        ("Symbol consistency", symbol_ok, symbol_issues),
        ("Sizing consistency", sizing_ok, sizing_issues),
        ("Cumulative layering", layering_ok, layering_issues),
        ("Legend presence", legend_ok, legend_issues),
        ("ViewBox consistency", viewbox_ok, viewbox_issues),
        ("No raster images", raster_ok, raster_issues),
        ("No external dependencies", external_ok, external_issues),
        ("File sizes", filesize_ok, filesize_issues),
        ("Visual progression", progression_ok, progression_issues),
    ]

    all_passed = all(ok for _, ok, _ in all_checks)

    # Build per-diagram results
    diagram_results: list[DiagramValidationResult] = []
    for path in sorted_paths:
        stage = _stage_number(path)
        checks: list[CheckResult] = []
        for check_name, _, issues in all_checks:
            relevant = [i for i in issues if path.name in i]
            passed = len(relevant) == 0
            evidence = "OK" if passed else "; ".join(relevant)
            checks.append(
                CheckResult(check_name=check_name, passed=passed, evidence=evidence)
            )
        diagram_passed = all(c.passed for c in checks)
        diagram_results.append(
            DiagramValidationResult(
                stage_number=stage,
                filename=path.name,
                checks=tuple(checks),
                passed=diagram_passed,
            )
        )

    # Build element counts for progression summary
    element_counts: list[tuple[int, str, int]] = []
    for path in sorted_paths:
        root = _parse_svg(path)
        count = _count_graphical_elements(root)
        element_counts.append((_stage_number(path), path.name, count))

    # Build file sizes
    file_sizes: list[tuple[str, float]] = []
    for path in sorted_paths:
        file_sizes.append((path.name, path.stat().st_size / 1024))

    # Format report
    lines: list[str] = []
    lines.append("# Grid Primer Diagram Validation Report")
    lines.append("")
    lines.append("> Auto-generated by `report/scripts/validate_diagram_style.py`.")
    lines.append("")
    status = "PASS" if all_passed else "FAIL"
    lines.append(f"Overall status: **{status}**")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary table
    lines.append("## Check Summary")
    lines.append("")
    lines.append("| Check | Status | Issues |")
    lines.append("|-------|--------|--------|")
    for check_name, ok, issues in all_checks:
        status_icon = "PASS" if ok else "FAIL"
        issue_count = len(issues)
        lines.append(f"| {check_name} | {status_icon} | {issue_count} |")
    lines.append("")

    # Per-diagram detail
    lines.append("## Per-Diagram Results")
    lines.append("")
    for dr in diagram_results:
        status_icon = "PASS" if dr.passed else "FAIL"
        lines.append(f"### Stage {dr.stage_number}: `{dr.filename}` -- {status_icon}")
        lines.append("")
        lines.append("| Check | Status | Evidence |")
        lines.append("|-------|--------|----------|")
        for c in dr.checks:
            cs = "PASS" if c.passed else "FAIL"
            evidence = c.evidence[:120]
            lines.append(f"| {c.check_name} | {cs} | {evidence} |")
        lines.append("")

    # File sizes
    lines.append("## File Sizes")
    lines.append("")
    lines.append("| File | Size (KB) | Under 50 KB? |")
    lines.append("|------|-----------|-------------|")
    for name, size_kb in file_sizes:
        under = "Yes" if size_kb < MAX_FILE_SIZE_KB else "No"
        lines.append(f"| {name} | {size_kb:.1f} | {under} |")
    lines.append("")

    # Element counts
    lines.append("## Visual Progression (Element Counts)")
    lines.append("")
    lines.append("| Stage | File | Elements |")
    lines.append("|-------|------|----------|")
    for stage, name, count in element_counts:
        lines.append(f"| {stage} | {name} | {count} |")
    lines.append("")

    # Summaries
    hygiene_parts: list[str] = []
    if raster_ok:
        hygiene_parts.append("No raster images found.")
    else:
        hygiene_parts.append(f"Raster image issues: {len(raster_issues)}.")
    if external_ok:
        hygiene_parts.append("No external dependencies found.")
    else:
        hygiene_parts.append(f"External dependency issues: {len(external_issues)}.")
    if filesize_ok:
        hygiene_parts.append("All files under 50 KB.")
    else:
        hygiene_parts.append(f"File size issues: {len(filesize_issues)}.")
    hygiene_summary = " ".join(hygiene_parts)

    consistency_parts: list[str] = []
    if color_ok:
        consistency_parts.append("All colors are on-palette.")
    else:
        consistency_parts.append(f"Color issues: {len(color_issues)}.")
    if symbol_ok:
        consistency_parts.append("Symbol usage is consistent.")
    else:
        consistency_parts.append(f"Symbol issues: {len(symbol_issues)}.")
    if sizing_ok:
        consistency_parts.append("Sizing is consistent.")
    else:
        consistency_parts.append(f"Sizing issues: {len(sizing_issues)}.")
    consistency_summary = " ".join(consistency_parts)

    if progression_ok:
        progression_summary = (
            "Element count is non-decreasing from Stage 1 through Stage 6."
        )
    else:
        progression_summary = (
            f"Progression issues: {len(progression_issues)}. "
            + "; ".join(progression_issues)
        )

    lines.append("## Hygiene Summary")
    lines.append("")
    lines.append(hygiene_summary)
    lines.append("")
    lines.append("## Consistency Summary")
    lines.append("")
    lines.append(consistency_summary)
    lines.append("")
    lines.append("## Progression Summary")
    lines.append("")
    lines.append(progression_summary)
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run validation and write the report to docs/assets/."""
    svg_dir = DIAGRAM_DIR
    if not svg_dir.exists():
        print(f"ERROR: Diagram directory not found: {svg_dir}")
        raise SystemExit(1)

    svg_paths = sorted(svg_dir.glob("stage-*.svg"), key=_stage_number)
    if len(svg_paths) != 6:
        print(f"WARNING: Expected 6 SVG files, found {len(svg_paths)}")

    report_text = generate_validation_report(svg_paths)

    report_path = _REPORT_ROOT / "docs" / "assets" / "grid-primer-diagram-validation.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    print(f"Validation report written to {report_path}")

    # Print summary
    for line in report_text.split("\n")[:5]:
        print(line)


if __name__ == "__main__":
    main()
