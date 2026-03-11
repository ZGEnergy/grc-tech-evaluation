"""Chart manifest validation for the Phase 1 Report Site.

Validates chart-manifest.json against files on disk, checks SVG/PNG file
format integrity, and provides the entry point for ``make charts-validate``.
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REPORT_DIR = SCRIPT_DIR.parent
DEFAULT_STATIC_DIR = REPORT_DIR / "static"
DEFAULT_MANIFEST_PATH = DEFAULT_STATIC_DIR / "img" / "chart-manifest.json"

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

# Chart files follow the naming convention {chart-type}_{subject}.{ext}
CHART_FILE_PATTERN_SUFFIXES = (".svg", ".png")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ManifestValidationResult:
    """Result of validating chart-manifest.json against files on disk."""

    valid: bool
    total_entries: int
    missing_files: list[str]
    extra_files: list[str]
    errors: list[str]


@dataclass(frozen=True)
class FileFormatValidation:
    """Result of validating the format of a single chart output file."""

    file_path: Path
    format: str
    valid: bool
    error: str | None


@dataclass(frozen=True)
class IntegrationTestExpectation:
    """Expected chart output for integration test assertions."""

    min_radar_charts: int = 7
    min_heatmap_charts: int = 1
    min_matrix_charts: int = 1
    min_scalability_charts: int = 0
    expected_formats: tuple[str, ...] = ("svg", "png")


@dataclass(frozen=True)
class ManifestSchema:
    """Expected schema for chart-manifest.json, used for validation."""

    required_top_level_key: str = "charts"
    required_entry_fields: tuple[str, ...] = (
        "id",
        "type",
        "subject",
        "files",
        "data_source",
        "title",
    )
    required_file_formats: tuple[str, ...] = ("svg", "png")


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------


def validate_manifest_schema(
    manifest_data: dict,
) -> list[str]:
    """Validate that manifest JSON conforms to the expected schema.

    Checks for the required top-level 'charts' key, and that each entry
    contains all required fields (id, type, subject, files, data_source,
    title). Checks that each entry's files dict contains 'svg' and 'png'
    keys.

    Args:
        manifest_data: Parsed JSON content of chart-manifest.json.

    Returns:
        A list of error strings. Empty list if schema is valid.
    """
    schema = ManifestSchema()
    errors: list[str] = []

    if schema.required_top_level_key not in manifest_data:
        errors.append(
            f"Missing required top-level key: '{schema.required_top_level_key}'"
        )
        return errors

    charts = manifest_data[schema.required_top_level_key]
    if not isinstance(charts, list):
        errors.append(f"'{schema.required_top_level_key}' must be a list")
        return errors

    for i, entry in enumerate(charts):
        if not isinstance(entry, dict):
            errors.append(f"Entry {i}: not a dict")
            continue
        for req_field in schema.required_entry_fields:
            if req_field not in entry:
                entry_id = entry.get("id", f"index-{i}")
                errors.append(
                    f"Entry '{entry_id}': missing required field '{req_field}'"
                )

        files = entry.get("files")
        if isinstance(files, dict):
            for fmt in schema.required_file_formats:
                if fmt not in files:
                    entry_id = entry.get("id", f"index-{i}")
                    errors.append(
                        f"Entry '{entry_id}': missing file format '{fmt}' in files"
                    )

    return errors


def _is_chart_file(filename: str) -> bool:
    """Return True if the filename matches the chart naming convention.

    Chart files follow ``{chart-type}_{subject}.{ext}`` where the type
    is one of radar, heatmap, matrix, line and the extension is svg or png.
    """
    if not any(filename.endswith(s) for s in CHART_FILE_PATTERN_SUFFIXES):
        return False
    # Must contain an underscore separating type from subject
    stem = filename.rsplit(".", 1)[0]
    return "_" in stem


def validate_manifest(
    manifest_path: Path,
    static_dir: Path,
) -> ManifestValidationResult:
    """Validate chart-manifest.json against files on disk.

    Reads the manifest, checks that it is valid JSON with the expected
    schema, and verifies that every referenced file path resolves to an
    existing file under static_dir.

    Also checks for "extra" files: chart image files in the output directory
    that are not referenced by the manifest.

    Args:
        manifest_path: Path to chart-manifest.json.
        static_dir: The report/static/ directory, used to resolve
            relative paths from the manifest.

    Returns:
        A ManifestValidationResult summarizing the validation.

    Raises:
        FileNotFoundError: If manifest_path does not exist.
    """
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    errors: list[str] = []
    try:
        with open(manifest_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return ManifestValidationResult(
            valid=False,
            total_entries=0,
            missing_files=[],
            extra_files=[],
            errors=[f"Invalid JSON: {e}"],
        )

    schema_errors = validate_manifest_schema(data)
    errors.extend(schema_errors)

    charts = data.get("charts", [])
    if not isinstance(charts, list):
        charts = []

    # Collect all manifest-referenced file paths (relative to static_dir)
    manifest_rel_paths: set[str] = set()
    missing_files: list[str] = []

    for entry in charts:
        if not isinstance(entry, dict):
            continue
        files = entry.get("files", {})
        if not isinstance(files, dict):
            continue
        for _fmt, rel_path in files.items():
            manifest_rel_paths.add(rel_path)
            full_path = static_dir / rel_path
            if not full_path.exists():
                missing_files.append(rel_path)

    # Check for extra chart files on disk not in manifest
    img_dir = static_dir / "img"
    extra_files: list[str] = []
    if img_dir.exists():
        for f in sorted(img_dir.iterdir()):
            if f.is_file() and _is_chart_file(f.name):
                rel = str(f.relative_to(static_dir))
                if rel not in manifest_rel_paths:
                    extra_files.append(rel)

    valid = not errors and not missing_files
    return ManifestValidationResult(
        valid=valid,
        total_entries=len(charts),
        missing_files=missing_files,
        extra_files=extra_files,
        errors=errors,
    )


def validate_svg_file(file_path: Path) -> FileFormatValidation:
    """Validate that a file is well-formed SVG (XML with <svg> root).

    Parses the file as XML and checks that the root element is <svg>
    (with or without namespace prefix).

    Args:
        file_path: Path to the SVG file.

    Returns:
        A FileFormatValidation indicating whether the file is valid SVG.
    """
    try:
        tree = ET.parse(file_path)  # noqa: S314
        root = tree.getroot()
        # Strip namespace if present: {http://www.w3.org/2000/svg}svg -> svg
        tag = root.tag
        if "}" in tag:
            tag = tag.split("}", 1)[1]
        if tag != "svg":
            return FileFormatValidation(
                file_path=file_path,
                format="svg",
                valid=False,
                error=f"Root element is '{root.tag}', expected 'svg'",
            )
        return FileFormatValidation(
            file_path=file_path,
            format="svg",
            valid=True,
            error=None,
        )
    except ET.ParseError as e:
        return FileFormatValidation(
            file_path=file_path,
            format="svg",
            valid=False,
            error=f"XML parse error: {e}",
        )
    except Exception as e:
        return FileFormatValidation(
            file_path=file_path,
            format="svg",
            valid=False,
            error=f"Unexpected error: {e}",
        )


def validate_png_file(file_path: Path) -> FileFormatValidation:
    """Validate that a file has a valid PNG header.

    Checks the first 8 bytes against the PNG magic number signature.

    Args:
        file_path: Path to the PNG file.

    Returns:
        A FileFormatValidation indicating whether the file is valid PNG.
    """
    try:
        with open(file_path, "rb") as f:
            header = f.read(8)
        if header == PNG_MAGIC:
            return FileFormatValidation(
                file_path=file_path,
                format="png",
                valid=True,
                error=None,
            )
        return FileFormatValidation(
            file_path=file_path,
            format="png",
            valid=False,
            error=(f"Invalid PNG header: got {header!r}, expected {PNG_MAGIC!r}"),
        )
    except Exception as e:
        return FileFormatValidation(
            file_path=file_path,
            format="png",
            valid=False,
            error=f"Error reading file: {e}",
        )


def validate_all_chart_files(
    manifest_path: Path,
    static_dir: Path,
) -> list[FileFormatValidation]:
    """Validate the format of every chart file referenced in the manifest.

    Reads the manifest, resolves each file path, and validates SVG files
    as well-formed XML and PNG files as having valid headers.

    Args:
        manifest_path: Path to chart-manifest.json.
        static_dir: The report/static/ directory.

    Returns:
        A list of FileFormatValidation results, one per file.
    """
    with open(manifest_path) as f:
        data = json.load(f)

    charts = data.get("charts", [])
    results: list[FileFormatValidation] = []

    for entry in charts:
        files = entry.get("files", {})
        for fmt, rel_path in files.items():
            full_path = static_dir / rel_path
            if not full_path.exists():
                results.append(
                    FileFormatValidation(
                        file_path=full_path,
                        format=fmt,
                        valid=False,
                        error=f"File not found: {full_path}",
                    )
                )
                continue

            if fmt == "svg":
                results.append(validate_svg_file(full_path))
            elif fmt == "png":
                results.append(validate_png_file(full_path))
            else:
                results.append(
                    FileFormatValidation(
                        file_path=full_path,
                        format=fmt,
                        valid=False,
                        error=f"Unknown format: {fmt}",
                    )
                )

    return results


def run_charts_validate(
    manifest_path: Path | None = None,
    static_dir: Path | None = None,
) -> bool:
    """Entry point for ``make charts-validate``.

    Runs manifest validation and file format validation, prints results
    to stdout, and returns True if all validations pass.

    Args:
        manifest_path: Path to chart-manifest.json. Defaults to
            report/static/img/chart-manifest.json.
        static_dir: Path to report/static/. Defaults to report/static/.

    Returns:
        True if all validations pass, False otherwise.
    """
    manifest_path = manifest_path or DEFAULT_MANIFEST_PATH
    static_dir = static_dir or DEFAULT_STATIC_DIR

    print(f"Validating chart manifest: {manifest_path}")
    print(f"Static directory: {static_dir}\n")

    # 1. Manifest validation
    try:
        manifest_result = validate_manifest(manifest_path, static_dir)
    except FileNotFoundError as e:
        print(f"FAIL: {e}")
        return False

    print(f"Manifest entries: {manifest_result.total_entries}")

    if manifest_result.errors:
        print("\nSchema errors:")
        for err in manifest_result.errors:
            print(f"  - {err}")

    if manifest_result.missing_files:
        print("\nMissing files:")
        for mf in manifest_result.missing_files:
            print(f"  - {mf}")

    if manifest_result.extra_files:
        print("\nExtra files (not in manifest):")
        for ef in manifest_result.extra_files:
            print(f"  - {ef}")

    if manifest_result.valid:
        print("\nManifest validation: PASS")
    else:
        print("\nManifest validation: FAIL")

    # 2. File format validation
    print("\nValidating file formats...")
    file_results = validate_all_chart_files(manifest_path, static_dir)
    invalid_files = [r for r in file_results if not r.valid]

    if invalid_files:
        print(f"\n{len(invalid_files)} file(s) with invalid format:")
        for r in invalid_files:
            print(f"  - {r.file_path}: {r.error}")
    else:
        print(f"All {len(file_results)} files have valid format.")

    all_pass = manifest_result.valid and not invalid_files
    print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")
    return all_pass


def main() -> int:
    """CLI entry point. Returns 0 on success, 1 on failure."""
    success = run_charts_validate()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
