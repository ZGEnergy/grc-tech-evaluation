"""Tests for Grid Primer diagram style guide and validation.

Maps to success criteria SC-01 through SC-16 from PRD-04.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Resolve paths relative to the report root (one level up from tests/).
REPORT_ROOT = Path(__file__).resolve().parent.parent
DIAGRAM_DIR = REPORT_ROOT / "static" / "img" / "grid-primer"
STYLE_GUIDE_PATH = REPORT_ROOT / "docs" / "assets" / "grid-primer-style-guide.md"
VALIDATION_REPORT_PATH = (
    REPORT_ROOT / "docs" / "assets" / "grid-primer-diagram-validation.md"
)

# Add scripts directory to path so we can import the validation module.
sys.path.insert(0, str(REPORT_ROOT / "scripts"))

from validate_diagram_style import (  # noqa: E402
    validate_color_consistency,
    validate_cumulative_layering,
    validate_file_sizes,
    validate_legend_presence,
    validate_no_external_dependencies,
    validate_no_raster_images,
    validate_sizing_consistency,
    validate_symbol_consistency,
    validate_viewbox_consistency,
    validate_visual_progression,
)


@pytest.fixture()
def svg_paths() -> list[Path]:
    """Return sorted list of the six stage SVG paths."""
    paths = sorted(DIAGRAM_DIR.glob("stage-*.svg"))
    assert len(paths) == 6, f"Expected 6 SVG files, found {len(paths)}"
    return paths


# ---------------------------------------------------------------------------
# SC-01: Style guide document exists
# ---------------------------------------------------------------------------


class TestSC01StyleGuideExists:
    def test_style_guide_file_exists(self) -> None:
        assert STYLE_GUIDE_PATH.exists(), f"Style guide not found at {STYLE_GUIDE_PATH}"

    def test_style_guide_is_nonempty(self) -> None:
        assert STYLE_GUIDE_PATH.stat().st_size > 0, "Style guide is empty"


# ---------------------------------------------------------------------------
# SC-02: Color palette defined with hex values
# ---------------------------------------------------------------------------


class TestSC02ColorPalette:
    def test_style_guide_defines_hex_colors(self) -> None:
        content = STYLE_GUIDE_PATH.read_text(encoding="utf-8")
        # Must contain at least the core element colors
        for color in ["#333333", "#2e7d32", "#c62828", "#1565c0", "#ff8f00"]:
            # Allow 3- or 6-digit variants
            short = "#" + color[1] + color[3] + color[5] if len(color) == 7 else color
            assert color in content or short in content, (
                f"Color {color} not found in style guide"
            )

    def test_style_guide_defines_congestion_color(self) -> None:
        content = STYLE_GUIDE_PATH.read_text(encoding="utf-8")
        assert "#e65100" in content, "Congestion color #e65100 not in style guide"

    def test_style_guide_defines_trip_color(self) -> None:
        content = STYLE_GUIDE_PATH.read_text(encoding="utf-8")
        assert "#b71c1c" in content, "Trip color #b71c1c not in style guide"


# ---------------------------------------------------------------------------
# SC-03: Symbol vocabulary defined
# ---------------------------------------------------------------------------


class TestSC03SymbolVocabulary:
    def test_style_guide_defines_symbols(self) -> None:
        content = STYLE_GUIDE_PATH.read_text(encoding="utf-8").lower()
        for keyword in ["bus", "generator", "load", "transmission line", "flow arrow"]:
            assert keyword in content, f"Symbol '{keyword}' not defined in style guide"

    def test_style_guide_defines_congestion_marker(self) -> None:
        content = STYLE_GUIDE_PATH.read_text(encoding="utf-8").lower()
        assert "congestion" in content, "Congestion marker not in style guide"

    def test_style_guide_defines_trip_marker(self) -> None:
        content = STYLE_GUIDE_PATH.read_text(encoding="utf-8").lower()
        assert "trip" in content, "Trip marker not in style guide"


# ---------------------------------------------------------------------------
# SC-04: Sizing conventions defined
# ---------------------------------------------------------------------------


class TestSC04SizingConventions:
    def test_style_guide_defines_sizing(self) -> None:
        content = STYLE_GUIDE_PATH.read_text(encoding="utf-8").lower()
        for keyword in ["radius", "stroke width", "font size", "font family"]:
            assert keyword in content, (
                f"Sizing convention '{keyword}' not in style guide"
            )


# ---------------------------------------------------------------------------
# SC-05: Cumulative layering rules defined
# ---------------------------------------------------------------------------


class TestSC05CumulativeLayering:
    def test_style_guide_defines_layering(self) -> None:
        content = STYLE_GUIDE_PATH.read_text(encoding="utf-8").lower()
        assert "opacity" in content, "Opacity not mentioned in style guide"
        assert "0.35" in content, "Dimmed opacity value 0.35 not in style guide"

    def test_style_guide_defines_stage1_treatment(self) -> None:
        content = STYLE_GUIDE_PATH.read_text(encoding="utf-8").lower()
        assert "stage 1" in content, "Stage 1 treatment not in style guide"


# ---------------------------------------------------------------------------
# SC-06: All SVGs use palette colors
# ---------------------------------------------------------------------------


class TestSC06PaletteColors:
    def test_all_svgs_use_palette_colors(self, svg_paths: list[Path]) -> None:
        ok, issues = validate_color_consistency(svg_paths)
        assert ok, "Off-palette colors found:\n" + "\n".join(issues)


# ---------------------------------------------------------------------------
# SC-07: Symbols consistent across diagrams
# ---------------------------------------------------------------------------


class TestSC07SymbolConsistency:
    def test_symbols_consistent_across_diagrams(self, svg_paths: list[Path]) -> None:
        ok, issues = validate_symbol_consistency(svg_paths)
        assert ok, "Symbol inconsistencies:\n" + "\n".join(issues)


# ---------------------------------------------------------------------------
# SC-08: Sizing consistent across diagrams
# ---------------------------------------------------------------------------


class TestSC08SizingConsistency:
    def test_sizing_consistent_across_diagrams(self, svg_paths: list[Path]) -> None:
        ok, issues = validate_sizing_consistency(svg_paths)
        assert ok, "Sizing violations:\n" + "\n".join(issues)


# ---------------------------------------------------------------------------
# SC-09: Cumulative layering applied correctly
# ---------------------------------------------------------------------------


class TestSC09LayeringApplied:
    def test_cumulative_layering_correct(self, svg_paths: list[Path]) -> None:
        ok, issues = validate_cumulative_layering(svg_paths)
        assert ok, "Layering issues:\n" + "\n".join(issues)


# ---------------------------------------------------------------------------
# SC-10: Legends present in stages 2-6
# ---------------------------------------------------------------------------


class TestSC10LegendPresence:
    def test_legends_present(self, svg_paths: list[Path]) -> None:
        ok, issues = validate_legend_presence(svg_paths)
        assert ok, "Legend issues:\n" + "\n".join(issues)


# ---------------------------------------------------------------------------
# SC-11: No raster images in any SVG
# ---------------------------------------------------------------------------


class TestSC11NoRasterImages:
    def test_no_raster_images(self, svg_paths: list[Path]) -> None:
        ok, issues = validate_no_raster_images(svg_paths)
        assert ok, "Raster images found:\n" + "\n".join(issues)


# ---------------------------------------------------------------------------
# SC-12: No external dependencies in any SVG
# ---------------------------------------------------------------------------


class TestSC12NoExternalDeps:
    def test_no_external_dependencies(self, svg_paths: list[Path]) -> None:
        ok, issues = validate_no_external_dependencies(svg_paths)
        assert ok, "External dependencies found:\n" + "\n".join(issues)


# ---------------------------------------------------------------------------
# SC-13: All file sizes under 50 KB
# ---------------------------------------------------------------------------


class TestSC13FileSizes:
    def test_all_files_under_50kb(self, svg_paths: list[Path]) -> None:
        ok, issues = validate_file_sizes(svg_paths)
        assert ok, "Oversized files:\n" + "\n".join(issues)


# ---------------------------------------------------------------------------
# SC-14: ViewBox aspect ratios consistent
# ---------------------------------------------------------------------------


class TestSC14ViewBox:
    def test_viewbox_consistent(self, svg_paths: list[Path]) -> None:
        ok, issues = validate_viewbox_consistency(svg_paths)
        assert ok, "ViewBox issues:\n" + "\n".join(issues)


# ---------------------------------------------------------------------------
# SC-15: Visual progression confirmed
# ---------------------------------------------------------------------------


class TestSC15VisualProgression:
    def test_visual_progression(self, svg_paths: list[Path]) -> None:
        ok, issues = validate_visual_progression(svg_paths)
        assert ok, "Progression issues:\n" + "\n".join(issues)


# ---------------------------------------------------------------------------
# SC-16: Validation report produced
# ---------------------------------------------------------------------------


class TestSC16ValidationReport:
    def test_validation_report_exists(self) -> None:
        assert VALIDATION_REPORT_PATH.exists(), (
            f"Validation report not found at {VALIDATION_REPORT_PATH}"
        )

    def test_validation_report_is_nonempty(self) -> None:
        assert VALIDATION_REPORT_PATH.stat().st_size > 0, "Validation report is empty"

    def test_validation_report_contains_check_results(self) -> None:
        content = VALIDATION_REPORT_PATH.read_text(encoding="utf-8")
        assert "Check Summary" in content, (
            "Validation report missing 'Check Summary' section"
        )
        assert "Per-Diagram Results" in content, (
            "Validation report missing 'Per-Diagram Results' section"
        )
