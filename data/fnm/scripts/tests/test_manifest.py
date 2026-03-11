"""Tests for FNM directory structure and manifest I/O."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from fnm.scripts.manifest_io import (
    FnmManifest,
    SourceFileEntry,
    SourceFileType,
    compute_file_sha256,
    load_manifest,
    save_manifest,
    update_manifest_checksums,
    validate_manifest_against_disk,
)

# Root of the data/fnm/ directory in the worktree
FNM_DIR = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Tests 1-8: Directory and file existence (reference actual worktree paths)
# ---------------------------------------------------------------------------


def test_fnm_root_directory_exists() -> None:
    """Test that the data/fnm/ directory exists."""
    assert FNM_DIR.is_dir(), f"Expected directory at {FNM_DIR}"


def test_fnm_subdirectories_exist() -> None:
    """Test that all four required subdirectories exist."""
    expected = ["intermediate", "reference", "docs", "scripts"]
    for subdir in expected:
        path = FNM_DIR / subdir
        assert path.is_dir(), f"Expected subdirectory at {path}"


def test_fnm_readme_exists_and_documents_layout() -> None:
    """Test that the top-level README exists and documents the directory layout."""
    readme = FNM_DIR / "README.md"
    assert readme.is_file(), f"Expected README at {readme}"
    content = readme.read_text(encoding="utf-8")
    # Should document key directories
    assert "intermediate" in content.lower()
    assert "reference" in content.lower()
    assert "docs" in content.lower()
    assert "scripts" in content.lower()
    # Should mention NDA restrictions
    assert "NDA" in content or "nda" in content
    # Should mention FNM_PATH
    assert "FNM_PATH" in content


def test_manifest_json_exists_and_is_valid() -> None:
    """Test that manifest.json exists and is valid JSON with required keys."""
    manifest_path = FNM_DIR / "manifest.json"
    assert manifest_path.is_file(), f"Expected manifest at {manifest_path}"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "version" in data
    assert "variant" in data
    assert "source_files" in data
    assert isinstance(data["source_files"], list)


def test_manifest_contains_all_expected_source_files() -> None:
    """Test that the manifest lists exactly 8 source files (1 RAW + 7 CSVs)."""
    manifest = load_manifest(FNM_DIR / "manifest.json")
    assert len(manifest.source_files) == 8
    file_names = [sf.file_name for sf in manifest.source_files]
    assert "FNM_ANNUAL_S01.raw" in file_names


def test_manifest_source_file_types_correct() -> None:
    """Test that the RAW file is typed as PSSE_RAW and CSVs as SUPPLEMENTAL_CSV."""
    manifest = load_manifest(FNM_DIR / "manifest.json")
    raw_files = [sf for sf in manifest.source_files if sf.file_type == SourceFileType.PSSE_RAW]
    csv_files = [
        sf for sf in manifest.source_files if sf.file_type == SourceFileType.SUPPLEMENTAL_CSV
    ]
    assert len(raw_files) == 1
    assert len(csv_files) == 7


def test_gitignore_blocks_fnm_data_files() -> None:
    """Test that .gitignore contains patterns to block data file extensions."""
    gitignore = FNM_DIR / ".gitignore"
    assert gitignore.is_file(), f"Expected .gitignore at {gitignore}"
    content = gitignore.read_text(encoding="utf-8")
    blocked = ["*.raw", "*.RAW", "*.csv", "*.CSV", "*.parquet", "*.m"]
    for pattern in blocked:
        assert pattern in content, f"Missing blocked pattern: {pattern}"
    # Should also block intermediate and reference dirs
    assert "intermediate/**" in content
    assert "reference/**" in content


def test_gitignore_allows_tracked_files() -> None:
    """Test that .gitignore has negation patterns for tracked infrastructure files."""
    gitignore = FNM_DIR / ".gitignore"
    content = gitignore.read_text(encoding="utf-8")
    allowed = ["!manifest.json", "!README.md", "!scripts/**/*.py", "!.gitignore"]
    for pattern in allowed:
        assert pattern in content, f"Missing allowed pattern: {pattern}"


# ---------------------------------------------------------------------------
# Tests 9-16: API tests (use tmp_path for isolation)
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_manifest() -> FnmManifest:
    """Build a small manifest for testing."""
    return FnmManifest(
        version="1.0",
        variant="test",
        source_files=[
            SourceFileEntry(
                file_name="test.raw",
                file_type=SourceFileType.PSSE_RAW,
                description="Test RAW file",
            ),
            SourceFileEntry(
                file_name="test.csv",
                file_type=SourceFileType.SUPPLEMENTAL_CSV,
                description="Test CSV file",
            ),
        ],
        notes="test manifest",
    )


def test_load_manifest_roundtrip(tmp_path: Path, sample_manifest: FnmManifest) -> None:
    """Test that save then load produces an identical manifest."""
    path = tmp_path / "manifest.json"
    save_manifest(sample_manifest, path)
    loaded = load_manifest(path)
    assert loaded.version == sample_manifest.version
    assert loaded.variant == sample_manifest.variant
    assert loaded.notes == sample_manifest.notes
    assert len(loaded.source_files) == len(sample_manifest.source_files)
    for orig, loaded_sf in zip(sample_manifest.source_files, loaded.source_files):
        assert orig.file_name == loaded_sf.file_name
        assert orig.file_type == loaded_sf.file_type
        assert orig.description == loaded_sf.description
        assert orig.sha256 == loaded_sf.sha256
        assert orig.required == loaded_sf.required


def test_load_manifest_raises_on_missing_file(tmp_path: Path) -> None:
    """Test that loading a nonexistent manifest raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_manifest(tmp_path / "nonexistent.json")


def test_load_manifest_raises_on_malformed_json(tmp_path: Path) -> None:
    """Test that loading malformed JSON raises ValueError."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{invalid json", encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed JSON"):
        load_manifest(bad_file)


def test_validate_manifest_all_files_present(tmp_path: Path, sample_manifest: FnmManifest) -> None:
    """Test validation passes when all required files are present."""
    for entry in sample_manifest.source_files:
        (tmp_path / entry.file_name).write_text("data", encoding="utf-8")

    result = validate_manifest_against_disk(sample_manifest, tmp_path)
    assert result.is_valid
    assert len(result.found) == 2
    assert len(result.missing) == 0
    assert len(result.checksum_mismatches) == 0


def test_validate_manifest_missing_files(tmp_path: Path, sample_manifest: FnmManifest) -> None:
    """Test validation fails when required files are missing."""
    # Create only the RAW file, not the CSV
    (tmp_path / "test.raw").write_text("data", encoding="utf-8")

    result = validate_manifest_against_disk(sample_manifest, tmp_path)
    assert not result.is_valid
    assert "test.csv" in result.missing
    assert "test.raw" in result.found


def test_validate_manifest_checksum_mismatch(
    tmp_path: Path,
) -> None:
    """Test validation detects SHA-256 checksum mismatches."""
    content = b"hello world"
    (tmp_path / "test.raw").write_bytes(content)

    wrong_hash = "0000000000000000000000000000000000000000000000000000000000000000"
    manifest = FnmManifest(
        version="1.0",
        variant="test",
        source_files=[
            SourceFileEntry(
                file_name="test.raw",
                file_type=SourceFileType.PSSE_RAW,
                description="Test file",
                sha256=wrong_hash,
            ),
        ],
    )

    result = validate_manifest_against_disk(manifest, tmp_path, verify_checksums=True)
    assert not result.is_valid
    assert "test.raw" in result.checksum_mismatches


def test_compute_file_sha256_deterministic(tmp_path: Path) -> None:
    """Test that compute_file_sha256 returns a deterministic, correct hash."""
    content = b"deterministic content for hashing"
    test_file = tmp_path / "hashme.txt"
    test_file.write_bytes(content)

    expected = hashlib.sha256(content).hexdigest()
    result = compute_file_sha256(test_file)
    assert result == expected

    # Calling again should return the same hash
    assert compute_file_sha256(test_file) == result


def test_update_manifest_checksums_populates_hashes(tmp_path: Path) -> None:
    """Test that update_manifest_checksums fills in SHA-256 for existing files."""
    raw_content = b"raw file content"
    csv_content = b"csv file content"
    (tmp_path / "test.raw").write_bytes(raw_content)
    (tmp_path / "test.csv").write_bytes(csv_content)

    manifest = FnmManifest(
        version="1.0",
        variant="test",
        source_files=[
            SourceFileEntry(
                file_name="test.raw",
                file_type=SourceFileType.PSSE_RAW,
                description="Test RAW",
            ),
            SourceFileEntry(
                file_name="test.csv",
                file_type=SourceFileType.SUPPLEMENTAL_CSV,
                description="Test CSV",
            ),
            SourceFileEntry(
                file_name="missing.csv",
                file_type=SourceFileType.SUPPLEMENTAL_CSV,
                description="Missing file",
            ),
        ],
    )

    updated = update_manifest_checksums(manifest, tmp_path)

    # Existing files should have checksums
    raw_entry = next(sf for sf in updated.source_files if sf.file_name == "test.raw")
    csv_entry = next(sf for sf in updated.source_files if sf.file_name == "test.csv")
    missing_entry = next(sf for sf in updated.source_files if sf.file_name == "missing.csv")

    assert raw_entry.sha256 == hashlib.sha256(raw_content).hexdigest()
    assert csv_entry.sha256 == hashlib.sha256(csv_content).hexdigest()
    assert missing_entry.sha256 is None
