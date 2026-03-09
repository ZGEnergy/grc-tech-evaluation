"""Manifest I/O module for FNM source file management.

Provides typed data structures and functions for loading, validating, and updating
the FNM manifest that enumerates all expected source files (PSS/E RAW + supplemental CSVs).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class SourceFileType(Enum):
    """Type of FNM source file."""

    PSSE_RAW = "psse_raw"
    SUPPLEMENTAL_CSV = "supplemental_csv"


@dataclass(frozen=True)
class SourceFileEntry:
    """A single expected FNM source file entry in the manifest.

    Attributes:
        file_name: Base filename of the source file.
        file_type: Whether this is a PSS/E RAW file or a supplemental CSV.
        description: Human-readable description of the file's contents.
        sha256: SHA-256 checksum of the file, or None if not yet computed.
        required: Whether this file is required for a valid FNM dataset.
    """

    file_name: str
    file_type: SourceFileType
    description: str
    sha256: str | None = None
    required: bool = True


@dataclass(frozen=True)
class FnmManifest:
    """Machine-readable manifest of all expected FNM source files.

    Attributes:
        version: Manifest schema version string.
        variant: FNM variant identifier (e.g. "FNM_ANNUAL_S01").
        source_files: List of expected source file entries.
        notes: Optional free-text notes about this manifest.
    """

    version: str
    variant: str
    source_files: list[SourceFileEntry]
    notes: str = ""


@dataclass(frozen=True)
class ManifestValidationResult:
    """Result of validating a manifest against files on disk.

    Attributes:
        manifest_path: Path to the manifest JSON file.
        fnm_path: Path to the directory containing FNM source files.
        found: List of filenames that were found on disk.
        missing: List of filenames that were expected but not found.
        checksum_mismatches: List of filenames with SHA-256 mismatches.
        is_valid: True if all required files are present and checksums match.
    """

    manifest_path: Path
    fnm_path: Path
    found: list[str]
    missing: list[str]
    checksum_mismatches: list[str]
    is_valid: bool


FNM_ROOT = Path("data/fnm")
FNM_SUBDIRS: list[str] = ["intermediate", "reference", "docs", "scripts"]

GITIGNORE_BLOCKED_PATTERNS: list[str] = [
    "*.raw",
    "*.RAW",
    "*.csv",
    "*.CSV",
    "*.parquet",
    "*.m",
    "intermediate/**",
    "reference/**",
]

GITIGNORE_ALLOWED_PATTERNS: list[str] = [
    "!manifest.json",
    "!README.md",
    "!**/README.md",
    "!scripts/**/*.py",
    "!docs/**/*.md",
    "!docs/**/*.json",
    "!.gitignore",
]


def _source_file_entry_to_dict(entry: SourceFileEntry) -> dict:
    """Convert a SourceFileEntry to a JSON-serializable dict."""
    return {
        "file_name": entry.file_name,
        "file_type": entry.file_type.value,
        "description": entry.description,
        "sha256": entry.sha256,
        "required": entry.required,
    }


def _dict_to_source_file_entry(d: dict) -> SourceFileEntry:
    """Convert a dict to a SourceFileEntry."""
    return SourceFileEntry(
        file_name=d["file_name"],
        file_type=SourceFileType(d["file_type"]),
        description=d["description"],
        sha256=d.get("sha256"),
        required=d.get("required", True),
    )


def build_default_manifest() -> FnmManifest:
    """Build the default FNM manifest with all expected source files.

    Returns:
        An FnmManifest with entries for the PSS/E RAW file and 7 supplemental CSVs,
        all with placeholder (None) SHA-256 checksums.
    """
    source_files = [
        SourceFileEntry(
            file_name="FNM_ANNUAL_S01.raw",
            file_type=SourceFileType.PSSE_RAW,
            description="PSS/E v31 RAW file containing the full network model",
        ),
        SourceFileEntry(
            file_name="bus_names.csv",
            file_type=SourceFileType.SUPPLEMENTAL_CSV,
            description="Bus name mapping with station and voltage level metadata",
        ),
        SourceFileEntry(
            file_name="branch_ratings.csv",
            file_type=SourceFileType.SUPPLEMENTAL_CSV,
            description="Branch thermal rating overrides and seasonal limits",
        ),
        SourceFileEntry(
            file_name="generator_costs.csv",
            file_type=SourceFileType.SUPPLEMENTAL_CSV,
            description="Generator cost curves and fuel type classifications",
        ),
        SourceFileEntry(
            file_name="load_distribution.csv",
            file_type=SourceFileType.SUPPLEMENTAL_CSV,
            description="Load distribution factors by weather zone and bus",
        ),
        SourceFileEntry(
            file_name="transformer_taps.csv",
            file_type=SourceFileType.SUPPLEMENTAL_CSV,
            description="Transformer tap position settings and regulation bands",
        ),
        SourceFileEntry(
            file_name="shunt_switching.csv",
            file_type=SourceFileType.SUPPLEMENTAL_CSV,
            description="Switched shunt device status and control parameters",
        ),
        SourceFileEntry(
            file_name="contingency_definitions.csv",
            file_type=SourceFileType.SUPPLEMENTAL_CSV,
            description="Contingency definitions for N-1 and N-2 analysis",
        ),
    ]
    return FnmManifest(
        version="1.0",
        variant="FNM_ANNUAL_S01",
        source_files=source_files,
        notes="Default manifest for FNM ingestion. SHA-256 checksums are populated "
        "after first successful parse via update_manifest_checksums().",
    )


def load_manifest(manifest_path: Path) -> FnmManifest:
    """Load an FNM manifest from a JSON file.

    Args:
        manifest_path: Path to the manifest JSON file.

    Returns:
        The deserialized FnmManifest.

    Raises:
        FileNotFoundError: If manifest_path does not exist.
        ValueError: If the JSON is malformed or missing required fields.
    """
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    try:
        text = manifest_path.read_text(encoding="utf-8")
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON in manifest: {e}") from e

    try:
        source_files = [_dict_to_source_file_entry(sf) for sf in data["source_files"]]
        return FnmManifest(
            version=data["version"],
            variant=data["variant"],
            source_files=source_files,
            notes=data.get("notes", ""),
        )
    except (KeyError, TypeError) as e:
        raise ValueError(f"Invalid manifest structure: {e}") from e


def save_manifest(manifest: FnmManifest, manifest_path: Path) -> None:
    """Save an FNM manifest to a JSON file.

    Args:
        manifest: The manifest to serialize.
        manifest_path: Destination path for the JSON file.
    """
    data = {
        "version": manifest.version,
        "variant": manifest.variant,
        "source_files": [_source_file_entry_to_dict(sf) for sf in manifest.source_files],
        "notes": manifest.notes,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def validate_manifest_against_disk(
    manifest: FnmManifest,
    fnm_path: Path,
    *,
    verify_checksums: bool = False,
) -> ManifestValidationResult:
    """Validate that all manifest source files exist on disk.

    Args:
        manifest: The manifest to validate.
        fnm_path: Directory containing the FNM source files.
        verify_checksums: If True, also verify SHA-256 checksums for files that have them.

    Returns:
        A ManifestValidationResult with found/missing/mismatch details.
    """
    found: list[str] = []
    missing: list[str] = []
    checksum_mismatches: list[str] = []

    for entry in manifest.source_files:
        file_path = fnm_path / entry.file_name
        if file_path.exists():
            found.append(entry.file_name)
            if verify_checksums and entry.sha256 is not None:
                actual = compute_file_sha256(file_path)
                if actual != entry.sha256:
                    checksum_mismatches.append(entry.file_name)
        else:
            if entry.required:
                missing.append(entry.file_name)

    is_valid = len(missing) == 0 and len(checksum_mismatches) == 0

    return ManifestValidationResult(
        manifest_path=Path("manifest.json"),
        fnm_path=fnm_path,
        found=found,
        missing=missing,
        checksum_mismatches=checksum_mismatches,
        is_valid=is_valid,
    )


def compute_file_sha256(file_path: Path) -> str:
    """Compute the SHA-256 hex digest of a file.

    Args:
        file_path: Path to the file to hash.

    Returns:
        Lowercase hex string of the SHA-256 digest.

    Raises:
        FileNotFoundError: If file_path does not exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def update_manifest_checksums(manifest: FnmManifest, fnm_path: Path) -> FnmManifest:
    """Compute and populate SHA-256 checksums for all source files found on disk.

    Files that do not exist on disk retain their current checksum value (typically None).

    Args:
        manifest: The manifest to update.
        fnm_path: Directory containing the FNM source files.

    Returns:
        A new FnmManifest with checksums populated for files that exist.
    """
    updated_files: list[SourceFileEntry] = []
    for entry in manifest.source_files:
        file_path = fnm_path / entry.file_name
        if file_path.exists():
            sha = compute_file_sha256(file_path)
            updated_files.append(
                SourceFileEntry(
                    file_name=entry.file_name,
                    file_type=entry.file_type,
                    description=entry.description,
                    sha256=sha,
                    required=entry.required,
                )
            )
        else:
            updated_files.append(entry)

    return FnmManifest(
        version=manifest.version,
        variant=manifest.variant,
        source_files=updated_files,
        notes=manifest.notes,
    )
