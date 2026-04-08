"""Tests for Flowgate & Scenario Validation (PRD 05/05).

All 25 unit tests specified in the PRD Success Criteria section.
Tests are self-contained with no external file or network dependencies.
"""

from __future__ import annotations

import numpy as np

from scripts.validate_flowgate_scenario import (
    BranchRecord,
    CheckStatus,
    FlowgateRecord,
    FlowgateScenarioValidationConfig,
    ForecastData,
    NetworkBranchTopology,
    ResourceType,
    ScenarioMultiplierData,
    check_correlation_fidelity,
    check_ensemble_mean,
    check_flowgate_branch_disjoint,
    check_flowgate_branch_existence,
    check_flowgate_count,
    check_flowgate_limits,
    check_flowgate_weights,
    check_forecast_rmse,
    check_multiplier_non_negative,
    check_multiplier_pmax_bound,
    check_scenario_dimensions,
    check_solar_nighttime_zero,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = FlowgateScenarioValidationConfig()


def _make_topology(
    branch_data: list[tuple[int, int, int, float]],
    network_id: str = "test",
) -> NetworkBranchTopology:
    """Create a NetworkBranchTopology from (idx, from_bus, to_bus, rate_a) tuples."""
    branches = [
        BranchRecord(branch_idx=idx, from_bus=fb, to_bus=tb, rate_a_mw=ra)
        for idx, fb, tb, ra in branch_data
    ]
    return NetworkBranchTopology(
        network_id=network_id,
        branches=branches,
        branch_idx_set=frozenset(b.branch_idx for b in branches),
        branch_rate_map={b.branch_idx: b.rate_a_mw for b in branches},
    )


def _make_flowgate(
    flowgate_id: str,
    branch_ids: list[int],
    weights: list[float] | None = None,
    limit_mw: float = 100.0,
    direction: str = "both",
) -> FlowgateRecord:
    """Create a FlowgateRecord with defaults."""
    if weights is None:
        weights = [1.0] * len(branch_ids)
    return FlowgateRecord(
        flowgate_id=flowgate_id,
        flowgate_name=f"Test {flowgate_id}",
        branch_ids=branch_ids,
        weights=weights,
        limit_mw=limit_mw,
        direction=direction,
    )


def _make_scenario_data(
    multipliers: list[list[list[float]]],
    n_generators: int = 2,
    generator_ids: list[str] | None = None,
    pmax_values: list[float] | None = None,
    resource_type: ResourceType = ResourceType.WIND,
    network_id: str = "test",
) -> ScenarioMultiplierData:
    """Create a ScenarioMultiplierData from a 3-D multiplier array."""
    n_scenarios = len(multipliers)
    n_hours = len(multipliers[0][0]) if multipliers and multipliers[0] else 24
    if generator_ids is None:
        generator_ids = [f"GEN_{i}" for i in range(n_generators)]
    if pmax_values is None:
        pmax_values = [100.0] * n_generators
    return ScenarioMultiplierData(
        network_id=network_id,
        resource_type=resource_type,
        generator_ids=generator_ids,
        pmax_values=pmax_values,
        multipliers=multipliers,
        n_scenarios=n_scenarios,
        n_generators=n_generators,
        n_hours=n_hours,
    )


def _make_forecast_data(
    forecast: list[list[float]],
    actual: list[list[float]],
    pmax_values: list[float],
    resource_type: ResourceType = ResourceType.WIND,
    night_hours: list[int] | None = None,
    generator_ids: list[str] | None = None,
    network_id: str = "test",
) -> ForecastData:
    """Create a ForecastData."""
    n_gen = len(forecast)
    if generator_ids is None:
        generator_ids = [f"GEN_{i}" for i in range(n_gen)]
    return ForecastData(
        network_id=network_id,
        resource_type=resource_type,
        generator_ids=generator_ids,
        pmax_values=pmax_values,
        forecast=forecast,
        actual=actual,
        night_hours=night_hours or [],
    )


def _uniform_multipliers(
    n_scenarios: int, n_generators: int, n_hours: int, value: float = 1.0
) -> list[list[list[float]]]:
    """Create a 3-D multiplier array with uniform values."""
    return [[[value] * n_hours for _ in range(n_generators)] for _ in range(n_scenarios)]


# ---------------------------------------------------------------------------
# Flowgate checks (a-e)
# ---------------------------------------------------------------------------


class TestFlowgateBranchExistence:
    """Tests 1-2: check_flowgate_branch_existence."""

    def test_all_valid(self) -> None:
        """Test 1: All branch IDs valid -> PASS."""
        topology = _make_topology(
            [
                (1, 10, 20, 500.0),
                (2, 20, 30, 400.0),
                (3, 30, 40, 300.0),
                (4, 40, 50, 200.0),
                (5, 50, 60, 100.0),
            ]
        )
        flowgates = [
            _make_flowgate("FG_1", [1, 2]),
            _make_flowgate("FG_2", [4, 5]),
        ]
        result = check_flowgate_branch_existence(flowgates, topology)
        assert result.status == CheckStatus.PASS
        assert result.items_checked == 2
        assert result.items_failed == 0

    def test_missing_branch(self) -> None:
        """Test 2: Branch 99 doesn't exist -> FAIL."""
        topology = _make_topology(
            [
                (1, 10, 20, 500.0),
                (2, 20, 30, 400.0),
                (3, 30, 40, 300.0),
            ]
        )
        flowgates = [_make_flowgate("FG_1", [1, 99])]
        result = check_flowgate_branch_existence(flowgates, topology)
        assert result.status == CheckStatus.FAIL
        assert any("99" in d for d in result.details)


class TestFlowgateLimits:
    """Tests 3-4: check_flowgate_limits."""

    def test_positive_and_bounded(self) -> None:
        """Test 3: limit_mw=800 < sum_rate_a=900 -> PASS; limit_mw=1000 > 900 -> FAIL."""
        topology = _make_topology(
            [
                (1, 10, 20, 500.0),
                (2, 20, 30, 400.0),
            ]
        )

        # PASS case: 0 < 800 < 900
        fg_pass = [_make_flowgate("FG_1", [1, 2], limit_mw=800.0)]
        result = check_flowgate_limits(fg_pass, topology)
        assert result.status == CheckStatus.PASS

        # FAIL case: 1000 > 900
        fg_fail = [_make_flowgate("FG_1", [1, 2], limit_mw=1000.0)]
        result = check_flowgate_limits(fg_fail, topology)
        assert result.status == CheckStatus.FAIL

    def test_rejects_zero(self) -> None:
        """Test 4: limit_mw=0 -> FAIL."""
        topology = _make_topology(
            [
                (1, 10, 20, 500.0),
                (2, 20, 30, 400.0),
            ]
        )
        flowgates = [_make_flowgate("FG_1", [1, 2], limit_mw=0.0)]
        result = check_flowgate_limits(flowgates, topology)
        assert result.status == CheckStatus.FAIL
        assert any("not positive" in d for d in result.details)


class TestFlowgateWeights:
    """Tests 5-7: check_flowgate_weights."""

    def test_valid(self) -> None:
        """Test 5: weights [1.0, 0.75] -> PASS."""
        flowgates = [_make_flowgate("FG_1", [1, 2], weights=[1.0, 0.75])]
        result = check_flowgate_weights(flowgates)
        assert result.status == CheckStatus.PASS

    def test_rejects_zero(self) -> None:
        """Test 6: weight 0.0 at position 1 -> FAIL."""
        flowgates = [_make_flowgate("FG_1", [1, 2], weights=[1.0, 0.0])]
        result = check_flowgate_weights(flowgates)
        assert result.status == CheckStatus.FAIL
        assert any("position 1" in d and "zero" in d for d in result.details)

    def test_rejects_nan(self) -> None:
        """Test 7: NaN weight -> FAIL."""
        flowgates = [_make_flowgate("FG_1", [1, 2], weights=[1.0, float("nan")])]
        result = check_flowgate_weights(flowgates)
        assert result.status == CheckStatus.FAIL


class TestFlowgateBranchDisjoint:
    """Tests 8-9: check_flowgate_branch_disjoint."""

    def test_no_overlap(self) -> None:
        """Test 8: disjoint branches -> PASS."""
        flowgates = [
            _make_flowgate("FG_1", [1, 2]),
            _make_flowgate("FG_2", [3, 4]),
            _make_flowgate("FG_3", [5]),
        ]
        result = check_flowgate_branch_disjoint(flowgates)
        assert result.status == CheckStatus.PASS

    def test_overlap(self) -> None:
        """Test 9: branch 3 shared -> FAIL."""
        flowgates = [
            _make_flowgate("FG_1", [1, 2, 3]),
            _make_flowgate("FG_2", [3, 4, 5]),
        ]
        result = check_flowgate_branch_disjoint(flowgates)
        assert result.status == CheckStatus.FAIL
        assert any("3" in d and "FG_1" in d and "FG_2" in d for d in result.details)


class TestFlowgateCount:
    """Tests 10-11: check_flowgate_count."""

    def test_in_range(self) -> None:
        """Test 10: 4 flowgates in [3, 5] -> PASS."""
        flowgates = [_make_flowgate(f"FG_{i}", [i]) for i in range(1, 5)]
        result = check_flowgate_count(flowgates, DEFAULT_CONFIG)
        assert result.status == CheckStatus.PASS

    def test_below_minimum(self) -> None:
        """Test 11: 2 flowgates < minimum 3 -> FAIL."""
        flowgates = [_make_flowgate(f"FG_{i}", [i]) for i in range(1, 3)]
        result = check_flowgate_count(flowgates, DEFAULT_CONFIG)
        assert result.status == CheckStatus.FAIL
        assert "2" in result.message
        assert "3" in result.message


# ---------------------------------------------------------------------------
# Scenario checks (f-l)
# ---------------------------------------------------------------------------


class TestScenarioDimensions:
    """Tests 12-13: check_scenario_dimensions."""

    def test_correct(self) -> None:
        """Test 12: 50 scenarios x 24 hours -> PASS."""
        mults = _uniform_multipliers(50, 2, 24)
        data = _make_scenario_data(mults, n_generators=2)
        result = check_scenario_dimensions(data, DEFAULT_CONFIG)
        assert result.status == CheckStatus.PASS

    def test_wrong_count(self) -> None:
        """Test 13: 40 scenarios -> FAIL."""
        mults = _uniform_multipliers(40, 2, 24)
        data = _make_scenario_data(mults, n_generators=2)
        result = check_scenario_dimensions(data, DEFAULT_CONFIG)
        assert result.status == CheckStatus.FAIL
        assert "40" in result.message


class TestMultiplierNonNegative:
    """Tests 14-15: check_multiplier_non_negative."""

    def test_passes(self) -> None:
        """Test 14: all values >= 0 -> PASS."""
        mults = _uniform_multipliers(50, 2, 24, value=0.8)
        data = _make_scenario_data(mults, n_generators=2)
        result = check_multiplier_non_negative(data)
        assert result.status == CheckStatus.PASS
        assert result.measured_value == 0.0

    def test_fails(self) -> None:
        """Test 15: one negative value -> FAIL."""
        mults = _uniform_multipliers(50, 2, 24, value=0.8)
        mults[0][0][0] = -0.5
        data = _make_scenario_data(mults, n_generators=2)
        result = check_multiplier_non_negative(data)
        assert result.status == CheckStatus.FAIL
        assert result.measured_value is not None
        assert result.measured_value > 0.0


class TestMultiplierPmaxBound:
    """Tests 16-17: check_multiplier_pmax_bound."""

    def test_passes(self) -> None:
        """Test 16: forecast * multiplier <= Pmax -> PASS."""
        # forecast=80, multiplier=1.0, Pmax=100 -> realization=80 <= 100
        mults = _uniform_multipliers(50, 1, 24, value=1.0)
        data = _make_scenario_data(mults, n_generators=1, pmax_values=[100.0])
        forecast = _make_forecast_data(
            forecast=[[80.0] * 24],
            actual=[[80.0] * 24],
            pmax_values=[100.0],
        )
        result = check_multiplier_pmax_bound(data, forecast, DEFAULT_CONFIG)
        assert result.status == CheckStatus.PASS

    def test_fails(self) -> None:
        """Test 17: forecast=100, multiplier=2.0, Pmax=150 -> 200 > 150 -> FAIL."""
        mults = _uniform_multipliers(50, 1, 24, value=2.0)
        data = _make_scenario_data(mults, n_generators=1, pmax_values=[150.0])
        forecast = _make_forecast_data(
            forecast=[[100.0] * 24],
            actual=[[100.0] * 24],
            pmax_values=[150.0],
        )
        result = check_multiplier_pmax_bound(data, forecast, DEFAULT_CONFIG)
        assert result.status == CheckStatus.FAIL
        assert result.measured_value is not None
        assert result.measured_value > 0


class TestEnsembleMean:
    """Tests 18-19: check_ensemble_mean."""

    def test_within_tolerance(self) -> None:
        """Test 18: mean ~ 1.02, tolerance 0.05 -> PASS."""
        mults = _uniform_multipliers(50, 2, 24, value=1.02)
        data = _make_scenario_data(mults, n_generators=2)
        result = check_ensemble_mean(data, DEFAULT_CONFIG)
        assert result.status == CheckStatus.PASS
        assert result.measured_value is not None
        assert abs(result.measured_value - 1.02) < 0.001

    def test_outside_tolerance(self) -> None:
        """Test 19: all multipliers = 1.20, deviation > 0.05 -> FAIL."""
        mults = _uniform_multipliers(50, 2, 24, value=1.20)
        data = _make_scenario_data(mults, n_generators=2)
        result = check_ensemble_mean(data, DEFAULT_CONFIG)
        assert result.status == CheckStatus.FAIL


class TestCorrelationFidelity:
    """Tests 20-21: check_correlation_fidelity."""

    def test_passes(self) -> None:
        """Test 20: generate correlated samples matching target rho=0.7 -> PASS."""
        rng = np.random.default_rng(42)
        n_scenarios = 500
        n_generators = 2
        n_hours = 24
        target_rho = 0.7

        # Generate correlated normal samples via Cholesky
        target_corr = [[1.0, target_rho], [target_rho, 1.0]]
        l_chol = np.linalg.cholesky(target_corr)

        mults: list[list[list[float]]] = []
        for _ in range(n_scenarios):
            gen_hours: list[list[float]] = [[] for _ in range(n_generators)]
            for _ in range(n_hours):
                z = rng.standard_normal(n_generators)
                correlated = l_chol @ z
                # Convert to multipliers centered at 1.0
                for g in range(n_generators):
                    gen_hours[g].append(1.0 + 0.1 * correlated[g])
            mults.append(gen_hours)

        data = _make_scenario_data(mults, n_generators=n_generators)
        config = FlowgateScenarioValidationConfig(
            correlation_frobenius_threshold=0.10,
        )
        result = check_correlation_fidelity(data, target_corr, config)
        assert result.status == CheckStatus.PASS

    def test_skips_single_generator(self) -> None:
        """Test 21: single generator -> SKIPPED."""
        mults = _uniform_multipliers(50, 1, 24)
        data = _make_scenario_data(mults, n_generators=1)
        target = [[1.0]]
        result = check_correlation_fidelity(data, target, DEFAULT_CONFIG)
        assert result.status == CheckStatus.SKIPPED


class TestSolarNighttimeZero:
    """Tests 22-23: check_solar_nighttime_zero."""

    def test_passes(self) -> None:
        """Test 22: all night-hour multipliers = 1.0 -> PASS."""
        night_hours = [0, 1, 22, 23]
        mults = _uniform_multipliers(50, 2, 24, value=1.0)
        # Set non-night hours to something different to make the test meaningful
        for s in range(50):
            for g in range(2):
                for h in range(24):
                    if h not in night_hours:
                        mults[s][g][h] = 0.9
        data = _make_scenario_data(mults, n_generators=2, resource_type=ResourceType.SOLAR)
        forecast = _make_forecast_data(
            forecast=[[0.0] * 24] * 2,
            actual=[[0.0] * 24] * 2,
            pmax_values=[100.0, 100.0],
            resource_type=ResourceType.SOLAR,
            night_hours=night_hours,
        )
        result = check_solar_nighttime_zero(data, forecast)
        assert result.status == CheckStatus.PASS

    def test_fails(self) -> None:
        """Test 23: one nighttime multiplier = 1.5 -> FAIL."""
        night_hours = [0, 1, 22, 23]
        mults = _uniform_multipliers(50, 2, 24, value=1.0)
        mults[0][0][0] = 1.5  # violation at hour 0 (nighttime)
        data = _make_scenario_data(mults, n_generators=2, resource_type=ResourceType.SOLAR)
        forecast = _make_forecast_data(
            forecast=[[0.0] * 24] * 2,
            actual=[[0.0] * 24] * 2,
            pmax_values=[100.0, 100.0],
            resource_type=ResourceType.SOLAR,
            night_hours=night_hours,
        )
        result = check_solar_nighttime_zero(data, forecast)
        assert result.status == CheckStatus.FAIL
        assert result.measured_value is not None
        assert result.measured_value >= 1


class TestForecastRmse:
    """Tests 24-25: check_forecast_rmse."""

    def test_wind_in_range(self) -> None:
        """Test 24: wind RMSE ~ 20% of capacity -> PASS in [10, 30]%."""
        # 1 generator, Pmax=100, forecast=80, actual=60
        # error = 20 MW, RMSE = 20 MW, RMSE% = 20/100 * 100 = 20%
        forecast = _make_forecast_data(
            forecast=[[80.0] * 24],
            actual=[[60.0] * 24],
            pmax_values=[100.0],
            resource_type=ResourceType.WIND,
        )
        result = check_forecast_rmse(forecast, DEFAULT_CONFIG)
        assert result.status == CheckStatus.PASS
        assert result.measured_value is not None
        assert 19.0 <= result.measured_value <= 21.0

    def test_solar_too_low(self) -> None:
        """Test 25: solar forecast == actual (RMSE=0%) -> FAIL, below 5%."""
        forecast = _make_forecast_data(
            forecast=[[50.0] * 24],
            actual=[[50.0] * 24],
            pmax_values=[100.0],
            resource_type=ResourceType.SOLAR,
        )
        result = check_forecast_rmse(forecast, DEFAULT_CONFIG)
        assert result.status == CheckStatus.FAIL
        assert result.measured_value is not None
        assert result.measured_value < 5.0
