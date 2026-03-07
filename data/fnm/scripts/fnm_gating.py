"""FNM_PATH gating infrastructure.

Provides resolution and validation of the FNM_PATH environment variable against
the FNM manifest, enabling graceful test skipping and developer onboarding.
"""

from __future__ import annotations

import enum
import os
from dataclasses import dataclass, field
from pathlib import Path

from fnm.scripts.manifest_io import FnmManifest, load_manifest


class FnmFileStatus(enum.Enum):
    """Status of an individual FNM source file check."""

    FOUND = "found"
    MISSING = "missing"


@dataclass(frozen=True)
class FnmFileCheck:
    """Result of checking a single FNM source file.

    Attributes:
        relative_path: Relative path within the FNM directory.
        expected_name: Base filename expected by the manifest.
        status: Whether the file was found or missing.
        absolute_path: Resolved absolute path, or None if not found.
    """

    relative_path: str
    expected_name: str
    status: FnmFileStatus
    absolute_path: Path | None


class FnmPathStatus(enum.Enum):
    """Overall status of FNM_PATH resolution."""

    VALID = "valid"
    PARTIAL = "partial"
    INVALID_PATH = "invalid_path"
    NOT_SET = "not_set"
    MANIFEST_ERROR = "manifest_error"


@dataclass(frozen=True)
class FnmPathResult:
    """Result of resolving and validating FNM_PATH.

    Attributes:
        status: Overall status of the resolution.
        fnm_path: Resolved absolute path, or None if not set.
        file_checks: Per-file check results from manifest validation.
        message: Human-readable summary message.
    """

    status: FnmPathStatus
    fnm_path: Path | None
    file_checks: list[FnmFileCheck] = field(default_factory=list)
    message: str = ""

    @property
    def is_usable(self) -> bool:
        """Whether the FNM path is usable (VALID or PARTIAL)."""
        return self.status in (FnmPathStatus.VALID, FnmPathStatus.PARTIAL)

    @property
    def found_files(self) -> list[FnmFileCheck]:
        """File checks with FOUND status."""
        return [f for f in self.file_checks if f.status == FnmFileStatus.FOUND]

    @property
    def missing_files(self) -> list[FnmFileCheck]:
        """File checks with MISSING status."""
        return [f for f in self.file_checks if f.status == FnmFileStatus.MISSING]

    @property
    def skip_reason(self) -> str:
        """Pytest skip message explaining why FNM data is unavailable."""
        if self.status == FnmPathStatus.NOT_SET:
            return (
                "FNM_PATH environment variable is not set. "
                "Set FNM_PATH to the directory containing CAISO FNM Annual S01 data files. "
                "See data/fnm/README.md for setup instructions."
            )
        if self.status == FnmPathStatus.INVALID_PATH:
            return (
                f"FNM_PATH is set to '{self.fnm_path}' but this is not a valid directory. "
                "Verify the path exists and contains the FNM data files."
            )
        if self.status == FnmPathStatus.MANIFEST_ERROR:
            return (
                "Could not load the FNM manifest file (data/fnm/manifest.json). "
                "Ensure PRD 01 deliverables are in place."
            )
        if self.status == FnmPathStatus.PARTIAL:
            missing = ", ".join(f.expected_name for f in self.missing_files)
            return (
                f"FNM_PATH is set but {len(self.missing_files)} required file(s) are missing: "
                f"{missing}. Verify your FNM data directory is complete."
            )
        return ""


def find_repo_root(start: Path | None = None) -> Path:
    """Walk up from start to find the repository root.

    Looks for a directory containing either a ``.git`` entry or an
    ``evaluation_guides/`` subdirectory.

    Args:
        start: Starting directory. Defaults to the current working directory.

    Returns:
        The repository root path.

    Raises:
        FileNotFoundError: If no repo root can be found.
    """
    current = (start or Path.cwd()).resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists() or (parent / "evaluation_guides").is_dir():
            return parent
    raise FileNotFoundError(
        f"Could not find repository root from {current}. "
        "Expected .git or evaluation_guides/ directory."
    )


def load_fnm_manifest(manifest_path: Path) -> FnmManifest:
    """Load the FNM manifest, delegating to manifest_io.load_manifest().

    Args:
        manifest_path: Path to the manifest JSON file.

    Returns:
        The deserialized FnmManifest.
    """
    return load_manifest(manifest_path)


def resolve_fnm_path(
    *,
    env_var: str = "FNM_PATH",
    manifest_path: Path | None = None,
) -> FnmPathResult:
    """Resolve FNM_PATH env var and validate expected files against the manifest.

    Args:
        env_var: Name of the environment variable to read (default: ``FNM_PATH``).
        manifest_path: Explicit path to the manifest JSON file. If None, the
            function locates it relative to the repository root.

    Returns:
        An FnmPathResult describing the resolution outcome.
    """
    raw_value = os.environ.get(env_var)
    if raw_value is None:
        return FnmPathResult(
            status=FnmPathStatus.NOT_SET,
            fnm_path=None,
            message=f"{env_var} environment variable is not set.",
        )

    fnm_path = Path(raw_value).expanduser().resolve()
    if not fnm_path.is_dir():
        return FnmPathResult(
            status=FnmPathStatus.INVALID_PATH,
            fnm_path=fnm_path,
            message=f"{env_var} points to '{fnm_path}' which is not a valid directory.",
        )

    # Locate manifest
    if manifest_path is None:
        try:
            repo_root = find_repo_root()
            manifest_path = repo_root / "data" / "fnm" / "manifest.json"
        except FileNotFoundError:
            return FnmPathResult(
                status=FnmPathStatus.MANIFEST_ERROR,
                fnm_path=fnm_path,
                message="Could not locate repository root to find manifest.json.",
            )

    try:
        manifest = load_fnm_manifest(manifest_path)
    except (FileNotFoundError, ValueError) as exc:
        return FnmPathResult(
            status=FnmPathStatus.MANIFEST_ERROR,
            fnm_path=fnm_path,
            message=f"Failed to load manifest: {exc}",
        )

    # Check each source file
    file_checks: list[FnmFileCheck] = []
    for entry in manifest.source_files:
        abs_path = fnm_path / entry.file_name
        if abs_path.exists():
            file_checks.append(
                FnmFileCheck(
                    relative_path=entry.file_name,
                    expected_name=entry.file_name,
                    status=FnmFileStatus.FOUND,
                    absolute_path=abs_path,
                )
            )
        else:
            file_checks.append(
                FnmFileCheck(
                    relative_path=entry.file_name,
                    expected_name=entry.file_name,
                    status=FnmFileStatus.MISSING,
                    absolute_path=None,
                )
            )

    found_count = sum(1 for fc in file_checks if fc.status == FnmFileStatus.FOUND)
    missing_count = sum(1 for fc in file_checks if fc.status == FnmFileStatus.MISSING)

    if missing_count == 0:
        status = FnmPathStatus.VALID
        message = f"All {found_count} expected files found."
    elif found_count > 0:
        status = FnmPathStatus.PARTIAL
        message = f"{found_count} of {len(file_checks)} files found, {missing_count} missing."
    else:
        status = FnmPathStatus.PARTIAL
        message = f"No expected files found in '{fnm_path}'."

    return FnmPathResult(
        status=status,
        fnm_path=fnm_path,
        file_checks=file_checks,
        message=message,
    )
