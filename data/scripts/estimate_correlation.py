"""Spatial correlation estimation for renewable generator profiles.

Estimates inter-generator Spearman rank correlation matrices from ACTIVSg
companion renewable profiles. Projects to PSD via eigenvalue clamping.
Outputs JSON with correlation matrices per network per resource type.

PRD 04/02 — Spatial Correlation Estimation.
"""

from __future__ import annotations

import csv
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

import numpy as np

__version__ = "0.1.0"

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class ResourceType(StrEnum):
    """Renewable resource type for correlation matrix labeling."""

    WIND = "wind"
    SOLAR = "solar"


class NetworkId(StrEnum):
    """Network identifiers relevant to correlation estimation."""

    ACTIVSG2000 = "ACTIVSg2000"
    ACTIVSG10K = "ACTIVSg10k"
    TINY = "TINY"


class PsdStatus(StrEnum):
    """Whether the estimated correlation matrix required PSD projection."""

    ALREADY_PSD = "already_psd"
    PROJECTED = "projected"


@dataclass(frozen=True)
class GeneratorInfo:
    """Metadata for a single renewable generator in the correlation matrix.

    Each row/column of the correlation matrix corresponds to one generator.
    This record maps matrix indices to physical generator identities.
    """

    index: int  # 0-based index into the correlation matrix
    generator_id: str  # unique generator identifier from the companion CSV
    bus_number: int  # bus number the generator is connected to
    resource_type: ResourceType


@dataclass(frozen=True)
class PsdProjectionDiagnostics:
    """Diagnostics from the nearest-PSD projection step."""

    original_min_eigenvalue: float  # most negative eigenvalue before projection
    projected_min_eigenvalue: float  # smallest eigenvalue after projection (>= epsilon)
    num_negative_eigenvalues: int  # count of eigenvalues that were clipped
    frobenius_norm_change: float  # ||C_projected - C_original||_F


@dataclass(frozen=True)
class CorrelationMatrixDiagnostics:
    """Diagnostic statistics for an estimated correlation matrix."""

    dimension: int  # number of generators (matrix is dimension x dimension)
    num_wind_generators: int
    num_solar_generators: int
    num_profile_hours: int  # number of hourly observations used in estimation
    condition_number: float  # condition number of the final (post-projection) matrix
    min_eigenvalue: float  # smallest eigenvalue of the final matrix
    max_abs_off_diagonal: float  # largest absolute off-diagonal correlation
    mean_abs_off_diagonal: float  # mean absolute off-diagonal correlation
    fraction_strong_correlation: float  # fraction of off-diag entries with |r| > 0.5
    psd_status: PsdStatus
    psd_projection: PsdProjectionDiagnostics | None  # None if already PSD


@dataclass(frozen=True)
class CorrelationBlock:
    """A sub-block of the full correlation matrix for a specific pair type.

    Used for reporting wind-wind, solar-solar, and wind-solar blocks separately
    before they are assembled into the combined matrix.
    """

    row_type: ResourceType
    col_type: ResourceType
    row_generator_ids: list[str]
    col_generator_ids: list[str]
    mean_abs_correlation: float
    min_correlation: float
    max_correlation: float


@dataclass(frozen=True)
class NetworkCorrelationResult:
    """Complete correlation estimation result for one network."""

    network_id: NetworkId
    generators: list[GeneratorInfo]
    correlation_matrix: list[list[float]]  # row-major; JSON-serializable form
    diagnostics: CorrelationMatrixDiagnostics
    blocks: list[CorrelationBlock]
    source_files: list[str]  # paths to companion CSVs used (relative to repo root)


@dataclass(frozen=True)
class TinySubmatrixDerivation:
    """Record of how the TINY correlation submatrix was derived from ACTIVSg2000."""

    source_network: NetworkId  # always ACTIVSg2000
    source_dimension: int  # dimension of the source matrix
    target_dimension: int  # dimension of the extracted submatrix
    source_generator_indices: list[int]  # which rows/cols were selected from source
    sorting_method: str  # "bus_number_ascending"


@dataclass(frozen=True)
class CorrelationEstimationOutput:
    """Top-level container for the full correlation estimation output.

    Serialized to scenarios/rank_correlation_matrix.json.
    """

    networks: list[NetworkCorrelationResult]
    tiny_derivation: TinySubmatrixDerivation | None
    script_version: str
    generated_at: str  # ISO 8601


# ---------------------------------------------------------------------------
# Helper: extract bus number from column header
# ---------------------------------------------------------------------------

_BUS_PATTERN = re.compile(r"(?:bus[_\s]?)(\d+)", re.IGNORECASE)


def _parse_bus_number(col_name: str) -> int | None:
    """Extract a bus number from a column header like 'Bus_123'."""
    m = _BUS_PATTERN.search(col_name)
    if m:
        return int(m.group(1))
    if col_name.strip().isdigit():
        return int(col_name.strip())
    return None


# ---------------------------------------------------------------------------
# Core API functions
# ---------------------------------------------------------------------------


def load_renewable_profiles(
    csv_dir: Path,
    network_id: NetworkId,
) -> tuple[np.ndarray, list[GeneratorInfo]]:
    """Load full-year renewable generation profiles from companion CSVs.

    Reads the wind and solar companion CSV files for the specified network
    from the raw download directory. Extracts hourly generation values for
    each renewable generator and assembles them into a (T, G) array where
    T is the number of hourly time steps and G is the number of generators.
    Also builds the GeneratorInfo list mapping matrix columns to physical
    generators.

    Generators are ordered by resource type (wind first, then solar) and
    within each type by bus number ascending. This ordering is deterministic
    and matches the convention used for TINY submatrix extraction.

    Args:
        csv_dir: Directory containing the raw companion CSV files for the
            network (e.g., data/timeseries/ACTIVSg2000/raw/).
        network_id: Which network to load profiles for.

    Returns:
        A tuple of:
        - profiles: np.ndarray of shape (T, G) with hourly generation in MW.
        - generators: list of GeneratorInfo, one per column of profiles.

    Raises:
        FileNotFoundError: If csv_dir does not exist or contains no
            wind/solar CSV files.
        ValueError: If wind and solar CSVs have mismatched time indices
            (different row counts).
    """
    csv_dir = Path(csv_dir)
    if not csv_dir.is_dir():
        msg = f"CSV directory does not exist: {csv_dir}"
        raise FileNotFoundError(msg)

    network_prefix = network_id.value

    # Find wind and solar CSVs
    wind_files = sorted(csv_dir.glob(f"{network_prefix}_wind*"))
    solar_files = sorted(csv_dir.glob(f"{network_prefix}_solar*"))

    if not wind_files and not solar_files:
        # Try case-insensitive fallback
        wind_files = sorted(p for p in csv_dir.glob("*wind*") if p.suffix.lower() == ".csv")
        solar_files = sorted(p for p in csv_dir.glob("*solar*") if p.suffix.lower() == ".csv")

    if not wind_files and not solar_files:
        msg = f"No wind or solar CSV files found in {csv_dir}"
        raise FileNotFoundError(msg)

    all_arrays: list[np.ndarray] = []
    generators: list[GeneratorInfo] = []
    source_files: list[str] = []
    num_rows: int | None = None

    # Process wind first, then solar (ordering convention)
    for resource_type, file_list in [
        (ResourceType.WIND, wind_files),
        (ResourceType.SOLAR, solar_files),
    ]:
        for csv_path in file_list:
            source_files.append(str(csv_path))
            with open(csv_path, newline="") as fh:
                reader = csv.reader(fh)
                headers = next(reader)
                rows = list(reader)

            # Identify data columns (skip time column)
            data_cols: list[tuple[int, int, str]] = []  # (col_idx, bus_num, col_name)
            for col_idx, col_name in enumerate(headers):
                bus_num = _parse_bus_number(col_name)
                if bus_num is not None:
                    data_cols.append((col_idx, bus_num, col_name))

            # Sort by bus number ascending within this resource type
            data_cols.sort(key=lambda x: x[1])

            if num_rows is None:
                num_rows = len(rows)
            elif len(rows) != num_rows:
                msg = (
                    f"Row count mismatch: expected {num_rows} rows but "
                    f"{csv_path.name} has {len(rows)} rows"
                )
                raise ValueError(msg)

            for col_idx, bus_num, col_name in data_cols:
                values = []
                for row in rows:
                    val_str = row[col_idx].strip() if col_idx < len(row) else "0"
                    try:
                        values.append(float(val_str))
                    except ValueError:
                        values.append(0.0)
                all_arrays.append(np.array(values, dtype=np.float64))
                generators.append(
                    GeneratorInfo(
                        index=len(generators),
                        generator_id=f"{resource_type.value}_{col_name}",
                        bus_number=bus_num,
                        resource_type=resource_type,
                    )
                )

    profiles = np.column_stack(all_arrays) if all_arrays else np.empty((0, 0))
    return profiles, generators


def compute_spearman_rank_correlation(
    profiles: np.ndarray,
) -> np.ndarray:
    """Compute the Spearman rank correlation matrix from generation profiles.

    Ranks each column (generator) independently across the time axis, then
    computes the Pearson correlation of the ranks. Uses average-rank
    convention for tied values.

    Args:
        profiles: np.ndarray of shape (T, G) with hourly generation values.
            T must be >= 2. G must be >= 2.

    Returns:
        A (G, G) symmetric correlation matrix with ones on the diagonal
        and Spearman rank correlations on the off-diagonal.

    Raises:
        ValueError: If profiles has fewer than 2 rows or fewer than 2 columns.
        ValueError: If any column has zero variance (constant generation),
            which produces undefined correlation.
    """
    t, g = profiles.shape
    if t < 2:
        msg = f"Need at least 2 time steps, got {t}"
        raise ValueError(msg)
    if g < 2:
        msg = f"Need at least 2 generators, got {g}"
        raise ValueError(msg)

    ranks = np.empty_like(profiles, dtype=np.float64)
    for col in range(g):
        ranks[:, col] = _average_rank(profiles[:, col])

    # Check for zero-variance columns (constant values => all same rank)
    for col in range(g):
        if np.all(ranks[:, col] == ranks[0, col]):
            msg = f"Column {col} has zero variance (constant generation)"
            raise ValueError(msg)

    corr = np.corrcoef(ranks, rowvar=False)
    # Ensure exact unit diagonal and symmetry
    np.fill_diagonal(corr, 1.0)
    corr = (corr + corr.T) / 2.0
    return corr


def _average_rank(arr: np.ndarray) -> np.ndarray:
    """Compute average ranks for a 1-D array, handling ties.

    Tied values receive the mean of the ranks they would occupy.
    """
    n = len(arr)
    order = np.argsort(arr, kind="mergesort")
    ranks = np.empty(n, dtype=np.float64)
    ranks[order] = np.arange(1, n + 1, dtype=np.float64)

    # Handle ties: group by value and assign average rank
    sorted_vals = arr[order]
    i = 0
    while i < n:
        j = i + 1
        while j < n and sorted_vals[j] == sorted_vals[i]:
            j += 1
        if j > i + 1:
            # Tied group from i to j-1
            avg_rank = np.mean(np.arange(i + 1, j + 1, dtype=np.float64))
            for k in range(i, j):
                ranks[order[k]] = avg_rank
        i = j
    return ranks


def check_positive_semidefinite(
    matrix: np.ndarray,
    *,
    tol: float = -1e-10,
) -> bool:
    """Check whether a symmetric matrix is positive semi-definite.

    Computes eigenvalues and checks that the smallest eigenvalue is
    greater than or equal to tol. The tolerance allows for small
    negative eigenvalues arising from floating-point rounding.

    Args:
        matrix: A (G, G) symmetric matrix.
        tol: Minimum acceptable eigenvalue. Values below this threshold
            are considered negative. Default is -1e-10.

    Returns:
        True if the matrix is PSD within the given tolerance, False otherwise.
    """
    eigenvalues = np.linalg.eigvalsh(matrix)
    return bool(eigenvalues.min() >= tol)


def project_to_nearest_psd(
    matrix: np.ndarray,
    *,
    epsilon: float = 1e-8,
) -> tuple[np.ndarray, PsdProjectionDiagnostics]:
    """Project a symmetric matrix to the nearest positive semi-definite matrix.

    Uses eigenvalue clipping: compute the eigendecomposition, replace
    negative eigenvalues with epsilon, reconstruct the matrix, then
    rescale the diagonal to 1.0 to maintain the correlation matrix
    property (unit diagonal).

    Args:
        matrix: A (G, G) symmetric matrix that may have negative eigenvalues.
        epsilon: The minimum eigenvalue in the projected matrix. Must be > 0.

    Returns:
        A tuple of:
        - projected: The nearest PSD correlation matrix (unit diagonal).
        - diagnostics: PsdProjectionDiagnostics recording the projection details.

    Raises:
        ValueError: If matrix is not square or not symmetric (within tolerance).
        ValueError: If epsilon is not positive.
    """
    if epsilon <= 0:
        msg = f"epsilon must be positive, got {epsilon}"
        raise ValueError(msg)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        msg = f"Matrix must be square, got shape {matrix.shape}"
        raise ValueError(msg)
    if not np.allclose(matrix, matrix.T, atol=1e-8):
        msg = "Matrix is not symmetric"
        raise ValueError(msg)

    eigenvalues, eigenvectors = np.linalg.eigh(matrix)

    original_min = float(eigenvalues.min())
    num_negative = int(np.sum(eigenvalues < 0))

    # Clip negative eigenvalues to epsilon
    clipped = np.maximum(eigenvalues, epsilon)

    # Reconstruct matrix
    projected = eigenvectors @ np.diag(clipped) @ eigenvectors.T

    # Rescale diagonal to 1.0 (maintain correlation matrix property)
    d = np.sqrt(np.diag(projected))
    projected = projected / np.outer(d, d)

    # Ensure exact symmetry and unit diagonal
    projected = (projected + projected.T) / 2.0
    np.fill_diagonal(projected, 1.0)

    projected_eigenvalues = np.linalg.eigvalsh(projected)
    projected_min = float(projected_eigenvalues.min())

    frobenius = float(np.linalg.norm(projected - matrix, "fro"))

    diagnostics = PsdProjectionDiagnostics(
        original_min_eigenvalue=original_min,
        projected_min_eigenvalue=projected_min,
        num_negative_eigenvalues=num_negative,
        frobenius_norm_change=frobenius,
    )

    return projected, diagnostics


def extract_correlation_blocks(
    correlation_matrix: np.ndarray,
    generators: list[GeneratorInfo],
) -> list[CorrelationBlock]:
    """Extract wind-wind, solar-solar, and wind-solar sub-blocks.

    Partitions the full correlation matrix by resource type and computes
    summary statistics for each block. The three blocks are:
    - wind-wind: correlations among wind generators
    - solar-solar: correlations among solar generators
    - wind-solar: cross-correlations between wind and solar generators

    Args:
        correlation_matrix: A (G, G) correlation matrix.
        generators: Generator metadata list matching the matrix dimensions.

    Returns:
        A list of CorrelationBlock objects. If a resource type has zero
        generators, the corresponding blocks are omitted.
    """
    wind_indices = [g.index for g in generators if g.resource_type == ResourceType.WIND]
    solar_indices = [g.index for g in generators if g.resource_type == ResourceType.SOLAR]

    wind_ids = [g.generator_id for g in generators if g.resource_type == ResourceType.WIND]
    solar_ids = [g.generator_id for g in generators if g.resource_type == ResourceType.SOLAR]

    blocks: list[CorrelationBlock] = []

    # Wind-wind block
    if len(wind_indices) >= 2:
        ww = correlation_matrix[np.ix_(wind_indices, wind_indices)]
        # Off-diagonal only for same-type blocks
        mask = ~np.eye(len(wind_indices), dtype=bool)
        off_diag = ww[mask]
        blocks.append(
            CorrelationBlock(
                row_type=ResourceType.WIND,
                col_type=ResourceType.WIND,
                row_generator_ids=wind_ids,
                col_generator_ids=wind_ids,
                mean_abs_correlation=float(np.mean(np.abs(off_diag))),
                min_correlation=float(np.min(off_diag)),
                max_correlation=float(np.max(off_diag)),
            )
        )
    elif len(wind_indices) == 1:
        blocks.append(
            CorrelationBlock(
                row_type=ResourceType.WIND,
                col_type=ResourceType.WIND,
                row_generator_ids=wind_ids,
                col_generator_ids=wind_ids,
                mean_abs_correlation=1.0,
                min_correlation=1.0,
                max_correlation=1.0,
            )
        )

    # Solar-solar block
    if len(solar_indices) >= 2:
        ss = correlation_matrix[np.ix_(solar_indices, solar_indices)]
        mask = ~np.eye(len(solar_indices), dtype=bool)
        off_diag = ss[mask]
        blocks.append(
            CorrelationBlock(
                row_type=ResourceType.SOLAR,
                col_type=ResourceType.SOLAR,
                row_generator_ids=solar_ids,
                col_generator_ids=solar_ids,
                mean_abs_correlation=float(np.mean(np.abs(off_diag))),
                min_correlation=float(np.min(off_diag)),
                max_correlation=float(np.max(off_diag)),
            )
        )
    elif len(solar_indices) == 1:
        blocks.append(
            CorrelationBlock(
                row_type=ResourceType.SOLAR,
                col_type=ResourceType.SOLAR,
                row_generator_ids=solar_ids,
                col_generator_ids=solar_ids,
                mean_abs_correlation=1.0,
                min_correlation=1.0,
                max_correlation=1.0,
            )
        )

    # Wind-solar cross block
    if wind_indices and solar_indices:
        ws = correlation_matrix[np.ix_(wind_indices, solar_indices)]
        blocks.append(
            CorrelationBlock(
                row_type=ResourceType.WIND,
                col_type=ResourceType.SOLAR,
                row_generator_ids=wind_ids,
                col_generator_ids=solar_ids,
                mean_abs_correlation=float(np.mean(np.abs(ws))),
                min_correlation=float(np.min(ws)),
                max_correlation=float(np.max(ws)),
            )
        )

    return blocks


def compute_diagnostics(
    correlation_matrix: np.ndarray,
    generators: list[GeneratorInfo],
    num_profile_hours: int,
    psd_status: PsdStatus,
    psd_projection: PsdProjectionDiagnostics | None,
) -> CorrelationMatrixDiagnostics:
    """Compute diagnostic statistics for a correlation matrix.

    Calculates matrix dimension, condition number, eigenvalue range,
    off-diagonal statistics, and records PSD projection status.

    Args:
        correlation_matrix: The final (post-projection, if applicable)
            (G, G) correlation matrix.
        generators: Generator metadata list.
        num_profile_hours: Number of hourly observations used in estimation.
        psd_status: Whether PSD projection was applied.
        psd_projection: Projection diagnostics, or None if already PSD.

    Returns:
        A CorrelationMatrixDiagnostics with all computed statistics.
    """
    g = correlation_matrix.shape[0]
    eigenvalues = np.linalg.eigvalsh(correlation_matrix)

    # Off-diagonal elements
    mask = ~np.eye(g, dtype=bool)
    off_diag = correlation_matrix[mask]

    num_wind = sum(1 for gen in generators if gen.resource_type == ResourceType.WIND)
    num_solar = sum(1 for gen in generators if gen.resource_type == ResourceType.SOLAR)

    cond_number = float(np.linalg.cond(correlation_matrix))

    fraction_strong = float(np.mean(np.abs(off_diag) > 0.5)) if len(off_diag) > 0 else 0.0

    return CorrelationMatrixDiagnostics(
        dimension=g,
        num_wind_generators=num_wind,
        num_solar_generators=num_solar,
        num_profile_hours=num_profile_hours,
        condition_number=cond_number,
        min_eigenvalue=float(eigenvalues.min()),
        max_abs_off_diagonal=float(np.max(np.abs(off_diag))) if len(off_diag) > 0 else 0.0,
        mean_abs_off_diagonal=float(np.mean(np.abs(off_diag))) if len(off_diag) > 0 else 0.0,
        fraction_strong_correlation=fraction_strong,
        psd_status=psd_status,
        psd_projection=psd_projection,
    )


def estimate_network_correlation(
    csv_dir: Path,
    network_id: NetworkId,
    *,
    psd_epsilon: float = 1e-8,
    psd_tolerance: float = -1e-10,
) -> NetworkCorrelationResult:
    """Estimate the full spatial correlation matrix for a single network.

    Orchestrates the per-network pipeline: load profiles, compute Spearman
    rank correlation, check PSD, project if needed, extract block summaries,
    compute diagnostics.

    Args:
        csv_dir: Directory containing raw companion CSV files for the network.
        network_id: Which network to estimate correlation for.
        psd_epsilon: Minimum eigenvalue for PSD projection.
        psd_tolerance: Eigenvalue threshold for the PSD check.

    Returns:
        A NetworkCorrelationResult with the correlation matrix, generator
        metadata, diagnostics, and block summaries.
    """
    profiles, generators = load_renewable_profiles(csv_dir, network_id)
    num_hours = profiles.shape[0]

    logger.info(
        "Loaded %d generators (%d time steps) for %s",
        len(generators),
        num_hours,
        network_id.value,
    )

    corr = compute_spearman_rank_correlation(profiles)

    psd_projection: PsdProjectionDiagnostics | None = None
    if check_positive_semidefinite(corr, tol=psd_tolerance):
        psd_status = PsdStatus.ALREADY_PSD
        logger.info("Correlation matrix for %s is already PSD", network_id.value)
    else:
        psd_status = PsdStatus.PROJECTED
        corr, psd_projection = project_to_nearest_psd(corr, epsilon=psd_epsilon)
        logger.info(
            "Projected %s correlation matrix to PSD (min eigenvalue was %.2e, "
            "clipped %d eigenvalues)",
            network_id.value,
            psd_projection.original_min_eigenvalue,
            psd_projection.num_negative_eigenvalues,
        )

    blocks = extract_correlation_blocks(corr, generators)
    diagnostics = compute_diagnostics(corr, generators, num_hours, psd_status, psd_projection)

    logger.info(
        "Diagnostics for %s: dim=%d, cond=%.2e, min_eig=%.2e, frac_strong=%.2f",
        network_id.value,
        diagnostics.dimension,
        diagnostics.condition_number,
        diagnostics.min_eigenvalue,
        diagnostics.fraction_strong_correlation,
    )

    # Round matrix for JSON storage
    corr_list = [[round(float(v), 6) for v in row] for row in corr]

    source_files = [str(csv_dir / f) for f in sorted(p.name for p in csv_dir.iterdir())]

    return NetworkCorrelationResult(
        network_id=network_id,
        generators=generators,
        correlation_matrix=corr_list,
        diagnostics=diagnostics,
        blocks=blocks,
        source_files=source_files,
    )


def derive_tiny_submatrix(
    source_result: NetworkCorrelationResult,
    tiny_generator_count: int,
) -> tuple[NetworkCorrelationResult, TinySubmatrixDerivation]:
    """Derive the TINY network correlation submatrix from ACTIVSg2000.

    Sorts the source network's generators by bus number ascending, then
    extracts the top-left principal submatrix of dimension
    tiny_generator_count.

    Args:
        source_result: The ACTIVSg2000 NetworkCorrelationResult.
        tiny_generator_count: Number of renewable generators in TINY.

    Returns:
        A tuple of (tiny_result, derivation).

    Raises:
        ValueError: If tiny_generator_count exceeds source matrix dimension.
        ValueError: If tiny_generator_count is less than 2.
    """
    source_dim = len(source_result.generators)
    if tiny_generator_count < 2:
        msg = f"tiny_generator_count must be >= 2, got {tiny_generator_count}"
        raise ValueError(msg)
    if tiny_generator_count > source_dim:
        msg = (
            f"tiny_generator_count ({tiny_generator_count}) exceeds source "
            f"matrix dimension ({source_dim})"
        )
        raise ValueError(msg)

    # Sort generators by bus number ascending
    sorted_gens = sorted(source_result.generators, key=lambda g: g.bus_number)
    sorted_indices = [g.index for g in sorted_gens[:tiny_generator_count]]

    # Extract source matrix as numpy array
    source_matrix = np.array(source_result.correlation_matrix)

    # Extract principal submatrix
    sub_matrix = source_matrix[np.ix_(sorted_indices, sorted_indices)]
    sub_list = [[round(float(v), 6) for v in row] for row in sub_matrix]

    # Build new generator list for TINY
    tiny_generators = []
    for new_idx, src_gen_idx in enumerate(range(tiny_generator_count)):
        src_gen = sorted_gens[src_gen_idx]
        tiny_generators.append(
            GeneratorInfo(
                index=new_idx,
                generator_id=src_gen.generator_id,
                bus_number=src_gen.bus_number,
                resource_type=src_gen.resource_type,
            )
        )

    # Compute diagnostics for the submatrix
    sub_np = np.array(sub_list)
    blocks = extract_correlation_blocks(sub_np, tiny_generators)
    diagnostics = compute_diagnostics(
        sub_np,
        tiny_generators,
        source_result.diagnostics.num_profile_hours,
        PsdStatus.ALREADY_PSD,  # principal submatrix of PSD is PSD
        None,
    )

    tiny_result = NetworkCorrelationResult(
        network_id=NetworkId.TINY,
        generators=tiny_generators,
        correlation_matrix=sub_list,
        diagnostics=diagnostics,
        blocks=blocks,
        source_files=source_result.source_files,
    )

    derivation = TinySubmatrixDerivation(
        source_network=NetworkId.ACTIVSG2000,
        source_dimension=source_dim,
        target_dimension=tiny_generator_count,
        source_generator_indices=sorted_indices,
        sorting_method="bus_number_ascending",
    )

    return tiny_result, derivation


def write_correlation_output(
    output: CorrelationEstimationOutput,
    dest_path: Path,
) -> None:
    """Serialize the full correlation estimation output to JSON.

    Writes a human-readable (indented, 2-space) JSON file. Correlation
    matrices are rounded to 6 decimal places.

    Args:
        output: The complete correlation estimation output.
        dest_path: File path to write the JSON output.

    Raises:
        PermissionError: If dest_path is not writable.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    data = _to_serializable(output)
    with open(dest_path, "w") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


def _to_serializable(obj: object) -> object:
    """Recursively convert dataclasses, enums, and numpy types to JSON-safe types."""
    if isinstance(obj, StrEnum):
        return obj.value
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, list):
        return [_to_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if hasattr(obj, "__dataclass_fields__"):
        d = {}
        for field_name in obj.__dataclass_fields__:
            d[field_name] = _to_serializable(getattr(obj, field_name))
        return d
    return str(obj)


def main(
    timeseries_base_dir: Path | None = None,
    output_path: Path | None = None,
    *,
    tiny_generator_count: int | None = None,
) -> CorrelationEstimationOutput:
    """Entry point: estimate correlation matrices for all networks.

    Orchestrates the full workflow:
    1. Estimate correlation for ACTIVSg2000 from its companion profiles.
    2. Estimate correlation for ACTIVSg10k from its companion profiles.
    3. Derive TINY submatrix from the ACTIVSg2000 result.
    4. Assemble the CorrelationEstimationOutput and write to JSON.

    Args:
        timeseries_base_dir: Base directory containing per-network
            subdirectories with raw/ CSVs. Defaults to
            <repo_root>/data/timeseries/.
        output_path: Where to write the output JSON. Defaults to
            <repo_root>/data/timeseries/scenarios/rank_correlation_matrix.json.
        tiny_generator_count: Number of renewable generators in the TINY
            network. If None, defaults to 4.

    Returns:
        The complete CorrelationEstimationOutput.
    """
    if timeseries_base_dir is None:
        timeseries_base_dir = Path(__file__).resolve().parent.parent / "timeseries"

    if output_path is None:
        output_path = timeseries_base_dir / "scenarios" / "rank_correlation_matrix.json"

    if tiny_generator_count is None:
        tiny_generator_count = 4

    results: list[NetworkCorrelationResult] = []

    # Estimate for ACTIVSg2000
    csv_dir_2000 = timeseries_base_dir / "ACTIVSg2000" / "raw"
    result_2000 = estimate_network_correlation(csv_dir_2000, NetworkId.ACTIVSG2000)
    results.append(result_2000)

    # Estimate for ACTIVSg10k
    csv_dir_10k = timeseries_base_dir / "ACTIVSg10k" / "raw"
    result_10k = estimate_network_correlation(csv_dir_10k, NetworkId.ACTIVSG10K)
    results.append(result_10k)

    # Derive TINY submatrix from ACTIVSg2000
    tiny_derivation: TinySubmatrixDerivation | None = None
    if tiny_generator_count >= 2 and len(result_2000.generators) >= tiny_generator_count:
        tiny_result, tiny_derivation = derive_tiny_submatrix(result_2000, tiny_generator_count)
        results.append(tiny_result)
    else:
        logger.warning(
            "Cannot derive TINY submatrix: tiny_generator_count=%s, source dimension=%d",
            tiny_generator_count,
            len(result_2000.generators),
        )

    output = CorrelationEstimationOutput(
        networks=results,
        tiny_derivation=tiny_derivation,
        script_version=__version__,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    write_correlation_output(output, output_path)
    logger.info("Wrote correlation output to %s", output_path)

    return output


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
