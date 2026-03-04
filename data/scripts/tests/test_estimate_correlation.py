"""Tests for estimate_correlation module (PRD 04/02).

Self-contained tests with synthetic correlated profile data. No external
data files required.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.estimate_correlation import (
    CorrelationEstimationOutput,
    CorrelationMatrixDiagnostics,
    GeneratorInfo,
    NetworkCorrelationResult,
    NetworkId,
    PsdStatus,
    ResourceType,
    check_positive_semidefinite,
    compute_spearman_rank_correlation,
    derive_tiny_submatrix,
    estimate_network_correlation,
    extract_correlation_blocks,
    load_renewable_profiles,
    project_to_nearest_psd,
    write_correlation_output,
)

# ---------------------------------------------------------------------------
# Fixtures: synthetic companion CSVs
# ---------------------------------------------------------------------------


def _make_wind_csv(num_rows: int, bus_numbers: list[int], *, seed: int = 42) -> str:
    """Generate a synthetic wind CSV with correlated profiles."""
    rng = np.random.default_rng(seed)
    base = rng.uniform(20, 80, size=num_rows)

    lines = ["Time," + ",".join(f"Bus_{b}" for b in bus_numbers)]
    for t in range(num_rows):
        day = 1 + t // 24
        hour = t % 24
        ts = f"2019-01-01 {t:02d}:00:00" if t < 24 else f"2019-01-{day:02d} {hour:02d}:00:00"
        vals = [base[t] + rng.normal(0, 5) for _ in bus_numbers]
        lines.append(ts + "," + ",".join(f"{v:.2f}" for v in vals))
    return "\n".join(lines) + "\n"


def _make_solar_csv(num_rows: int, bus_numbers: list[int], *, seed: int = 99) -> str:
    """Generate a synthetic solar CSV with correlated profiles."""
    rng = np.random.default_rng(seed)
    base = rng.uniform(0, 50, size=num_rows)

    lines = ["Time," + ",".join(f"Bus_{b}" for b in bus_numbers)]
    for t in range(num_rows):
        day = 1 + t // 24
        hour = t % 24
        ts = f"2019-01-01 {t:02d}:00:00" if t < 24 else f"2019-01-{day:02d} {hour:02d}:00:00"
        vals = [max(0, base[t] + rng.normal(0, 3)) for _ in bus_numbers]
        lines.append(ts + "," + ",".join(f"{v:.2f}" for v in vals))
    return "\n".join(lines) + "\n"


@pytest.fixture()
def small_network_dir(tmp_path: Path) -> Path:
    """Create a synthetic network with 4 wind + 2 solar generators, 200 hours."""
    raw_dir = tmp_path / "ACTIVSg2000" / "raw"
    raw_dir.mkdir(parents=True)

    wind_csv = _make_wind_csv(200, [10, 20, 30, 40], seed=42)
    (raw_dir / "ACTIVSg2000_wind.csv").write_text(wind_csv)

    solar_csv = _make_solar_csv(200, [100, 200], seed=99)
    (raw_dir / "ACTIVSg2000_solar.csv").write_text(solar_csv)

    return raw_dir


@pytest.fixture()
def large_network_dir(tmp_path: Path) -> Path:
    """Create a synthetic network with 10 generators for submatrix tests."""
    raw_dir = tmp_path / "ACTIVSg2000" / "raw"
    raw_dir.mkdir(parents=True)

    wind_csv = _make_wind_csv(300, [5, 15, 25, 35, 45, 55, 65], seed=11)
    (raw_dir / "ACTIVSg2000_wind.csv").write_text(wind_csv)

    solar_csv = _make_solar_csv(300, [105, 205, 305], seed=22)
    (raw_dir / "ACTIVSg2000_solar.csv").write_text(solar_csv)

    return raw_dir


# ---------------------------------------------------------------------------
# 1. test_load_renewable_profiles_returns_correct_shape
# ---------------------------------------------------------------------------


def test_load_renewable_profiles_returns_correct_shape(small_network_dir: Path) -> None:
    """Given fixture CSVs with 4 wind + 2 solar, 200 time steps, verify shape."""
    profiles, generators = load_renewable_profiles(small_network_dir, NetworkId.ACTIVSG2000)
    assert profiles.shape == (200, 6)
    assert len(generators) == 6


# ---------------------------------------------------------------------------
# 2. test_load_renewable_profiles_generator_ordering
# ---------------------------------------------------------------------------


def test_load_renewable_profiles_generator_ordering(small_network_dir: Path) -> None:
    """Verify wind generators come first, sorted by bus number, then solar."""
    _, generators = load_renewable_profiles(small_network_dir, NetworkId.ACTIVSG2000)

    # First 4 should be wind
    for g in generators[:4]:
        assert g.resource_type == ResourceType.WIND

    # Last 2 should be solar
    for g in generators[4:]:
        assert g.resource_type == ResourceType.SOLAR

    # Within each type, sorted by bus number ascending
    wind_buses = [g.bus_number for g in generators[:4]]
    assert wind_buses == sorted(wind_buses)

    solar_buses = [g.bus_number for g in generators[4:]]
    assert solar_buses == sorted(solar_buses)


# ---------------------------------------------------------------------------
# 3. test_load_renewable_profiles_missing_csv_raises
# ---------------------------------------------------------------------------


def test_load_renewable_profiles_missing_csv_raises(tmp_path: Path) -> None:
    """Verify FileNotFoundError when no wind or solar CSV files exist."""
    empty_dir = tmp_path / "empty" / "raw"
    empty_dir.mkdir(parents=True)
    # Write a non-wind/solar file so the directory exists but has no matches
    (empty_dir / "readme.txt").write_text("nothing here")

    with pytest.raises(FileNotFoundError):
        load_renewable_profiles(empty_dir, NetworkId.ACTIVSG2000)


# ---------------------------------------------------------------------------
# 4. test_compute_spearman_rank_correlation_identity_for_identical_columns
# ---------------------------------------------------------------------------


def test_compute_spearman_rank_correlation_identity_for_identical_columns() -> None:
    """Two identical columns should have Spearman correlation of 1.0."""
    rng = np.random.default_rng(7)
    col = rng.uniform(0, 100, size=50)
    profiles = np.column_stack([col, col, rng.uniform(0, 100, size=50)])
    corr = compute_spearman_rank_correlation(profiles)
    assert corr[0, 1] == pytest.approx(1.0, abs=1e-10)


# ---------------------------------------------------------------------------
# 5. test_compute_spearman_rank_correlation_known_values
# ---------------------------------------------------------------------------


def test_compute_spearman_rank_correlation_known_values() -> None:
    """Given known monotonic relationships, verify expected correlations."""
    t = np.arange(100, dtype=np.float64)
    profiles = np.column_stack(
        [
            t,  # monotonically increasing
            -t,  # perfectly anti-correlated with first
            t + 0.001 * np.random.default_rng(0).standard_normal(100),  # nearly identical to first
            np.random.default_rng(1).uniform(0, 100, 100),  # unrelated
            t**2,  # monotonic with t => rho = 1.0
        ]
    )
    corr = compute_spearman_rank_correlation(profiles)

    # col0 vs col1: perfect anti-correlation
    assert corr[0, 1] == pytest.approx(-1.0, abs=1e-6)
    # col0 vs col2: near 1.0
    assert corr[0, 2] == pytest.approx(1.0, abs=0.01)
    # col0 vs col4: t vs t^2 is monotonic => rho = 1.0
    assert corr[0, 4] == pytest.approx(1.0, abs=1e-6)


# ---------------------------------------------------------------------------
# 6. test_compute_spearman_rank_correlation_diagonal_is_one
# ---------------------------------------------------------------------------


def test_compute_spearman_rank_correlation_diagonal_is_one() -> None:
    """Diagonal of the correlation matrix should always be 1.0."""
    rng = np.random.default_rng(12)
    profiles = rng.uniform(0, 100, size=(50, 4))
    corr = compute_spearman_rank_correlation(profiles)
    np.testing.assert_array_equal(np.diag(corr), np.ones(4))


# ---------------------------------------------------------------------------
# 7. test_compute_spearman_rank_correlation_symmetry
# ---------------------------------------------------------------------------


def test_compute_spearman_rank_correlation_symmetry() -> None:
    """Correlation matrix should be symmetric: matrix[i,j] == matrix[j,i]."""
    rng = np.random.default_rng(33)
    profiles = rng.uniform(0, 100, size=(80, 5))
    corr = compute_spearman_rank_correlation(profiles)
    np.testing.assert_array_almost_equal(corr, corr.T)


# ---------------------------------------------------------------------------
# 8. test_compute_spearman_handles_tied_ranks
# ---------------------------------------------------------------------------


def test_compute_spearman_handles_tied_ranks() -> None:
    """Profiles with many tied values should produce a valid correlation matrix."""
    rng = np.random.default_rng(44)
    # Create profiles with lots of ties (integer values in small range)
    profiles = rng.integers(0, 5, size=(100, 3)).astype(np.float64)
    # Ensure no column is constant
    profiles[0, :] = [0.0, 1.0, 2.0]
    profiles[1, :] = [4.0, 0.0, 4.0]

    corr = compute_spearman_rank_correlation(profiles)

    # Valid correlation matrix properties
    np.testing.assert_array_equal(np.diag(corr), np.ones(3))
    np.testing.assert_array_almost_equal(corr, corr.T)
    assert np.all(corr >= -1.0 - 1e-10)
    assert np.all(corr <= 1.0 + 1e-10)


# ---------------------------------------------------------------------------
# 9. test_check_positive_semidefinite_true_for_identity
# ---------------------------------------------------------------------------


def test_check_positive_semidefinite_true_for_identity() -> None:
    """Identity matrix is PSD."""
    assert check_positive_semidefinite(np.eye(5)) is True


# ---------------------------------------------------------------------------
# 10. test_check_positive_semidefinite_false_for_non_psd
# ---------------------------------------------------------------------------


def test_check_positive_semidefinite_false_for_non_psd() -> None:
    """A matrix with a negative eigenvalue should not be PSD."""
    # Construct a symmetric matrix with a guaranteed negative eigenvalue
    m = np.array(
        [
            [1.0, 0.9, 0.9],
            [0.9, 1.0, -0.9],
            [0.9, -0.9, 1.0],
        ]
    )
    assert check_positive_semidefinite(m) is False


# ---------------------------------------------------------------------------
# 11. test_project_to_nearest_psd_fixes_negative_eigenvalues
# ---------------------------------------------------------------------------


def test_project_to_nearest_psd_fixes_negative_eigenvalues() -> None:
    """After projection, all eigenvalues should be >= epsilon, diagonal 1.0, symmetric."""
    m = np.array(
        [
            [1.0, 0.9, 0.9],
            [0.9, 1.0, -0.9],
            [0.9, -0.9, 1.0],
        ]
    )
    epsilon = 1e-8
    projected, diag = project_to_nearest_psd(m, epsilon=epsilon)

    eigenvalues = np.linalg.eigvalsh(projected)
    assert eigenvalues.min() >= epsilon * 0.5  # allow small float rounding
    np.testing.assert_array_almost_equal(np.diag(projected), np.ones(3))
    np.testing.assert_array_almost_equal(projected, projected.T)


# ---------------------------------------------------------------------------
# 12. test_project_to_nearest_psd_diagnostics_correct
# ---------------------------------------------------------------------------


def test_project_to_nearest_psd_diagnostics_correct() -> None:
    """Diagnostics should report correct min eigenvalue and clipped count."""
    m = np.array(
        [
            [1.0, 0.9, 0.9],
            [0.9, 1.0, -0.9],
            [0.9, -0.9, 1.0],
        ]
    )
    _, diag = project_to_nearest_psd(m)

    assert diag.original_min_eigenvalue < 0
    assert diag.num_negative_eigenvalues >= 1
    assert diag.frobenius_norm_change >= 0


# ---------------------------------------------------------------------------
# 13. test_project_to_nearest_psd_preserves_already_psd
# ---------------------------------------------------------------------------


def test_project_to_nearest_psd_preserves_already_psd() -> None:
    """An already-PSD matrix should have near-zero Frobenius norm change."""
    m = np.array(
        [
            [1.0, 0.3, 0.1],
            [0.3, 1.0, 0.2],
            [0.1, 0.2, 1.0],
        ]
    )
    assert check_positive_semidefinite(m) is True

    projected, diag = project_to_nearest_psd(m)
    assert diag.frobenius_norm_change < 1e-10
    assert diag.num_negative_eigenvalues == 0


# ---------------------------------------------------------------------------
# 14. test_extract_correlation_blocks_three_blocks
# ---------------------------------------------------------------------------


def test_extract_correlation_blocks_three_blocks() -> None:
    """With both wind and solar generators, should return 3 blocks."""
    generators = [
        GeneratorInfo(0, "w1", 10, ResourceType.WIND),
        GeneratorInfo(1, "w2", 20, ResourceType.WIND),
        GeneratorInfo(2, "s1", 100, ResourceType.SOLAR),
        GeneratorInfo(3, "s2", 200, ResourceType.SOLAR),
    ]
    corr = np.array(
        [
            [1.0, 0.8, 0.3, 0.2],
            [0.8, 1.0, 0.25, 0.15],
            [0.3, 0.25, 1.0, 0.7],
            [0.2, 0.15, 0.7, 1.0],
        ]
    )
    blocks = extract_correlation_blocks(corr, generators)
    assert len(blocks) == 3

    block_types = [(b.row_type, b.col_type) for b in blocks]
    assert (ResourceType.WIND, ResourceType.WIND) in block_types
    assert (ResourceType.SOLAR, ResourceType.SOLAR) in block_types
    assert (ResourceType.WIND, ResourceType.SOLAR) in block_types


# ---------------------------------------------------------------------------
# 15. test_extract_correlation_blocks_wind_only
# ---------------------------------------------------------------------------


def test_extract_correlation_blocks_wind_only() -> None:
    """With only wind generators, should return only wind-wind block."""
    generators = [
        GeneratorInfo(0, "w1", 10, ResourceType.WIND),
        GeneratorInfo(1, "w2", 20, ResourceType.WIND),
        GeneratorInfo(2, "w3", 30, ResourceType.WIND),
    ]
    corr = np.array(
        [
            [1.0, 0.5, 0.3],
            [0.5, 1.0, 0.4],
            [0.3, 0.4, 1.0],
        ]
    )
    blocks = extract_correlation_blocks(corr, generators)
    assert len(blocks) == 1
    assert blocks[0].row_type == ResourceType.WIND
    assert blocks[0].col_type == ResourceType.WIND


# ---------------------------------------------------------------------------
# 16. test_derive_tiny_submatrix_correct_dimension
# ---------------------------------------------------------------------------


def _make_source_result(dim: int, *, seed: int = 55) -> NetworkCorrelationResult:
    """Create a synthetic NetworkCorrelationResult with a PSD correlation matrix."""
    rng = np.random.default_rng(seed)
    # Generate a valid PSD correlation matrix via random data
    data = rng.standard_normal((500, dim))
    corr = np.corrcoef(data, rowvar=False)
    np.fill_diagonal(corr, 1.0)
    corr = (corr + corr.T) / 2.0

    n_wind = dim // 2
    generators = []
    for i in range(dim):
        rt = ResourceType.WIND if i < n_wind else ResourceType.SOLAR
        generators.append(GeneratorInfo(i, f"gen_{i}", bus_number=(i + 1) * 10, resource_type=rt))

    return NetworkCorrelationResult(
        network_id=NetworkId.ACTIVSG2000,
        generators=generators,
        correlation_matrix=[[round(float(v), 6) for v in row] for row in corr],
        diagnostics=CorrelationMatrixDiagnostics(
            dimension=dim,
            num_wind_generators=n_wind,
            num_solar_generators=dim - n_wind,
            num_profile_hours=500,
            condition_number=float(np.linalg.cond(corr)),
            min_eigenvalue=float(np.linalg.eigvalsh(corr).min()),
            max_abs_off_diagonal=0.5,
            mean_abs_off_diagonal=0.2,
            fraction_strong_correlation=0.1,
            psd_status=PsdStatus.ALREADY_PSD,
            psd_projection=None,
        ),
        blocks=[],
        source_files=["test_wind.csv", "test_solar.csv"],
    )


def test_derive_tiny_submatrix_correct_dimension() -> None:
    """50x50 source with tiny_generator_count=5 should produce 5x5."""
    source = _make_source_result(50)
    tiny_result, derivation = derive_tiny_submatrix(source, 5)
    assert len(tiny_result.generators) == 5
    assert len(tiny_result.correlation_matrix) == 5
    assert len(tiny_result.correlation_matrix[0]) == 5
    assert derivation.target_dimension == 5


# ---------------------------------------------------------------------------
# 17. test_derive_tiny_submatrix_is_psd
# ---------------------------------------------------------------------------


def test_derive_tiny_submatrix_is_psd() -> None:
    """Derived TINY submatrix should be positive semi-definite."""
    source = _make_source_result(20)
    tiny_result, _ = derive_tiny_submatrix(source, 5)
    sub = np.array(tiny_result.correlation_matrix)
    assert check_positive_semidefinite(sub) is True


# ---------------------------------------------------------------------------
# 18. test_derive_tiny_submatrix_sorted_by_bus_number
# ---------------------------------------------------------------------------


def test_derive_tiny_submatrix_sorted_by_bus_number() -> None:
    """Source generator indices should correspond to lowest bus numbers."""
    source = _make_source_result(20)
    _, derivation = derive_tiny_submatrix(source, 5)

    # The source generators sorted by bus number ascending
    sorted_gens = sorted(source.generators, key=lambda g: g.bus_number)
    expected_indices = [g.index for g in sorted_gens[:5]]
    assert derivation.source_generator_indices == expected_indices
    assert derivation.sorting_method == "bus_number_ascending"


# ---------------------------------------------------------------------------
# 19. test_derive_tiny_submatrix_exceeding_dimension_raises
# ---------------------------------------------------------------------------


def test_derive_tiny_submatrix_exceeding_dimension_raises() -> None:
    """Should raise ValueError when tiny count exceeds source dimension."""
    source = _make_source_result(5)
    with pytest.raises(ValueError, match="exceeds"):
        derive_tiny_submatrix(source, 10)


# ---------------------------------------------------------------------------
# 20. test_write_correlation_output_roundtrip
# ---------------------------------------------------------------------------


def test_write_correlation_output_roundtrip(tmp_path: Path) -> None:
    """Write JSON, read back, verify matrix values survive roundtrip within 1e-6."""
    generators = [
        GeneratorInfo(0, "w1", 10, ResourceType.WIND),
        GeneratorInfo(1, "s1", 100, ResourceType.SOLAR),
        GeneratorInfo(2, "w2", 20, ResourceType.WIND),
    ]
    corr_matrix = [[1.0, 0.123456, 0.654321], [0.123456, 1.0, 0.333333], [0.654321, 0.333333, 1.0]]

    result = NetworkCorrelationResult(
        network_id=NetworkId.ACTIVSG2000,
        generators=generators,
        correlation_matrix=corr_matrix,
        diagnostics=CorrelationMatrixDiagnostics(
            dimension=3,
            num_wind_generators=2,
            num_solar_generators=1,
            num_profile_hours=100,
            condition_number=2.5,
            min_eigenvalue=0.3,
            max_abs_off_diagonal=0.654321,
            mean_abs_off_diagonal=0.37037,
            fraction_strong_correlation=0.333,
            psd_status=PsdStatus.ALREADY_PSD,
            psd_projection=None,
        ),
        blocks=[],
        source_files=["wind.csv", "solar.csv"],
    )

    output = CorrelationEstimationOutput(
        networks=[result],
        tiny_derivation=None,
        script_version="0.1.0",
        generated_at="2024-01-01T00:00:00+00:00",
    )

    dest = tmp_path / "test_output.json"
    write_correlation_output(output, dest)

    with open(dest) as fh:
        data = json.load(fh)

    # Verify matrix roundtrip
    loaded_matrix = data["networks"][0]["correlation_matrix"]
    for i in range(3):
        for j in range(3):
            assert abs(loaded_matrix[i][j] - corr_matrix[i][j]) < 1e-6

    # Verify metadata fields
    assert data["script_version"] == "0.1.0"
    assert data["networks"][0]["network_id"] == "ACTIVSg2000"
    assert data["networks"][0]["diagnostics"]["psd_status"] == "already_psd"


# ---------------------------------------------------------------------------
# 21. test_write_correlation_output_human_readable
# ---------------------------------------------------------------------------


def test_write_correlation_output_human_readable(tmp_path: Path) -> None:
    """JSON should be indented (not minified) with snake_case keys."""
    generators = [
        GeneratorInfo(0, "w1", 10, ResourceType.WIND),
        GeneratorInfo(1, "s1", 100, ResourceType.SOLAR),
    ]
    result = NetworkCorrelationResult(
        network_id=NetworkId.ACTIVSG2000,
        generators=generators,
        correlation_matrix=[[1.0, 0.5], [0.5, 1.0]],
        diagnostics=CorrelationMatrixDiagnostics(
            dimension=2,
            num_wind_generators=1,
            num_solar_generators=1,
            num_profile_hours=50,
            condition_number=1.5,
            min_eigenvalue=0.5,
            max_abs_off_diagonal=0.5,
            mean_abs_off_diagonal=0.5,
            fraction_strong_correlation=0.5,
            psd_status=PsdStatus.ALREADY_PSD,
            psd_projection=None,
        ),
        blocks=[],
        source_files=["wind.csv"],
    )
    output = CorrelationEstimationOutput(
        networks=[result],
        tiny_derivation=None,
        script_version="0.1.0",
        generated_at="2024-01-01T00:00:00+00:00",
    )

    dest = tmp_path / "readable.json"
    write_correlation_output(output, dest)

    text = dest.read_text()
    # Indented means multiple lines with spaces
    lines = text.strip().split("\n")
    assert len(lines) > 5  # Not minified
    # Check for snake_case keys
    assert "network_id" in text
    assert "script_version" in text
    assert "correlation_matrix" in text
    assert "psd_status" in text


# ---------------------------------------------------------------------------
# 22. test_estimate_network_correlation_end_to_end
# ---------------------------------------------------------------------------


def test_estimate_network_correlation_end_to_end(small_network_dir: Path) -> None:
    """End-to-end: estimate correlation for a small synthetic network."""
    result = estimate_network_correlation(small_network_dir, NetworkId.ACTIVSG2000)

    # Should have 6 generators (4 wind + 2 solar)
    assert len(result.generators) == 6

    # Correlation matrix should be 6x6
    assert len(result.correlation_matrix) == 6
    assert all(len(row) == 6 for row in result.correlation_matrix)

    # Matrix should be PSD
    corr = np.array(result.correlation_matrix)
    assert check_positive_semidefinite(corr) is True

    # Diagnostics should be populated
    assert result.diagnostics.dimension == 6
    assert result.diagnostics.num_wind_generators == 4
    assert result.diagnostics.num_solar_generators == 2
    assert result.diagnostics.num_profile_hours == 200
    assert result.diagnostics.condition_number > 0

    # Should have block summaries
    assert len(result.blocks) >= 1

    # Diagonal should be 1.0
    for i in range(6):
        assert result.correlation_matrix[i][i] == pytest.approx(1.0, abs=1e-6)
