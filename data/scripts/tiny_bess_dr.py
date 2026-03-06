"""BESS & DR Resource Definitions for the IEEE 39-bus (TINY) network.

Defines one 150MW/600MWh BESS unit at bus 25 and one DR-eligible bus at bus 20
(25MW curtailment). Outputs bess_units.csv and dr_buses.csv conforming to the
canonical CSV schema from D4.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path

from scripts.reconcile_bus_gen import MatpowerBusRecord, parse_matpower_case

__version__ = "0.1.0"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BessUnit:
    """A single Battery Energy Storage System unit definition."""

    unit_id: str
    bus: int
    power_mw: float  # maximum charge/discharge power (MW)
    energy_mwh: float  # energy storage capacity (MWh)
    charge_eff: float  # charging efficiency (fraction)
    discharge_eff: float  # discharging efficiency (fraction)
    min_soc: float  # minimum state of charge (fraction)
    max_soc: float  # maximum state of charge (fraction)
    init_soc: float  # initial state of charge (fraction)
    cyclic_soc: bool  # whether SoC must return to init_soc at end of horizon
    spinning_eligible: bool  # eligible for spinning reserve
    non_spinning_eligible: bool  # eligible for non-spinning reserve

    @property
    def duration_hours(self) -> float:
        """Energy-to-power ratio in hours."""
        return self.energy_mwh / self.power_mw

    @property
    def round_trip_efficiency(self) -> float:
        """Round-trip efficiency = charge_eff * discharge_eff."""
        return self.charge_eff * self.discharge_eff


@dataclass(frozen=True)
class DrBus:
    """A single Demand Response eligible bus definition."""

    bus: int
    max_curtailment_mw: float  # maximum load curtailment (MW)
    max_recovery_mw: float  # maximum load recovery after curtailment (MW)
    curtailment_cost: float  # cost of curtailment ($/MWh)
    recovery_cost: float  # cost of recovery ($/MWh)
    max_hours: float  # maximum consecutive hours of curtailment
    energy_neutral: bool  # total curtailment energy == total recovery energy
    notification_lead_time_hr: float  # hours of advance notice required


@dataclass(frozen=True)
class BessDrDefinitionResult:
    """Complete result from the BESS & DR definition pipeline."""

    bess_units: list[BessUnit]
    dr_buses: list[DrBus]
    bess_csv_path: str
    dr_csv_path: str


# ---------------------------------------------------------------------------
# Builder functions
# ---------------------------------------------------------------------------


def build_bess_unit() -> BessUnit:
    """Build the single BESS unit for the TINY case39 network.

    Returns a 150MW/600MWh (4-hour) BESS at bus 25 with asymmetric
    charge/discharge efficiencies (0.92/0.95), SoC bounds of 10%-90%,
    initial SoC of 50%, cyclic SoC constraint, and reserve eligibility
    for both spinning and non-spinning products.

    Returns:
        A fully populated BessUnit.
    """
    return BessUnit(
        unit_id="BESS_1",
        bus=25,
        power_mw=150.0,
        energy_mwh=600.0,
        charge_eff=0.92,
        discharge_eff=0.95,
        min_soc=0.10,
        max_soc=0.90,
        init_soc=0.50,
        cyclic_soc=True,
        spinning_eligible=True,
        non_spinning_eligible=True,
    )


def build_dr_bus() -> DrBus:
    """Build the single DR-eligible bus for the TINY case39 network.

    Returns bus 20 (680MW load) with 25MW max curtailment (~3.7% of bus load),
    25MW max recovery, $200/MWh curtailment cost, $50/MWh recovery cost,
    4-hour max duration, energy neutrality, and 1-hour notification lead time.

    Returns:
        A fully populated DrBus.
    """
    return DrBus(
        bus=20,
        max_curtailment_mw=25.0,
        max_recovery_mw=25.0,
        curtailment_cost=200.0,
        recovery_cost=50.0,
        max_hours=4.0,
        energy_neutral=True,
        notification_lead_time_hr=1.0,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def load_bus_data(m_file_path: Path) -> list[MatpowerBusRecord]:
    """Load bus data from a MATPOWER .m file.

    Wrapper around parse_matpower_case that extracts just the bus records.

    Args:
        m_file_path: Path to the MATPOWER .m file.

    Returns:
        List of MatpowerBusRecord from the case file.

    Raises:
        FileNotFoundError: If m_file_path does not exist.
        ValueError: If the .m file cannot be parsed.
    """
    case_data = parse_matpower_case(m_file_path)
    return case_data.buses


def validate_bess_placement(
    bess: BessUnit,
    buses: list[MatpowerBusRecord],
) -> None:
    """Validate that a BESS unit is placed on a valid bus.

    Checks:
    1. The bus exists in the network.
    2. The bus has non-zero load (Pd > 0), since BESS placement on a
       zero-load bus is atypical and likely an error.

    Args:
        bess: The BESS unit to validate.
        buses: List of bus records from the network.

    Raises:
        ValueError: If the bus does not exist or has zero load.
    """
    bus_map = {b.bus_id: b for b in buses}

    if bess.bus not in bus_map:
        msg = f"BESS bus {bess.bus} does not exist in the network"
        raise ValueError(msg)

    bus_record = bus_map[bess.bus]
    if bus_record.pd <= 0:
        msg = (
            f"BESS bus {bess.bus} has zero or negative load (Pd={bus_record.pd:.2f} MW); "
            f"placement on a zero-load bus is atypical"
        )
        raise ValueError(msg)


def validate_dr_placement(
    dr: DrBus,
    buses: list[MatpowerBusRecord],
    *,
    min_curtailment_fraction: float = 0.01,
) -> None:
    """Validate that a DR bus is placed on a valid bus with sufficient load.

    Checks:
    1. The bus exists in the network.
    2. The bus has non-zero load (Pd > 0).
    3. The curtailment amount is at least min_curtailment_fraction of bus load.

    Args:
        dr: The DR bus to validate.
        buses: List of bus records from the network.
        min_curtailment_fraction: Minimum ratio of max_curtailment_mw to bus Pd.
            Defaults to 0.01 (1%).

    Raises:
        ValueError: If validation fails.
    """
    bus_map = {b.bus_id: b for b in buses}

    if dr.bus not in bus_map:
        msg = f"DR bus {dr.bus} does not exist in the network"
        raise ValueError(msg)

    bus_record = bus_map[dr.bus]
    if bus_record.pd <= 0:
        msg = (
            f"DR bus {dr.bus} has zero or negative load (Pd={bus_record.pd:.2f} MW); "
            f"DR requires a load bus"
        )
        raise ValueError(msg)

    curtailment_fraction = dr.max_curtailment_mw / bus_record.pd
    if curtailment_fraction < min_curtailment_fraction:
        msg = (
            f"DR bus {dr.bus} curtailment fraction ({curtailment_fraction:.4f}) is below "
            f"minimum threshold ({min_curtailment_fraction:.4f}); "
            f"max_curtailment_mw={dr.max_curtailment_mw:.2f} MW vs bus Pd={bus_record.pd:.2f} MW"
        )
        raise ValueError(msg)


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

# Column names aligned with csv_schema.py (build_bess_units_schema)
BESS_CSV_COLUMNS = [
    "unit_id",
    "bus_id",
    "power_mw",
    "energy_mwh",
    "efficiency",
    "min_soc",
    "max_soc",
    "init_soc",
]

# Column names aligned with csv_schema.py (build_dr_buses_schema)
DR_CSV_COLUMNS = [
    "bus_id",
    "max_curtailment_mw",
    "max_recovery_mw",
    "curtailment_cost",
    "recovery_cost",
    "max_hours",
]


def write_bess_units_csv(
    bess_units: list[BessUnit],
    dest_path: Path,
) -> None:
    """Write BESS unit definitions to a canonical CSV file.

    The CSV columns match the bess_units schema from D4. The efficiency
    column contains the round-trip efficiency (charge_eff * discharge_eff).

    Parent directories are created if they do not exist.

    Args:
        bess_units: List of BESS units to write.
        dest_path: Path to write the CSV file.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    with open(dest_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(BESS_CSV_COLUMNS)
        for bess in bess_units:
            writer.writerow(
                [
                    bess.unit_id,
                    bess.bus,
                    f"{bess.power_mw:.2f}",
                    f"{bess.energy_mwh:.2f}",
                    f"{bess.round_trip_efficiency:.4f}",
                    f"{bess.min_soc:.2f}",
                    f"{bess.max_soc:.2f}",
                    f"{bess.init_soc:.2f}",
                ]
            )


def write_dr_buses_csv(
    dr_buses: list[DrBus],
    dest_path: Path,
) -> None:
    """Write DR bus definitions to a canonical CSV file.

    The CSV columns match the dr_buses schema from D4.

    Parent directories are created if they do not exist.

    Args:
        dr_buses: List of DR buses to write.
        dest_path: Path to write the CSV file.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    with open(dest_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(DR_CSV_COLUMNS)
        for dr in dr_buses:
            writer.writerow(
                [
                    dr.bus,
                    f"{dr.max_curtailment_mw:.2f}",
                    f"{dr.max_recovery_mw:.2f}",
                    f"{dr.curtailment_cost:.2f}",
                    f"{dr.recovery_cost:.2f}",
                    f"{dr.max_hours:.1f}",
                ]
            )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def define_bess_and_dr(
    m_file_path: Path,
    output_dir: Path,
) -> BessDrDefinitionResult:
    """Define BESS and DR resources for the TINY case39 network.

    Builds the BESS unit and DR bus, validates placement against the
    network bus data, writes both CSV files, and returns a result summary.

    Args:
        m_file_path: Path to the case39.m file.
        output_dir: Directory to write bess_units.csv and dr_buses.csv.

    Returns:
        A BessDrDefinitionResult with the resources and output paths.

    Raises:
        FileNotFoundError: If m_file_path does not exist.
        ValueError: If placement validation fails.
    """
    buses = load_bus_data(m_file_path)

    bess = build_bess_unit()
    dr = build_dr_bus()

    validate_bess_placement(bess, buses)
    validate_dr_placement(dr, buses)

    bess_csv_path = output_dir / "bess_units.csv"
    dr_csv_path = output_dir / "dr_buses.csv"

    write_bess_units_csv([bess], bess_csv_path)
    write_dr_buses_csv([dr], dr_csv_path)

    logger.info(
        "BESS: %s at bus %d (%.0f MW / %.0f MWh), DR: bus %d (%.0f MW curtailment)",
        bess.unit_id,
        bess.bus,
        bess.power_mw,
        bess.energy_mwh,
        dr.bus,
        dr.max_curtailment_mw,
    )

    return BessDrDefinitionResult(
        bess_units=[bess],
        dr_buses=[dr],
        bess_csv_path=str(bess_csv_path),
        dr_csv_path=str(dr_csv_path),
    )


def main(
    networks_dir: Path | None = None,
    output_dir: Path | None = None,
) -> BessDrDefinitionResult:
    """Entry point: define BESS and DR resources for TINY case39.

    Args:
        networks_dir: Directory containing case39.m. Defaults to
            <repo_root>/data/networks/.
        output_dir: Directory to write output CSVs. Defaults to
            <repo_root>/data/timeseries/case39/.

    Returns:
        A BessDrDefinitionResult.
    """
    repo_root = Path(__file__).resolve().parent.parent

    if networks_dir is None:
        networks_dir = repo_root / "networks"
    if output_dir is None:
        output_dir = repo_root / "timeseries" / "case39"

    m_file_path = networks_dir / "case39.m"
    return define_bess_and_dr(m_file_path, output_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
