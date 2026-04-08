"""Reproducibility Manifest Generation (PRD 05/07).

Produces ``data/timeseries/manifest.json`` — a comprehensive reproducibility
manifest capturing file checksums (SHA-256), script hashes, RNG seed values,
generation parameters, software versions, git commit info, and a generation
timestamp.

All core logic uses only Python stdlib modules.  numpy and scipy are imported
only for version detection (try/except).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

__version__ = "0.1.0"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CHUNK_SIZE: int = 8192
"""Read buffer size for SHA-256 computation."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class NetworkId(StrEnum):
    """Network identifiers."""

    TINY = "case39"
    SMALL = "ACTIVSg2000"
    MEDIUM = "ACTIVSg10k"


@dataclass(frozen=True)
class FileChecksum:
    """SHA-256 checksum for a single file."""

    relative_path: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class NetworkFileChecksums:
    """All checksummed files for a single network."""

    network_id: NetworkId
    csv_files: list[FileChecksum]
    m_files: list[FileChecksum]


@dataclass(frozen=True)
class ScriptChecksum:
    """SHA-256 checksum for a generation script."""

    filename: str
    relative_path: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class SeedEntry:
    """A single RNG seed record."""

    script_name: str
    process_name: str
    seed_value: int


@dataclass(frozen=True)
class NetworkSeeds:
    """All known seeds for a single network."""

    network_id: NetworkId
    seeds: list[SeedEntry]


@dataclass(frozen=True)
class StudentTParams:
    """Student-t distribution parameters for one resource type at one hour."""

    hour: int  # 0-23 or -1 for pooled
    resource_type: str
    df: float
    loc: float
    scale: float


@dataclass(frozen=True)
class GenerationParameters:
    """All tuneable generation parameters for one network."""

    network_id: NetworkId
    smoothing_window: int | None
    wind_bias_fraction: float | None
    solar_bias_fraction: float | None
    scenario_count: int | None
    student_t_params: list[StudentTParams]
    bess_placement_scores: dict[str, float] | None
    bess_fleet_target_pct: float | None
    dr_selection_criteria: dict[str, object] | None
    dr_fleet_target_pct: float | None
    flowgate_thresholds: dict[str, float] | None


@dataclass(frozen=True)
class SoftwareVersions:
    """Captured software versions."""

    python: str
    numpy: str
    scipy: str
    octave: str | None
    matpower: str | None


@dataclass(frozen=True)
class GitInfo:
    """Git repository state."""

    commit_hash: str
    dirty: bool
    branch: str
    warning: str | None


@dataclass(frozen=True)
class Manifest:
    """Top-level reproducibility manifest."""

    manifest_version: str  # "1.0.0"
    generated_at: str  # ISO 8601 UTC
    git: GitInfo
    file_checksums: list[NetworkFileChecksums]
    script_checksums: list[ScriptChecksum]
    seeds: list[NetworkSeeds]
    parameters: list[GenerationParameters]
    software: SoftwareVersions
    total_files_checksummed: int
    total_scripts_hashed: int
    networks_covered: list[str]


# ---------------------------------------------------------------------------
# SHA-256 helpers
# ---------------------------------------------------------------------------


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 of *file_path* reading in 8 KB chunks.

    Args:
        file_path: Path to the file to hash.

    Returns:
        Lowercase hex digest (64 characters).

    Raises:
        FileNotFoundError: If *file_path* does not exist.
    """
    h = hashlib.sha256()
    with open(file_path, "rb") as fh:
        while True:
            chunk = fh.read(_CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# File-checksum collectors
# ---------------------------------------------------------------------------


def collect_csv_checksums(network_dir: Path) -> list[FileChecksum]:
    """Recursively collect SHA-256 checksums of all CSV files under *network_dir*.

    Results are sorted by relative path.

    Args:
        network_dir: Root directory to scan.

    Returns:
        Sorted list of :class:`FileChecksum`.
    """
    results: list[FileChecksum] = []
    for csv_path in sorted(network_dir.rglob("*.csv")):
        rel = str(csv_path.relative_to(network_dir))
        results.append(
            FileChecksum(
                relative_path=rel,
                sha256=compute_sha256(csv_path),
                size_bytes=csv_path.stat().st_size,
            )
        )
    return results


def collect_mfile_checksums(networks_dir: Path, network_id: NetworkId) -> list[FileChecksum]:
    """Collect SHA-256 checksums of ``*_clean.m`` files for *network_id*.

    Only files matching the ``*_clean.m`` glob are included (original
    MATPOWER case files are excluded).

    Args:
        networks_dir: Directory containing ``.m`` files.
        network_id: Network to filter on (used as filename prefix).

    Returns:
        Sorted list of :class:`FileChecksum` for matching clean files.
    """
    results: list[FileChecksum] = []
    for m_path in sorted(networks_dir.glob("*_clean.m")):
        rel = str(m_path.relative_to(networks_dir))
        results.append(
            FileChecksum(
                relative_path=rel,
                sha256=compute_sha256(m_path),
                size_bytes=m_path.stat().st_size,
            )
        )
    return results


def collect_all_file_checksums(
    timeseries_base_dir: Path, networks_dir: Path
) -> list[NetworkFileChecksums]:
    """Collect file checksums across all networks.

    Args:
        timeseries_base_dir: Base directory containing per-network timeseries dirs.
        networks_dir: Directory containing ``.m`` case files.

    Returns:
        One :class:`NetworkFileChecksums` per network that has a directory.
    """
    results: list[NetworkFileChecksums] = []
    for nid in NetworkId:
        ts_dir = timeseries_base_dir / nid.value
        if not ts_dir.is_dir():
            continue
        csv_checksums = collect_csv_checksums(ts_dir)
        m_checksums = collect_mfile_checksums(networks_dir, nid)
        results.append(
            NetworkFileChecksums(
                network_id=nid,
                csv_files=csv_checksums,
                m_files=m_checksums,
            )
        )
    return results


# ---------------------------------------------------------------------------
# Script-checksum collector
# ---------------------------------------------------------------------------


def collect_script_checksums(scripts_dir: Path) -> list[ScriptChecksum]:
    """Collect SHA-256 checksums of top-level ``.py`` files in *scripts_dir*.

    Excludes any ``tests/`` subdirectory contents — only direct children
    of *scripts_dir* are included.

    Args:
        scripts_dir: Directory to scan (non-recursive).

    Returns:
        Sorted list of :class:`ScriptChecksum`.
    """
    results: list[ScriptChecksum] = []
    for py_path in sorted(scripts_dir.glob("*.py")):
        if py_path.name == "__init__.py":
            continue
        rel = str(py_path.relative_to(scripts_dir.parent))
        results.append(
            ScriptChecksum(
                filename=py_path.name,
                relative_path=rel,
                sha256=compute_sha256(py_path),
                size_bytes=py_path.stat().st_size,
            )
        )
    return results


# ---------------------------------------------------------------------------
# Seed extraction
# ---------------------------------------------------------------------------


def extract_seeds_from_metadata(network_id: NetworkId, network_dir: Path) -> list[SeedEntry]:
    """Extract RNG seed values from scenario metadata.

    Looks for ``scenarios/stochastic_metadata.json`` inside *network_dir*.
    Recognises keys ``master_seed``, ``seed``, and ``seeds`` (dict of
    process-name to seed-value).

    Args:
        network_id: Network identifier (for labelling).
        network_dir: Network timeseries directory.

    Returns:
        List of :class:`SeedEntry` found (may be empty).
    """
    meta_path = network_dir / "scenarios" / "stochastic_metadata.json"
    if not meta_path.exists():
        return []

    data = json.loads(meta_path.read_text(encoding="utf-8"))
    entries: list[SeedEntry] = []

    if "master_seed" in data:
        entries.append(
            SeedEntry(
                script_name="stochastic_metadata",
                process_name="master",
                seed_value=int(data["master_seed"]),
            )
        )

    if "seed" in data and "master_seed" not in data:
        entries.append(
            SeedEntry(
                script_name="stochastic_metadata",
                process_name="default",
                seed_value=int(data["seed"]),
            )
        )

    if "seeds" in data and isinstance(data["seeds"], dict):
        for proc, val in sorted(data["seeds"].items()):
            entries.append(
                SeedEntry(
                    script_name="stochastic_metadata",
                    process_name=proc,
                    seed_value=int(val),
                )
            )

    return entries


def collect_all_seeds(timeseries_base_dir: Path) -> list[NetworkSeeds]:
    """Collect seed entries across all networks.

    Args:
        timeseries_base_dir: Base directory containing per-network timeseries dirs.

    Returns:
        One :class:`NetworkSeeds` per network.
    """
    results: list[NetworkSeeds] = []
    for nid in NetworkId:
        ts_dir = timeseries_base_dir / nid.value
        seeds = extract_seeds_from_metadata(nid, ts_dir) if ts_dir.is_dir() else []
        results.append(NetworkSeeds(network_id=nid, seeds=seeds))
    return results


# ---------------------------------------------------------------------------
# Parameter extraction
# ---------------------------------------------------------------------------


def extract_student_t_params(network_dir: Path) -> list[StudentTParams]:
    """Extract Student-t distribution parameters from metadata files.

    Supports two formats:
    * **TINY** (``scenarios/stochastic_metadata.json``): per-resource-type
      with optional per-hour breakdowns.
    * **SMALL/MEDIUM** (``scenarios/student_t_params.json``): dedicated
      per-hour parameter file.

    Args:
        network_dir: Network timeseries directory.

    Returns:
        List of :class:`StudentTParams`.
    """
    results: list[StudentTParams] = []

    # Try dedicated student_t_params.json first
    params_path = network_dir / "scenarios" / "student_t_params.json"
    if params_path.exists():
        data = json.loads(params_path.read_text(encoding="utf-8"))
        for resource_type, entries in data.items():
            if isinstance(entries, list):
                for entry in entries:
                    results.append(
                        StudentTParams(
                            hour=int(entry.get("hour", -1)),
                            resource_type=resource_type,
                            df=float(entry["df"]),
                            loc=float(entry.get("loc", 0.0)),
                            scale=float(entry.get("scale", 1.0)),
                        )
                    )
            elif isinstance(entries, dict):
                results.append(
                    StudentTParams(
                        hour=-1,
                        resource_type=resource_type,
                        df=float(entries["df"]),
                        loc=float(entries.get("loc", 0.0)),
                        scale=float(entries.get("scale", 1.0)),
                    )
                )
        return results

    # Fall back to stochastic_metadata.json
    meta_path = network_dir / "scenarios" / "stochastic_metadata.json"
    if meta_path.exists():
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        for resource_type in ("wind", "solar"):
            section = data.get(resource_type)
            if not isinstance(section, dict):
                continue
            params = section.get("params", section)
            if "df" in params:
                results.append(
                    StudentTParams(
                        hour=-1,
                        resource_type=resource_type,
                        df=float(params["df"]),
                        loc=float(params.get("loc", 0.0)),
                        scale=float(params.get("scale", 1.0)),
                    )
                )

    return results


def extract_generation_parameters(network_id: NetworkId, network_dir: Path) -> GenerationParameters:
    """Extract all generation parameters for one network.

    Reads from ``scenarios/stochastic_metadata.json`` and
    ``scenarios/student_t_params.json`` as available.

    Args:
        network_id: Network identifier.
        network_dir: Network timeseries directory.

    Returns:
        A :class:`GenerationParameters` instance.
    """
    student_t = extract_student_t_params(network_dir)

    # Defaults — populated from metadata when available
    smoothing_window: int | None = None
    wind_bias: float | None = None
    solar_bias: float | None = None
    scenario_count: int | None = None
    bess_scores: dict[str, float] | None = None
    bess_target: float | None = None
    dr_criteria: dict[str, object] | None = None
    dr_target: float | None = None
    fg_thresholds: dict[str, float] | None = None

    meta_path = network_dir / "scenarios" / "stochastic_metadata.json"
    if meta_path.exists():
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        smoothing_window = data.get("smoothing_window")
        wind_bias = data.get("wind_bias_fraction")
        solar_bias = data.get("solar_bias_fraction")
        scenario_count = data.get("scenario_count")
        bess_scores = data.get("bess_placement_scores")
        bess_target = data.get("bess_fleet_target_pct")
        dr_criteria = data.get("dr_selection_criteria")
        dr_target = data.get("dr_fleet_target_pct")
        fg_thresholds = data.get("flowgate_thresholds")

    return GenerationParameters(
        network_id=network_id,
        smoothing_window=smoothing_window,
        wind_bias_fraction=wind_bias,
        solar_bias_fraction=solar_bias,
        scenario_count=scenario_count,
        student_t_params=student_t,
        bess_placement_scores=bess_scores,
        bess_fleet_target_pct=bess_target,
        dr_selection_criteria=dr_criteria,
        dr_fleet_target_pct=dr_target,
        flowgate_thresholds=fg_thresholds,
    )


def collect_all_parameters(timeseries_base_dir: Path) -> list[GenerationParameters]:
    """Collect generation parameters across all networks.

    Args:
        timeseries_base_dir: Base directory containing per-network timeseries dirs.

    Returns:
        One :class:`GenerationParameters` per network.
    """
    results: list[GenerationParameters] = []
    for nid in NetworkId:
        ts_dir = timeseries_base_dir / nid.value
        if ts_dir.is_dir():
            results.append(extract_generation_parameters(nid, ts_dir))
    return results


# ---------------------------------------------------------------------------
# Software version detection
# ---------------------------------------------------------------------------


def detect_software_versions() -> SoftwareVersions:
    """Detect Python, numpy, scipy, Octave, and MATPOWER versions.

    numpy and scipy are imported via try/except so the manifest script
    itself has no hard dependency on them.

    Returns:
        A :class:`SoftwareVersions` instance.
    """
    python_ver = sys.version.split()[0]

    numpy_ver = ""
    try:
        import numpy  # type: ignore[import-untyped]

        numpy_ver = numpy.__version__
    except ImportError:
        numpy_ver = "not installed"

    scipy_ver = ""
    try:
        import scipy  # type: ignore[import-untyped]

        scipy_ver = scipy.__version__
    except ImportError:
        scipy_ver = "not installed"

    octave_ver: str | None = None
    try:
        result = subprocess.run(
            ["octave", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            first_line = result.stdout.strip().splitlines()[0]
            m = re.search(r"(\d+\.\d+\.\d+)", first_line)
            octave_ver = m.group(1) if m else first_line
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    matpower_ver: str | None = None
    try:
        result = subprocess.run(
            ["octave", "--eval", "mpver"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            m = re.search(r"(\d+\.\d+)", result.stdout)
            matpower_ver = m.group(1) if m else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return SoftwareVersions(
        python=python_ver,
        numpy=numpy_ver,
        scipy=scipy_ver,
        octave=octave_ver,
        matpower=matpower_ver,
    )


# ---------------------------------------------------------------------------
# Git info
# ---------------------------------------------------------------------------


def detect_git_info(repo_dir: Path) -> GitInfo:
    """Detect git commit hash, branch, and dirty status.

    Args:
        repo_dir: Path to the git repository root.

    Returns:
        A :class:`GitInfo` instance.
    """
    warning: str | None = None

    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(repo_dir),
            timeout=10,
        )
        commit_hash = commit.stdout.strip() if commit.returncode == 0 else "unknown"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        commit_hash = "unknown"
        warning = "git not available"

    try:
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(repo_dir),
            timeout=10,
        )
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        branch = "unknown"

    try:
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=str(repo_dir),
            timeout=10,
        )
        dirty = bool(status_result.stdout.strip()) if status_result.returncode == 0 else True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        dirty = True

    return GitInfo(
        commit_hash=commit_hash,
        dirty=dirty,
        branch=branch,
        warning=warning,
    )


# ---------------------------------------------------------------------------
# Manifest building
# ---------------------------------------------------------------------------


def build_manifest(
    file_checksums: list[NetworkFileChecksums],
    script_checksums: list[ScriptChecksum],
    seeds: list[NetworkSeeds],
    parameters: list[GenerationParameters],
    software: SoftwareVersions,
    git: GitInfo,
    generated_at: str | None = None,
) -> Manifest:
    """Assemble all components into a :class:`Manifest`.

    Args:
        file_checksums: Per-network file checksums.
        script_checksums: Script checksums.
        seeds: Per-network seeds.
        parameters: Per-network generation parameters.
        software: Software versions.
        git: Git info.
        generated_at: ISO 8601 timestamp (auto-generated if ``None``).

    Returns:
        A fully populated :class:`Manifest`.
    """
    if generated_at is None:
        generated_at = datetime.now(timezone.utc).isoformat()

    total_files = sum(len(nfc.csv_files) + len(nfc.m_files) for nfc in file_checksums)
    networks = sorted({nfc.network_id.value for nfc in file_checksums})

    return Manifest(
        manifest_version="1.0.0",
        generated_at=generated_at,
        git=git,
        file_checksums=file_checksums,
        script_checksums=script_checksums,
        seeds=seeds,
        parameters=parameters,
        software=software,
        total_files_checksummed=total_files,
        total_scripts_hashed=len(script_checksums),
        networks_covered=networks,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_HASH_RE = re.compile(r"^[0-9a-f]{40}$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T")


def validate_manifest(manifest: Manifest) -> list[str]:
    """Validate a manifest for internal consistency.

    Checks:
    * All SHA-256 hashes are 64-character lowercase hex.
    * Seed values are integers.
    * ``manifest_version`` is a valid semver string.
    * ``generated_at`` looks like an ISO 8601 timestamp.
    * ``git.commit_hash`` is 40-character hex (or ``"unknown"``).

    Args:
        manifest: The manifest to validate.

    Returns:
        A list of error message strings (empty if valid).
    """
    errors: list[str] = []

    # Semver
    if not _SEMVER_RE.match(manifest.manifest_version):
        errors.append(f"manifest_version '{manifest.manifest_version}' is not valid semver")

    # Timestamp
    if not _ISO_RE.match(manifest.generated_at):
        errors.append(f"generated_at '{manifest.generated_at}' is not a valid ISO 8601 timestamp")

    # Git hash
    if manifest.git.commit_hash != "unknown" and not _GIT_HASH_RE.match(manifest.git.commit_hash):
        errors.append(f"git commit_hash '{manifest.git.commit_hash}' is not 40-char hex")

    # File checksums
    for nfc in manifest.file_checksums:
        for fc in nfc.csv_files + nfc.m_files:
            if not _SHA256_RE.match(fc.sha256):
                errors.append(f"Bad SHA-256 for {fc.relative_path}: '{fc.sha256}'")

    # Script checksums
    for sc in manifest.script_checksums:
        if not _SHA256_RE.match(sc.sha256):
            errors.append(f"Bad SHA-256 for script {sc.filename}: '{sc.sha256}'")

    # Seeds
    for ns in manifest.seeds:
        for se in ns.seeds:
            if not isinstance(se.seed_value, int):
                errors.append(f"Seed value for {se.process_name} is not int: {se.seed_value}")

    return errors


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def _dataclass_to_dict(obj: object) -> object:
    """Recursively convert dataclasses (including StrEnum) to plain dicts."""
    if isinstance(obj, StrEnum):
        return obj.value
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _dataclass_to_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [_dataclass_to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    return obj


def serialize_manifest(manifest: Manifest) -> str:
    """Serialise a manifest to a deterministic JSON string.

    Uses sorted keys and 2-space indentation for human readability and
    reproducibility (two calls on the same input produce identical output).

    Args:
        manifest: The manifest to serialise.

    Returns:
        JSON string.
    """
    d = _dataclass_to_dict(manifest)
    return json.dumps(d, sort_keys=True, indent=2, ensure_ascii=False)


def write_manifest(manifest: Manifest, output_path: Path) -> None:
    """Validate and write a manifest to disk.

    Args:
        manifest: The manifest to write.
        output_path: Destination file path.

    Raises:
        ValueError: If validation finds errors.
    """
    errors = validate_manifest(manifest)
    if errors:
        raise ValueError(
            f"Manifest validation failed with {len(errors)} error(s):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialize_manifest(manifest) + "\n", encoding="utf-8")
    logger.info("Wrote manifest to %s", output_path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def generate_manifest(
    timeseries_base_dir: Path | None = None,
    networks_dir: Path | None = None,
    scripts_dir: Path | None = None,
    repo_dir: Path | None = None,
    output_path: Path | None = None,
) -> Manifest:
    """Generate a full reproducibility manifest.

    This is the main entry point.  All directory arguments default to
    locations relative to the repository root.

    Args:
        timeseries_base_dir: Base directory for per-network timeseries.
        networks_dir: Directory containing ``.m`` case files.
        scripts_dir: Directory containing generation scripts.
        repo_dir: Repository root (for git info).
        output_path: Where to write the JSON file (``None`` skips writing).

    Returns:
        The assembled :class:`Manifest`.
    """
    if repo_dir is None:
        repo_dir = Path(__file__).resolve().parent.parent

    if timeseries_base_dir is None:
        timeseries_base_dir = repo_dir / "data" / "timeseries"

    if networks_dir is None:
        networks_dir = repo_dir / "data" / "networks"

    if scripts_dir is None:
        scripts_dir = repo_dir / "scripts"

    file_checksums = collect_all_file_checksums(timeseries_base_dir, networks_dir)
    script_checksums = collect_script_checksums(scripts_dir)
    seeds = collect_all_seeds(timeseries_base_dir)
    parameters = collect_all_parameters(timeseries_base_dir)
    software = detect_software_versions()
    git = detect_git_info(repo_dir)

    manifest = build_manifest(
        file_checksums=file_checksums,
        script_checksums=script_checksums,
        seeds=seeds,
        parameters=parameters,
        software=software,
        git=git,
    )

    if output_path is not None:
        write_manifest(manifest, output_path)

    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    m = generate_manifest(output_path=Path("data/timeseries/manifest.json"))
    print(
        f"Manifest generated: {m.total_files_checksummed} files, "
        f"{m.total_scripts_hashed} scripts, "
        f"{len(m.networks_covered)} networks"
    )
