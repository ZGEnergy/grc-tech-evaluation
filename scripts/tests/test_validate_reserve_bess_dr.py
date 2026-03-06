"""Tests for Reserve, BESS & DR Plausibility Checks (PRD 05/04).

Each test function corresponds to one success criterion from the PRD.
All test data is self-contained -- no external files, network calls,
or database connections.
"""

from __future__ import annotations


import pytest

from scripts.validate_reserve_bess_dr import (
    NUM_HOURS,
    HourlyBusLoad,
    ValidationNetworkId,
    check_bess_cyclic_soc_feasibility,
    check_bess_efficiency,
    check_bess_positivity,
    check_bess_soc_ordering,
    check_dr_curtailment_vs_local_load,
    check_dr_energy_neutrality_feasibility,
    check_dr_positivity,
    check_reserve_non_spinning_adequacy,
    check_reserve_requirements_sanity,
    check_reserve_spinning_adequacy,
)

NETWORK_ID = ValidationNetworkId.TINY


# ---------------------------------------------------------------------------
# Helpers for building in-memory CSV row dicts
# ---------------------------------------------------------------------------


def _make_reserve_req(
    spinning: list[float] | None = None,
    non_spinning: list[float] | None = None,
) -> dict[str, list[float]]:
    """Build a reserve requirements dict."""
    result: dict[str, list[float]] = {}
    if spinning is not None:
        result["spinning"] = spinning
    if non_spinning is not None:
        result["non_spinning"] = non_spinning
    return result


def _make_eligibility_row(
    gen_uid: str,
    spinning_eligible: bool = False,
    max_spinning_mw: float = 0.0,
    non_spinning_eligible: bool = False,
    max_non_spinning_mw: float = 0.0,
) -> dict[str, str]:
    """Build a reserve eligibility CSV row dict."""
    return {
        "gen_uid": gen_uid,
        "spinning_eligible": "true" if spinning_eligible else "false",
        "max_spinning_mw": str(max_spinning_mw),
        "non_spinning_eligible": "true" if non_spinning_eligible else "false",
        "max_non_spinning_mw": str(max_non_spinning_mw),
    }


def _make_bess_row(
    unit_id: str,
    power_mw: float = 100.0,
    energy_mwh: float = 400.0,
    roundtrip_eff: float = 0.85,
    min_soc_pct: float = 10.0,
    max_soc_pct: float = 90.0,
    initial_soc_pct: float = 50.0,
    cyclic_soc: bool = True,
) -> dict[str, str]:
    """Build a BESS unit CSV row dict."""
    return {
        "unit_id": unit_id,
        "bus": "1",
        "power_mw": str(power_mw),
        "energy_mwh": str(energy_mwh),
        "roundtrip_eff": str(roundtrip_eff),
        "min_soc_pct": str(min_soc_pct),
        "max_soc_pct": str(max_soc_pct),
        "initial_soc_pct": str(initial_soc_pct),
        "cyclic_soc": "true" if cyclic_soc else "false",
    }


def _make_dr_row(
    dr_id: str,
    bus: int = 1,
    max_curtail_mw: float = 20.0,
    max_recover_mw: float = 15.0,
    max_curtail_hours: float = 4.0,
    daily_energy_neutral: bool = True,
) -> dict[str, str]:
    """Build a DR bus CSV row dict."""
    return {
        "dr_id": dr_id,
        "bus": str(bus),
        "max_curtail_mw": str(max_curtail_mw),
        "max_recover_mw": str(max_recover_mw),
        "max_curtail_hours": str(max_curtail_hours),
        "daily_energy_neutral": "true" if daily_energy_neutral else "false",
    }


# ---------------------------------------------------------------------------
# Reserve checks (tests 1-6)
# ---------------------------------------------------------------------------


def test_check_reserve_spinning_adequacy_passes():
    """Test 1: spinning req 500MW, eligible 2000MW -> passed=True, margin 1500MW."""
    req = _make_reserve_req(spinning=[500.0] * NUM_HOURS)
    eligibility = [
        _make_eligibility_row("G1", spinning_eligible=True, max_spinning_mw=800.0),
        _make_eligibility_row("G2", spinning_eligible=True, max_spinning_mw=700.0),
        _make_eligibility_row("G3", spinning_eligible=True, max_spinning_mw=500.0),
    ]
    # Total eligible = 2000MW

    result = check_reserve_spinning_adequacy(req, eligibility, NETWORK_ID)

    assert result.passed is True
    assert result.details["eligible_capacity_mw"] == 2000.0
    assert result.details["tightest_margin_mw"] == 1500.0


def test_check_reserve_spinning_adequacy_fails():
    """Test 2: spinning req 2500MW, eligible 2000MW -> passed=False, deficit -500MW."""
    req = _make_reserve_req(spinning=[2500.0] * NUM_HOURS)
    eligibility = [
        _make_eligibility_row("G1", spinning_eligible=True, max_spinning_mw=1000.0),
        _make_eligibility_row("G2", spinning_eligible=True, max_spinning_mw=1000.0),
    ]
    # Total eligible = 2000MW

    result = check_reserve_spinning_adequacy(req, eligibility, NETWORK_ID)

    assert result.passed is False
    assert result.details["tightest_margin_mw"] == -500.0


def test_check_reserve_non_spinning_adequacy_passes():
    """Test 3: non-spinning req 300MW, eligible 1500MW -> passed=True."""
    req = _make_reserve_req(non_spinning=[300.0] * NUM_HOURS)
    eligibility = [
        _make_eligibility_row(
            "G1", non_spinning_eligible=True, max_non_spinning_mw=800.0
        ),
        _make_eligibility_row(
            "G2", non_spinning_eligible=True, max_non_spinning_mw=700.0
        ),
    ]
    # Total eligible = 1500MW

    result = check_reserve_non_spinning_adequacy(req, eligibility, NETWORK_ID)

    assert result.passed is True
    assert result.details["eligible_capacity_mw"] == 1500.0
    assert result.details["tightest_margin_mw"] == 1200.0


def test_check_reserve_requirements_sanity_passes():
    """Test 4: req 400MW, load 5000MW -> ratio 8%, passes."""
    req = _make_reserve_req(spinning=[400.0] * NUM_HOURS)
    load = [5000.0] * NUM_HOURS

    results = check_reserve_requirements_sanity(req, load, NETWORK_ID)

    assert len(results) == 1
    assert results[0].passed is True
    assert results[0].details["all_positive"] is True
    assert results[0].details["within_bound"] is True
    assert results[0].details["max_ratio"] == pytest.approx(0.08, abs=1e-6)


def test_check_reserve_requirements_sanity_fails_exceeds_bound():
    """Test 5: req 1000MW, load 5000MW -> 20% > 15%, fails."""
    req = _make_reserve_req(spinning=[1000.0] * NUM_HOURS)
    load = [5000.0] * NUM_HOURS

    results = check_reserve_requirements_sanity(req, load, NETWORK_ID)

    assert len(results) == 1
    assert results[0].passed is False
    assert results[0].details["within_bound"] is False
    assert results[0].details["max_ratio"] == pytest.approx(0.20, abs=1e-6)


def test_check_reserve_requirements_sanity_fails_nonpositive():
    """Test 6: zero/negative req -> fails."""
    req = _make_reserve_req(spinning=[0.0] * NUM_HOURS)
    load = [5000.0] * NUM_HOURS

    results = check_reserve_requirements_sanity(req, load, NETWORK_ID)

    assert len(results) == 1
    assert results[0].passed is False
    assert results[0].details["all_positive"] is False


# ---------------------------------------------------------------------------
# BESS checks (tests 7-14)
# ---------------------------------------------------------------------------


def test_check_bess_positivity_passes():
    """Test 7: 3 BESS units all positive, duration >= 1hr -> passes."""
    bess = [
        _make_bess_row("B1", power_mw=50.0, energy_mwh=200.0),
        _make_bess_row("B2", power_mw=100.0, energy_mwh=400.0),
        _make_bess_row("B3", power_mw=75.0, energy_mwh=300.0),
    ]

    result = check_bess_positivity(bess, NETWORK_ID)

    assert result.passed is True
    assert result.details["total_units"] == 3
    assert result.details["failing_units"] == []


def test_check_bess_positivity_fails_zero_power():
    """Test 8: one unit power_mw=0 -> fails."""
    bess = [
        _make_bess_row("B1", power_mw=50.0, energy_mwh=200.0),
        _make_bess_row("B2", power_mw=0.0, energy_mwh=400.0),
    ]

    result = check_bess_positivity(bess, NETWORK_ID)

    assert result.passed is False
    assert "B2" in result.details["failing_units"]


def test_check_bess_positivity_fails_insufficient_duration():
    """Test 9: power=100, energy=50 (0.5hr) -> fails."""
    bess = [
        _make_bess_row("B1", power_mw=100.0, energy_mwh=50.0),
    ]

    result = check_bess_positivity(bess, NETWORK_ID)

    assert result.passed is False
    assert "B1" in result.details["failing_units"]


def test_check_bess_efficiency_passes():
    """Test 10: efficiencies [0.85, 0.92, 0.88] -> passes."""
    bess = [
        _make_bess_row("B1", roundtrip_eff=0.85),
        _make_bess_row("B2", roundtrip_eff=0.92),
        _make_bess_row("B3", roundtrip_eff=0.88),
    ]

    result = check_bess_efficiency(bess, NETWORK_ID)

    assert result.passed is True
    assert result.details["failing_units"] == []


def test_check_bess_efficiency_fails_too_low():
    """Test 11: eff=0.50 -> fails."""
    bess = [
        _make_bess_row("B1", roundtrip_eff=0.50),
    ]

    result = check_bess_efficiency(bess, NETWORK_ID)

    assert result.passed is False
    assert "B1" in result.details["failing_units"]


def test_check_bess_soc_ordering_passes():
    """Test 12: min=10, max=90, initial=50 -> passes."""
    bess = [
        _make_bess_row("B1", min_soc_pct=10.0, max_soc_pct=90.0, initial_soc_pct=50.0),
    ]

    result = check_bess_soc_ordering(bess, NETWORK_ID)

    assert result.passed is True
    assert result.details["failing_units"] == []


def test_check_bess_soc_ordering_fails_inverted():
    """Test 13: min=90, max=10 -> fails."""
    bess = [
        _make_bess_row("B1", min_soc_pct=90.0, max_soc_pct=10.0, initial_soc_pct=50.0),
    ]

    result = check_bess_soc_ordering(bess, NETWORK_ID)

    assert result.passed is False
    assert "B1" in result.details["failing_units"]


def test_check_bess_cyclic_soc_feasibility_passes():
    """Test 14: valid cyclic BESS unit -> passes."""
    bess = [
        _make_bess_row(
            "B1",
            power_mw=100.0,
            energy_mwh=400.0,
            min_soc_pct=10.0,
            max_soc_pct=90.0,
            initial_soc_pct=50.0,
            roundtrip_eff=0.85,
            cyclic_soc=True,
        ),
    ]

    result = check_bess_cyclic_soc_feasibility(bess, NETWORK_ID)

    assert result.passed is True
    assert result.details["failing_units"] == []


# ---------------------------------------------------------------------------
# DR checks (tests 15-20)
# ---------------------------------------------------------------------------


def test_check_dr_positivity_passes():
    """Test 15: 2 DR resources all positive -> passes."""
    dr = [
        _make_dr_row("DR1", max_curtail_mw=20.0, max_recover_mw=15.0),
        _make_dr_row("DR2", max_curtail_mw=30.0, max_recover_mw=25.0),
    ]

    result = check_dr_positivity(dr, NETWORK_ID)

    assert result.passed is True
    assert result.details["failing_resources"] == []


def test_check_dr_positivity_fails_zero_recovery():
    """Test 16: max_recover_mw=0 -> fails."""
    dr = [
        _make_dr_row("DR1", max_curtail_mw=20.0, max_recover_mw=0.0),
    ]

    result = check_dr_positivity(dr, NETWORK_ID)

    assert result.passed is False
    assert "DR1" in result.details["failing_resources"]


def test_check_dr_energy_neutrality_feasible():
    """Test 17: curtail=20MW*4hr=80MWh, recover=15MW*20hr=300MWh -> passes."""
    dr = [
        _make_dr_row(
            "DR1",
            max_curtail_mw=20.0,
            max_recover_mw=15.0,
            max_curtail_hours=4.0,
            daily_energy_neutral=True,
        ),
    ]

    result = check_dr_energy_neutrality_feasibility(dr, NETWORK_ID)

    assert result.passed is True


def test_check_dr_energy_neutrality_infeasible():
    """Test 18: curtail=100MW*20hr=2000MWh, recover=10MW*4hr=40MWh -> fails."""
    dr = [
        _make_dr_row(
            "DR1",
            max_curtail_mw=100.0,
            max_recover_mw=10.0,
            max_curtail_hours=20.0,
            daily_energy_neutral=True,
        ),
    ]

    result = check_dr_energy_neutrality_feasibility(dr, NETWORK_ID)

    assert result.passed is False
    assert "DR1" in result.details["failing_resources"]


def test_check_dr_curtailment_vs_local_load_passes():
    """Test 19: curtail=25MW, load>=30MW all hours -> passes."""
    dr = [
        _make_dr_row("DR1", bus=1, max_curtail_mw=25.0),
    ]
    bus_loads = [
        HourlyBusLoad(bus_id=1, load_mw=[30.0] * NUM_HOURS),
    ]

    result = check_dr_curtailment_vs_local_load(dr, bus_loads, NETWORK_ID)

    assert result.passed is True
    assert result.details["failing_resources"] == []


def test_check_dr_curtailment_vs_local_load_fails():
    """Test 20: curtail=50MW, load=40MW hours 3,4 -> fails."""
    dr = [
        _make_dr_row("DR1", bus=1, max_curtail_mw=50.0),
    ]
    # Load is 100MW at all hours except hours 3 and 4 where it's 40MW
    load_values = [100.0] * NUM_HOURS
    load_values[3] = 40.0
    load_values[4] = 40.0
    bus_loads = [
        HourlyBusLoad(bus_id=1, load_mw=load_values),
    ]

    result = check_dr_curtailment_vs_local_load(dr, bus_loads, NETWORK_ID)

    assert result.passed is False
    assert "DR1" in result.details["failing_resources"]
    failing_hours = result.details["failing_values"]["DR1"]["failing_hours"]
    assert 3 in failing_hours
    assert 4 in failing_hours
