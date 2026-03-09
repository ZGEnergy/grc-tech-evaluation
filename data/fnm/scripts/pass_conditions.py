"""Pass Condition Definitions for ACPF and DCPF FNM Verification.

Produces the formal pass condition specification as both machine-readable JSON
(``data/fnm/reference/pass_conditions.json``) and human-readable markdown
(``data/fnm/reference/pass_conditions.md``).  The JSON is consumed at runtime
by evaluate-tool agents when comparing a tool's FNM power flow results against
the Phase 3 reference solutions.

The module is stateless and deterministic: given the threshold constants defined
here, it generates identical JSON and markdown output on every run.  There is no
FNM data dependency at generation time.

Uses only Python stdlib (no numpy/scipy).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# ---------------------------------------------------------------------------
# Outlier cause classification
# ---------------------------------------------------------------------------


class OutlierCause(Enum):
    """Probable cause for a bus or branch exceeding the pass tolerance."""

    SWITCHED_SHUNT = "switched_shunt"
    """Bus has a switched shunt device."""

    Q_LIMIT = "q_limit"
    """Bus has a generator that hit a reactive power limit."""

    SLACK_DISTRIBUTION = "slack_distribution"
    """Bus is the slack bus or electrically close to it."""

    TAP_POSITION = "tap_position"
    """Bus is the regulated bus of a tap-changing transformer."""

    ISLAND_BOUNDARY = "island_boundary"
    """Bus is at the boundary of a weakly connected subnetwork."""

    UNCLASSIFIED = "unclassified"
    """Bus exceeds tolerance but matches no classification rule."""


OUTLIER_PRIORITY: list[OutlierCause] = [
    OutlierCause.SWITCHED_SHUNT,
    OutlierCause.Q_LIMIT,
    OutlierCause.SLACK_DISTRIBUTION,
    OutlierCause.TAP_POSITION,
    OutlierCause.ISLAND_BOUNDARY,
    OutlierCause.UNCLASSIFIED,
]


# ---------------------------------------------------------------------------
# ACPF pass condition parameters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ACPFAggregateThresholds:
    """Aggregate pass thresholds for ACPF verification."""

    min_passing_fraction: float = 0.95
    vm_tolerance_pu: float = 0.005
    va_tolerance_deg: float = 0.5


@dataclass(frozen=True)
class ACPFHardFailThresholds:
    """Hard-fail thresholds for ACPF verification."""

    max_failing_fraction: float = 0.20
    vm_max_deviation_pu: float = 0.1
    va_max_deviation_deg: float = 10.0


# ---------------------------------------------------------------------------
# DCPF pass condition parameters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DCPFAggregateThresholds:
    """Aggregate pass thresholds for DCPF verification."""

    min_bus_passing_fraction: float = 0.95
    va_tolerance_deg: float = 1.0
    min_branch_passing_fraction: float = 0.90
    p_tolerance_pct: float = 10.0
    p_base_floor_mw: float = 1.0


@dataclass(frozen=True)
class DCPFHardFailThresholds:
    """Hard-fail thresholds for DCPF verification."""

    max_bus_failing_fraction: float = 0.20
    max_branch_failing_fraction: float = 0.20
    p_max_deviation_pct: float = 50.0


# ---------------------------------------------------------------------------
# Outlier classification rules
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OutlierRule:
    """A single outlier classification rule."""

    cause: OutlierCause
    description: str
    required_data: list[str]
    match_condition: str
    applies_to: str = "acpf"


@dataclass(frozen=True)
class OutlierClassificationConfig:
    """Complete outlier classification configuration."""

    rules: list[OutlierRule]
    max_classified_fraction: float = 0.10
    max_unclassified_fraction: float = 0.02


# ---------------------------------------------------------------------------
# Voltage-level informational breakdown
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VoltageLevelTier:
    """Informational voltage-level tier for detailed results breakdown."""

    label: str
    min_kv: float
    max_kv: float


# ---------------------------------------------------------------------------
# Default constants
# ---------------------------------------------------------------------------


DEFAULT_OUTLIER_RULES: list[OutlierRule] = [
    OutlierRule(
        cause=OutlierCause.SWITCHED_SHUNT,
        description=(
            "Bus has a switched shunt device in the intermediate format. "
            "Discrete switching step differences between solvers produce "
            "VM deviations of 0.002-0.010 p.u. that are legitimate "
            "solver-variation artifacts."
        ),
        required_data=["bus", "switched_shunt"],
        match_condition="has_switched_shunt(bus)",
        applies_to="acpf",
    ),
    OutlierRule(
        cause=OutlierCause.Q_LIMIT,
        description=(
            "Bus has a generator at or near a reactive power limit "
            "(|Q - Qmax| < 1.0 MVAr or |Q - Qmin| < 1.0 MVAr in the ACPF "
            "reference). Different Q-limit enforcement sequences across "
            "solvers produce different voltage setpoints at PV-to-PQ "
            "transitioned buses."
        ),
        required_data=["bus", "generator"],
        match_condition="generator_at_q_limit(bus, tolerance_mvar=1.0)",
        applies_to="acpf",
    ),
    OutlierRule(
        cause=OutlierCause.SLACK_DISTRIBUTION,
        description=(
            "Bus is the slack bus (type=3) or within 2 branches of the "
            "slack bus in the network graph. Slack bus power absorption "
            "differs between solvers, causing VA deviations that propagate "
            "to electrically nearby buses."
        ),
        required_data=["bus", "branch"],
        match_condition="is_slack_or_neighbor(bus, max_hops=2)",
        applies_to="both",
    ),
    OutlierRule(
        cause=OutlierCause.TAP_POSITION,
        description=(
            "Bus is the regulated bus (CONT field) of an in-service "
            "tap-changing transformer. Different tap optimization "
            "algorithms produce different tap positions, causing VM "
            "deviations at the regulated bus."
        ),
        required_data=["bus", "transformer"],
        match_condition="is_tap_regulated_bus(bus)",
        applies_to="acpf",
    ),
    OutlierRule(
        cause=OutlierCause.ISLAND_BOUNDARY,
        description=(
            "Bus is at the boundary of a weakly connected subnetwork "
            "(network degree <= 2 and base_kv < 69 kV). Low-voltage "
            "radial boundary buses are highly sensitive to upstream "
            "modeling differences."
        ),
        required_data=["bus", "branch"],
        match_condition="is_island_boundary(bus, max_degree=2, max_kv=69.0)",
        applies_to="both",
    ),
]


DEFAULT_VOLTAGE_TIERS: list[VoltageLevelTier] = [
    VoltageLevelTier(
        label="transmission_230kv_plus",
        min_kv=230.0,
        max_kv=float("inf"),
    ),
    VoltageLevelTier(
        label="subtransmission_69_to_229kv",
        min_kv=69.0,
        max_kv=230.0,
    ),
    VoltageLevelTier(
        label="distribution_below_69kv",
        min_kv=0.0,
        max_kv=69.0,
    ),
]


# ---------------------------------------------------------------------------
# Top-level pass condition specification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PassConditionSpec:
    """Complete pass condition specification for ACPF and DCPF verification."""

    version: str = "1.0.0"

    acpf_aggregate: ACPFAggregateThresholds = field(default_factory=ACPFAggregateThresholds)
    acpf_hard_fail: ACPFHardFailThresholds = field(default_factory=ACPFHardFailThresholds)
    dcpf_aggregate: DCPFAggregateThresholds = field(default_factory=DCPFAggregateThresholds)
    dcpf_hard_fail: DCPFHardFailThresholds = field(default_factory=DCPFHardFailThresholds)
    outlier_classification: OutlierClassificationConfig = field(
        default_factory=lambda: OutlierClassificationConfig(rules=DEFAULT_OUTLIER_RULES)
    )
    voltage_level_tiers: list[VoltageLevelTier] = field(
        default_factory=lambda: list(DEFAULT_VOLTAGE_TIERS)
    )
    bus_exclusion_registry_path: str = "data/fnm/reference/excluded_buses.json"
    acpf_reference_dir: str = "data/fnm/reference/acpf/"
    dcpf_reference_dir: str = "data/fnm/reference/dcpf/"


# ---------------------------------------------------------------------------
# Verdict structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MetricResult:
    """Result of a single metric evaluation."""

    metric_name: str
    passed: bool
    value: float
    threshold: float
    detail: str


@dataclass(frozen=True)
class HardFailResult:
    """Result of a hard-fail check."""

    check_name: str
    triggered: bool
    value: float
    threshold: float
    detail: str


@dataclass(frozen=True)
class OutlierSummary:
    """Summary of outlier classification results."""

    total_outliers: int
    classified_count: int
    unclassified_count: int
    by_cause: dict[str, int]
    classified_fraction: float
    unclassified_fraction: float
    classified_warning: bool
    unclassified_warning: bool


@dataclass(frozen=True)
class VoltageLevelBreakdown:
    """Per-voltage-level-tier metric breakdown (informational)."""

    tier_label: str
    bus_count: int
    passing_count: int
    passing_fraction: float
    mean_vm_deviation_pu: float | None
    mean_va_deviation_deg: float


@dataclass(frozen=True)
class VerificationVerdict:
    """Complete verification verdict for one analysis type (ACPF or DCPF)."""

    analysis_type: str
    overall_pass: bool
    hard_fail: bool
    aggregate_metrics: list[MetricResult]
    hard_fail_checks: list[HardFailResult]
    outlier_summary: OutlierSummary | None
    voltage_level_breakdown: list[VoltageLevelBreakdown]
    total_non_excluded_buses: int
    total_in_service_branches: int


# ---------------------------------------------------------------------------
# Specification generation
# ---------------------------------------------------------------------------


def build_pass_condition_spec() -> PassConditionSpec:
    """Build the complete pass condition specification with default thresholds.

    Returns:
        A fully populated PassConditionSpec.
    """
    return PassConditionSpec()


def spec_to_dict(spec: PassConditionSpec) -> dict:
    """Convert a PassConditionSpec to a JSON-serializable dict.

    Recursively converts all dataclass fields. Enum values are serialized
    as their string values. ``float('inf')`` is serialized as ``null``.

    Args:
        spec: The specification to serialize.

    Returns:
        A dict safe for ``json.dumps()``.
    """
    # Build the JSON structure matching the PRD schema
    outlier_rules_json = []
    for priority, rule in enumerate(spec.outlier_classification.rules, start=1):
        outlier_rules_json.append(
            {
                "priority": priority,
                "cause": rule.cause.value,
                "description": rule.description,
                "match_condition": rule.match_condition,
                "required_data": rule.required_data,
                "applies_to": rule.applies_to,
            }
        )

    tiers_json = []
    for tier in spec.voltage_level_tiers:
        tiers_json.append(
            {
                "label": tier.label,
                "min_kv": tier.min_kv,
                "max_kv_exclusive": None if math.isinf(tier.max_kv) else tier.max_kv,
            }
        )

    return {
        "$schema_version": spec.version,
        "$description": (
            "Pass condition definitions for ACPF and DCPF FNM verification. "
            "Machine-readable specification consumed by evaluate-tool agents "
            "at runtime."
        ),
        "bus_exclusion": {
            "registry_path": spec.bus_exclusion_registry_path,
            "description": (
                "Path to the D1 bus exclusion registry. All buses listed in "
                "this file are excluded from metric denominators. Exclusion "
                "reasons: ide_4_isolated, vm_zero_deenergized, "
                "disconnected_island."
            ),
            "usage": (
                "Load excluded_buses[].bus_number to build the exclusion set. "
                "Metric denominators = total_buses - len(exclusion_set)."
            ),
        },
        "acpf": {
            "reference_dir": spec.acpf_reference_dir,
            "reference_files": {
                "buses": "buses_acpf.csv",
                "branches": "branches_acpf.csv",
                "generators": "generators_acpf.csv",
                "summary": "summary_acpf.json",
            },
            "aggregate": {
                "description": (
                    "Primary pass gate. A bus passes if BOTH VM and VA "
                    "deviations are within tolerance. The fraction of passing "
                    "buses must exceed the minimum threshold."
                ),
                "min_passing_fraction": spec.acpf_aggregate.min_passing_fraction,
                "vm_tolerance_pu": spec.acpf_aggregate.vm_tolerance_pu,
                "va_tolerance_deg": spec.acpf_aggregate.va_tolerance_deg,
                "bus_pass_condition": (
                    f"|VM_tool - VM_ref| < {spec.acpf_aggregate.vm_tolerance_pu} "
                    f"AND |VA_tool - VA_ref| < {spec.acpf_aggregate.va_tolerance_deg}"
                ),
                "metric": (
                    f"count(passing_buses) / count(non_excluded_buses) >= "
                    f"{spec.acpf_aggregate.min_passing_fraction}"
                ),
            },
            "hard_fail": {
                "description": (
                    "Any single condition triggers unconditional test failure, "
                    "regardless of aggregate statistics."
                ),
                "conditions": [
                    {
                        "name": "excessive_failing_fraction",
                        "description": (
                            f"More than {spec.acpf_hard_fail.max_failing_fraction * 100:.0f}% "
                            "of non-excluded buses fail the aggregate tolerance."
                        ),
                        "condition": (
                            f"count(failing_buses) / count(non_excluded_buses) > "
                            f"{spec.acpf_hard_fail.max_failing_fraction}"
                        ),
                        "threshold": spec.acpf_hard_fail.max_failing_fraction,
                    },
                    {
                        "name": "extreme_vm_deviation",
                        "description": (
                            f"Any single bus has VM deviation exceeding "
                            f"{spec.acpf_hard_fail.vm_max_deviation_pu} p.u. "
                            "Indicates fundamental voltage error, not solver variation."
                        ),
                        "condition": (
                            f"max(|VM_tool - VM_ref|) > {spec.acpf_hard_fail.vm_max_deviation_pu}"
                        ),
                        "threshold_pu": spec.acpf_hard_fail.vm_max_deviation_pu,
                    },
                    {
                        "name": "extreme_va_deviation",
                        "description": (
                            f"Any single bus has VA deviation exceeding "
                            f"{spec.acpf_hard_fail.va_max_deviation_deg} degrees. "
                            "Indicates topology or connectivity error."
                        ),
                        "condition": (
                            f"max(|VA_tool - VA_ref|) > {spec.acpf_hard_fail.va_max_deviation_deg}"
                        ),
                        "threshold_deg": spec.acpf_hard_fail.va_max_deviation_deg,
                    },
                ],
            },
            "outlier_classification": {
                "description": (
                    "Buses that fail the aggregate tolerance are classified by "
                    "probable cause. Classification does not change pass/fail "
                    "-- it explains why outliers exist and whether they indicate "
                    "ingestion error vs. expected solver variation."
                ),
                "evaluation_order": (
                    "Rules are evaluated in the order listed. First matching "
                    "rule assigns the primary cause. A bus may match multiple "
                    "rules; only the first (highest priority) is assigned."
                ),
                "rules": outlier_rules_json,
                "warning_thresholds": {
                    "max_classified_fraction": (
                        spec.outlier_classification.max_classified_fraction
                    ),
                    "max_classified_description": (
                        f"If classified outliers (all causes except unclassified) "
                        f"exceed "
                        f"{spec.outlier_classification.max_classified_fraction * 100:.0f}% "
                        f"of non-excluded buses, emit a warning."
                    ),
                    "max_unclassified_fraction": (
                        spec.outlier_classification.max_unclassified_fraction
                    ),
                    "max_unclassified_description": (
                        f"If unclassified outliers exceed "
                        f"{spec.outlier_classification.max_unclassified_fraction * 100:.0f}% "
                        f"of non-excluded buses, emit a warning."
                    ),
                },
            },
        },
        "dcpf": {
            "reference_dir": spec.dcpf_reference_dir,
            "reference_files": {
                "buses": "buses_dcpf.csv",
                "branches": "branches_dcpf.csv",
                "summary": "summary_dcpf.json",
            },
            "aggregate": {
                "description": (
                    "Primary pass gate. Two independent metrics: bus angles and branch flows."
                ),
                "bus_angle": {
                    "description": (
                        "Fraction of non-excluded buses with VA deviation within tolerance."
                    ),
                    "min_passing_fraction": (spec.dcpf_aggregate.min_bus_passing_fraction),
                    "va_tolerance_deg": spec.dcpf_aggregate.va_tolerance_deg,
                    "bus_pass_condition": (
                        f"|VA_tool - VA_ref| < {spec.dcpf_aggregate.va_tolerance_deg}"
                    ),
                    "metric": (
                        f"count(passing_buses) / count(non_excluded_buses) >= "
                        f"{spec.dcpf_aggregate.min_bus_passing_fraction}"
                    ),
                },
                "branch_flow": {
                    "description": (
                        "Fraction of in-service branches with P deviation within tolerance."
                    ),
                    "min_passing_fraction": (spec.dcpf_aggregate.min_branch_passing_fraction),
                    "p_tolerance_pct": spec.dcpf_aggregate.p_tolerance_pct,
                    "p_base_floor_mw": spec.dcpf_aggregate.p_base_floor_mw,
                    "deviation_formula": (
                        f"|P_tool - P_ref| / max(|P_ref|, "
                        f"{spec.dcpf_aggregate.p_base_floor_mw}) * 100"
                    ),
                    "branch_pass_condition": (
                        f"deviation_pct < {spec.dcpf_aggregate.p_tolerance_pct}"
                    ),
                    "metric": (
                        f"count(passing_branches) / count(in_service_branches) >= "
                        f"{spec.dcpf_aggregate.min_branch_passing_fraction}"
                    ),
                },
            },
            "hard_fail": {
                "description": ("Any single condition triggers unconditional test failure."),
                "conditions": [
                    {
                        "name": "excessive_bus_failing_fraction",
                        "description": (
                            f"More than "
                            f"{spec.dcpf_hard_fail.max_bus_failing_fraction * 100:.0f}% "
                            "of non-excluded buses fail the VA tolerance."
                        ),
                        "condition": (
                            f"count(failing_buses) / count(non_excluded_buses) > "
                            f"{spec.dcpf_hard_fail.max_bus_failing_fraction}"
                        ),
                        "threshold": spec.dcpf_hard_fail.max_bus_failing_fraction,
                    },
                    {
                        "name": "excessive_branch_failing_fraction",
                        "description": (
                            f"More than "
                            f"{spec.dcpf_hard_fail.max_branch_failing_fraction * 100:.0f}% "
                            "of in-service branches fail the P tolerance."
                        ),
                        "condition": (
                            f"count(failing_branches) / count(in_service_branches) > "
                            f"{spec.dcpf_hard_fail.max_branch_failing_fraction}"
                        ),
                        "threshold": spec.dcpf_hard_fail.max_branch_failing_fraction,
                    },
                    {
                        "name": "extreme_branch_flow_deviation",
                        "description": (
                            f"Any single branch has P deviation exceeding "
                            f"{spec.dcpf_hard_fail.p_max_deviation_pct}%. "
                            "Indicates topology or impedance error."
                        ),
                        "condition": (
                            f"max(deviation_pct) > {spec.dcpf_hard_fail.p_max_deviation_pct}"
                        ),
                        "threshold_pct": spec.dcpf_hard_fail.p_max_deviation_pct,
                    },
                ],
            },
        },
        "voltage_level_tiers": {
            "description": (
                "Informational voltage-level breakdown in verification results. "
                "Not a pass/fail gate -- the primary pass condition uses a "
                "single tolerance for all buses. This breakdown helps diagnose "
                "systematic voltage-level-correlated errors."
            ),
            "tiers": tiers_json,
        },
    }


def write_json(spec: PassConditionSpec, output_path: Path) -> None:
    """Write the pass condition specification as a JSON file.

    Args:
        spec: The specification to write.
        output_path: Path to the output JSON file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = spec_to_dict(spec)
    output_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_markdown(spec: PassConditionSpec, output_path: Path) -> None:
    """Write the pass condition specification as a human-readable markdown file.

    Args:
        spec: The specification to render.
        output_path: Path to the output markdown file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    _a = lines.append

    _a("# Pass Condition Definitions")
    _a("")
    _a(f"**Schema version:** {spec.version}")
    _a("")
    _a("This document defines the acceptance criteria for verifying a tool's")
    _a("FNM power flow results against the Phase 3 reference solutions.")
    _a("")

    # -- Summary table -------------------------------------------------------
    _a("## Summary of Thresholds")
    _a("")
    _a("| Analysis | Metric | Threshold | Unit |")
    _a("|----------|--------|-----------|------|")
    _a(
        f"| ACPF | Min passing fraction | "
        f"{spec.acpf_aggregate.min_passing_fraction * 100:.0f}% | — |"
    )
    _a(f"| ACPF | VM tolerance | {spec.acpf_aggregate.vm_tolerance_pu} | p.u. |")
    _a(f"| ACPF | VA tolerance | {spec.acpf_aggregate.va_tolerance_deg} | degrees |")
    _a(
        f"| DCPF | Min bus passing fraction | "
        f"{spec.dcpf_aggregate.min_bus_passing_fraction * 100:.0f}% | — |"
    )
    _a(f"| DCPF | VA tolerance | {spec.dcpf_aggregate.va_tolerance_deg} | degrees |")
    _a(
        f"| DCPF | Min branch passing fraction | "
        f"{spec.dcpf_aggregate.min_branch_passing_fraction * 100:.0f}% | — |"
    )
    _a(f"| DCPF | P tolerance | {spec.dcpf_aggregate.p_tolerance_pct} | % |")
    _a(f"| DCPF | P base floor | {spec.dcpf_aggregate.p_base_floor_mw} | MW |")
    _a("")

    # -- ACPF ----------------------------------------------------------------
    _a("## ACPF Pass Conditions")
    _a("")
    _a("### Aggregate")
    _a("")
    _a(
        f"A bus passes if **both** |VM_tool - VM_ref| < "
        f"{spec.acpf_aggregate.vm_tolerance_pu} p.u. **and** "
        f"|VA_tool - VA_ref| < {spec.acpf_aggregate.va_tolerance_deg} degrees."
    )
    _a(
        f"At least {spec.acpf_aggregate.min_passing_fraction * 100:.0f}% of "
        f"non-excluded buses must pass for the ACPF gate to succeed."
    )
    _a("")
    _a("### Hard-Fail Conditions")
    _a("")
    _a(
        "Any single hard-fail condition triggers unconditional test failure, "
        "regardless of aggregate statistics."
    )
    _a("")
    _a(
        f"1. **Excessive failing fraction:** More than "
        f"{spec.acpf_hard_fail.max_failing_fraction * 100:.0f}% of "
        f"non-excluded buses fail the aggregate tolerance."
    )
    _a(
        f"2. **Extreme VM deviation:** Any bus has VM deviation > "
        f"{spec.acpf_hard_fail.vm_max_deviation_pu} p.u."
    )
    _a(
        f"3. **Extreme VA deviation:** Any bus has VA deviation > "
        f"{spec.acpf_hard_fail.va_max_deviation_deg} degrees."
    )
    _a("")

    # -- DCPF ----------------------------------------------------------------
    _a("## DCPF Pass Conditions")
    _a("")
    _a("### Aggregate")
    _a("")
    _a("Two independent metrics must both pass:")
    _a("")
    _a(
        f"1. **Bus angles:** >= "
        f"{spec.dcpf_aggregate.min_bus_passing_fraction * 100:.0f}% of "
        f"non-excluded buses must have |VA_tool - VA_ref| < "
        f"{spec.dcpf_aggregate.va_tolerance_deg} degree(s)."
    )
    _a(
        f"2. **Branch flows:** >= "
        f"{spec.dcpf_aggregate.min_branch_passing_fraction * 100:.0f}% of "
        f"in-service branches must have branch flow deviation < "
        f"{spec.dcpf_aggregate.p_tolerance_pct}%."
    )
    _a("")
    _a("### Branch Flow Deviation Formula")
    _a("")
    _a("```")
    _a("deviation_pct = |P_tool - P_ref| / P_base * 100")
    _a("")
    _a(f"where P_base = max(|P_ref|, {spec.dcpf_aggregate.p_base_floor_mw})")
    _a("```")
    _a("")
    _a("**Worked example:** P_ref = 200 MW, P_tool = 210 MW.")
    _a(f"P_base = max(200, {spec.dcpf_aggregate.p_base_floor_mw}) = 200.")
    _a("deviation_pct = |210 - 200| / 200 * 100 = 5.0%. This branch passes")
    _a(f"(5.0 < {spec.dcpf_aggregate.p_tolerance_pct}).")
    _a("")
    _a("### Hard-Fail Conditions")
    _a("")
    _a(
        f"1. **Excessive bus failing fraction:** More than "
        f"{spec.dcpf_hard_fail.max_bus_failing_fraction * 100:.0f}% of "
        f"non-excluded buses fail VA tolerance."
    )
    _a(
        f"2. **Excessive branch failing fraction:** More than "
        f"{spec.dcpf_hard_fail.max_branch_failing_fraction * 100:.0f}% of "
        f"in-service branches fail P tolerance."
    )
    _a(
        f"3. **Extreme branch flow deviation:** Any branch has P deviation > "
        f"{spec.dcpf_hard_fail.p_max_deviation_pct}%."
    )
    _a("")

    # -- Outlier classification ----------------------------------------------
    _a("## Outlier Classification Rules")
    _a("")
    _a(
        "Buses that fail the aggregate tolerance are classified by probable "
        "cause. Classification does not change pass/fail -- it explains why "
        "outliers exist."
    )
    _a("")
    _a("Rules are evaluated in priority order; first match wins:")
    _a("")
    for i, rule in enumerate(spec.outlier_classification.rules, start=1):
        _a(f"### Rule {i}: `{rule.cause.value}`")
        _a("")
        _a(f"- **Applies to:** {rule.applies_to}")
        _a(f"- **Condition:** `{rule.match_condition}`")
        _a(f"- **Required data:** {', '.join(rule.required_data)}")
        _a(f"- **Description:** {rule.description}")
        _a("")

    _a("### Warning Thresholds")
    _a("")
    _a(
        f"- **Max classified fraction:** "
        f"{spec.outlier_classification.max_classified_fraction * 100:.0f}% "
        f"of non-excluded buses."
    )
    _a(
        f"- **Max unclassified fraction:** "
        f"{spec.outlier_classification.max_unclassified_fraction * 100:.0f}% "
        f"of non-excluded buses."
    )
    _a("")

    # -- Voltage level tiers -------------------------------------------------
    _a("## Voltage Level Tiers")
    _a("")
    _a("Informational voltage level breakdown in verification results. Not a pass/fail gate.")
    _a("")
    _a("| Tier | Min kV (incl.) | Max kV (excl.) |")
    _a("|------|---------------|----------------|")
    for tier in spec.voltage_level_tiers:
        max_kv_str = "∞" if math.isinf(tier.max_kv) else f"{tier.max_kv}"
        _a(f"| {tier.label} | {tier.min_kv} | {max_kv_str} |")
    _a("")

    # -- Cross-references ---------------------------------------------------
    _a("## Cross-References")
    _a("")
    _a(f"- **Bus exclusion registry (D1):** `{spec.bus_exclusion_registry_path}`")
    _a(f"- **ACPF reference (D2):** `{spec.acpf_reference_dir}`")
    _a(f"- **DCPF reference (D3):** `{spec.dcpf_reference_dir}`")
    _a("- **DCPF-vs-ACPF characterization (D4):** Validates DCPF thresholds")
    _a("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Specification loading
# ---------------------------------------------------------------------------


def load_spec(json_path: Path) -> PassConditionSpec:
    """Load a pass condition specification from a JSON file.

    Args:
        json_path: Path to the pass conditions JSON file.

    Returns:
        A PassConditionSpec populated from the JSON.

    Raises:
        FileNotFoundError: If the JSON file does not exist.
        ValueError: If required fields are missing or values are invalid.
        KeyError: If the JSON structure does not match the expected schema.
    """
    if not json_path.exists():
        raise FileNotFoundError(f"Pass conditions JSON not found: {json_path}")

    data = json.loads(json_path.read_text(encoding="utf-8"))

    # Version check
    version = data.get("$schema_version", "")
    if version != "1.0.0":
        raise ValueError(f"Schema version mismatch: expected '1.0.0', got '{version}'")

    # Parse ACPF aggregate
    acpf_agg = data["acpf"]["aggregate"]
    acpf_aggregate = ACPFAggregateThresholds(
        min_passing_fraction=float(acpf_agg["min_passing_fraction"]),
        vm_tolerance_pu=float(acpf_agg["vm_tolerance_pu"]),
        va_tolerance_deg=float(acpf_agg["va_tolerance_deg"]),
    )

    # Parse ACPF hard-fail
    acpf_hf_conditions = data["acpf"]["hard_fail"]["conditions"]
    acpf_hf_map = {c["name"]: c for c in acpf_hf_conditions}
    acpf_hard_fail = ACPFHardFailThresholds(
        max_failing_fraction=float(acpf_hf_map["excessive_failing_fraction"]["threshold"]),
        vm_max_deviation_pu=float(acpf_hf_map["extreme_vm_deviation"]["threshold_pu"]),
        va_max_deviation_deg=float(acpf_hf_map["extreme_va_deviation"]["threshold_deg"]),
    )

    # Parse DCPF aggregate
    dcpf_agg = data["dcpf"]["aggregate"]
    dcpf_aggregate = DCPFAggregateThresholds(
        min_bus_passing_fraction=float(dcpf_agg["bus_angle"]["min_passing_fraction"]),
        va_tolerance_deg=float(dcpf_agg["bus_angle"]["va_tolerance_deg"]),
        min_branch_passing_fraction=float(dcpf_agg["branch_flow"]["min_passing_fraction"]),
        p_tolerance_pct=float(dcpf_agg["branch_flow"]["p_tolerance_pct"]),
        p_base_floor_mw=float(dcpf_agg["branch_flow"]["p_base_floor_mw"]),
    )

    # Parse DCPF hard-fail
    dcpf_hf_conditions = data["dcpf"]["hard_fail"]["conditions"]
    dcpf_hf_map = {c["name"]: c for c in dcpf_hf_conditions}
    dcpf_hard_fail = DCPFHardFailThresholds(
        max_bus_failing_fraction=float(dcpf_hf_map["excessive_bus_failing_fraction"]["threshold"]),
        max_branch_failing_fraction=float(
            dcpf_hf_map["excessive_branch_failing_fraction"]["threshold"]
        ),
        p_max_deviation_pct=float(dcpf_hf_map["extreme_branch_flow_deviation"]["threshold_pct"]),
    )

    # Parse outlier rules
    outlier_data = data["acpf"]["outlier_classification"]
    rules: list[OutlierRule] = []
    for r in outlier_data["rules"]:
        rules.append(
            OutlierRule(
                cause=OutlierCause(r["cause"]),
                description=r["description"],
                required_data=r["required_data"],
                match_condition=r["match_condition"],
                applies_to=r.get("applies_to", "acpf"),
            )
        )
    warning_thresholds = outlier_data["warning_thresholds"]
    outlier_config = OutlierClassificationConfig(
        rules=rules,
        max_classified_fraction=float(warning_thresholds["max_classified_fraction"]),
        max_unclassified_fraction=float(warning_thresholds["max_unclassified_fraction"]),
    )

    # Parse voltage tiers
    tiers_data = data["voltage_level_tiers"]["tiers"]
    voltage_tiers: list[VoltageLevelTier] = []
    for t in tiers_data:
        max_kv = t.get("max_kv_exclusive")
        voltage_tiers.append(
            VoltageLevelTier(
                label=t["label"],
                min_kv=float(t["min_kv"]),
                max_kv=float("inf") if max_kv is None else float(max_kv),
            )
        )

    # Validate plausible ranges
    for frac_name, frac_val in [
        ("acpf.min_passing_fraction", acpf_aggregate.min_passing_fraction),
        ("acpf.max_failing_fraction", acpf_hard_fail.max_failing_fraction),
        ("dcpf.min_bus_passing_fraction", dcpf_aggregate.min_bus_passing_fraction),
        ("dcpf.min_branch_passing_fraction", dcpf_aggregate.min_branch_passing_fraction),
        ("dcpf.max_bus_failing_fraction", dcpf_hard_fail.max_bus_failing_fraction),
        ("dcpf.max_branch_failing_fraction", dcpf_hard_fail.max_branch_failing_fraction),
    ]:
        if not (0.0 <= frac_val <= 1.0):
            raise ValueError(f"{frac_name} must be in [0, 1], got {frac_val}")

    for tol_name, tol_val in [
        ("acpf.vm_tolerance_pu", acpf_aggregate.vm_tolerance_pu),
        ("acpf.va_tolerance_deg", acpf_aggregate.va_tolerance_deg),
        ("dcpf.va_tolerance_deg", dcpf_aggregate.va_tolerance_deg),
        ("dcpf.p_tolerance_pct", dcpf_aggregate.p_tolerance_pct),
        ("dcpf.p_base_floor_mw", dcpf_aggregate.p_base_floor_mw),
    ]:
        if tol_val <= 0:
            raise ValueError(f"{tol_name} must be > 0, got {tol_val}")

    return PassConditionSpec(
        version=version,
        acpf_aggregate=acpf_aggregate,
        acpf_hard_fail=acpf_hard_fail,
        dcpf_aggregate=dcpf_aggregate,
        dcpf_hard_fail=dcpf_hard_fail,
        outlier_classification=outlier_config,
        voltage_level_tiers=voltage_tiers,
        bus_exclusion_registry_path=data["bus_exclusion"]["registry_path"],
        acpf_reference_dir=data["acpf"]["reference_dir"],
        dcpf_reference_dir=data["dcpf"]["reference_dir"],
    )


# ---------------------------------------------------------------------------
# Voltage-level tier classification helper
# ---------------------------------------------------------------------------


def _classify_bus_tier(
    base_kv: float,
    tiers: Sequence[VoltageLevelTier],
) -> str | None:
    """Return the tier label for a bus based on its base_kv."""
    for tier in tiers:
        if tier.min_kv <= base_kv < tier.max_kv:
            return tier.label
    return None


def _compute_voltage_level_breakdown(
    bus_deviations: list[dict],
    tiers: Sequence[VoltageLevelTier],
    bus_base_kv: dict[int, float],
    has_vm: bool,
    vm_tol: float,
    va_tol: float,
) -> list[VoltageLevelBreakdown]:
    """Compute per-voltage-level-tier metric breakdown.

    Args:
        bus_deviations: List of dicts with 'bus', 'vm_dev' (or None), 'va_dev', 'passed'.
        tiers: Voltage level tiers.
        bus_base_kv: Bus number to base kV mapping.
        has_vm: True for ACPF (includes VM), False for DCPF.
        vm_tol: VM tolerance (used only for description, not re-evaluation).
        va_tol: VA tolerance.

    Returns:
        List of VoltageLevelBreakdown.
    """
    # Group buses by tier
    tier_data: dict[str, list[dict]] = {tier.label: [] for tier in tiers}

    for bd in bus_deviations:
        bus_num = bd["bus"]
        kv = bus_base_kv.get(bus_num, 0.0)
        tier_label = _classify_bus_tier(kv, tiers)
        if tier_label is not None and tier_label in tier_data:
            tier_data[tier_label].append(bd)

    result: list[VoltageLevelBreakdown] = []
    for tier in tiers:
        entries = tier_data[tier.label]
        bus_count = len(entries)
        if bus_count == 0:
            result.append(
                VoltageLevelBreakdown(
                    tier_label=tier.label,
                    bus_count=0,
                    passing_count=0,
                    passing_fraction=0.0,
                    mean_vm_deviation_pu=None,
                    mean_va_deviation_deg=0.0,
                )
            )
            continue

        passing_count = sum(1 for e in entries if e["passed"])
        passing_fraction = passing_count / bus_count

        mean_va = sum(e["va_dev"] for e in entries) / bus_count

        mean_vm: float | None = None
        if has_vm:
            mean_vm = sum(e.get("vm_dev", 0.0) for e in entries) / bus_count

        result.append(
            VoltageLevelBreakdown(
                tier_label=tier.label,
                bus_count=bus_count,
                passing_count=passing_count,
                passing_fraction=passing_fraction,
                mean_vm_deviation_pu=mean_vm,
                mean_va_deviation_deg=mean_va,
            )
        )

    return result


# ---------------------------------------------------------------------------
# ACPF verification evaluation
# ---------------------------------------------------------------------------


def evaluate_acpf(
    spec: PassConditionSpec,
    tool_buses: list[dict],
    ref_buses: list[dict],
    excluded_bus_numbers: set[int],
    bus_base_kv: dict[int, float],
    classify_outliers: bool = True,
    intermediate_data: dict[str, list[dict]] | None = None,
) -> VerificationVerdict:
    """Evaluate a tool's ACPF results against the reference.

    Args:
        spec: The pass condition specification.
        tool_buses: Tool's ACPF bus results. Each dict has keys:
            ``bus`` (int), ``VM`` (float), ``VA`` (float).
        ref_buses: Reference ACPF bus results (same schema).
        excluded_bus_numbers: Set of excluded bus numbers from D1.
        bus_base_kv: Mapping from bus number to base kV.
        classify_outliers: If True and intermediate_data is provided,
            classify outlier buses by cause.
        intermediate_data: Optional dict mapping table names to row lists
            for outlier classification.

    Returns:
        A VerificationVerdict for ACPF.
    """
    agg = spec.acpf_aggregate
    hf = spec.acpf_hard_fail

    # Filter excluded buses
    ref_filtered = [b for b in ref_buses if b["bus"] not in excluded_bus_numbers]
    tool_map = {b["bus"]: b for b in tool_buses if b["bus"] not in excluded_bus_numbers}

    total_non_excluded = len(ref_filtered)

    # Handle pathological case: all buses excluded
    if total_non_excluded == 0:
        return VerificationVerdict(
            analysis_type="acpf",
            overall_pass=False,
            hard_fail=True,
            aggregate_metrics=[
                MetricResult(
                    metric_name="acpf_vm_va_aggregate",
                    passed=False,
                    value=0.0,
                    threshold=agg.min_passing_fraction,
                    detail="No non-excluded buses to evaluate.",
                )
            ],
            hard_fail_checks=[],
            outlier_summary=None,
            voltage_level_breakdown=[],
            total_non_excluded_buses=0,
            total_in_service_branches=0,
        )

    # Compute per-bus deviations
    bus_deviations: list[dict] = []
    max_vm_dev = 0.0
    max_va_dev = 0.0
    max_vm_bus = -1
    max_va_bus = -1
    passing_count = 0
    missing_count = 0

    for ref_bus in ref_filtered:
        bus_num = ref_bus["bus"]
        tool_bus = tool_map.get(bus_num)

        if tool_bus is None:
            # Missing bus counts as failing with infinite deviation
            missing_count += 1
            bus_deviations.append(
                {
                    "bus": bus_num,
                    "vm_dev": float("inf"),
                    "va_dev": float("inf"),
                    "passed": False,
                }
            )
            # Update max deviations with a large value
            if float("inf") > max_vm_dev:
                max_vm_dev = float("inf")
                max_vm_bus = bus_num
            if float("inf") > max_va_dev:
                max_va_dev = float("inf")
                max_va_bus = bus_num
            continue

        vm_dev = abs(tool_bus["VM"] - ref_bus["VM"])
        va_dev = abs(tool_bus["VA"] - ref_bus["VA"])
        passed = vm_dev < agg.vm_tolerance_pu and va_dev < agg.va_tolerance_deg

        if passed:
            passing_count += 1

        bus_deviations.append(
            {
                "bus": bus_num,
                "vm_dev": vm_dev,
                "va_dev": va_dev,
                "passed": passed,
            }
        )

        if vm_dev > max_vm_dev:
            max_vm_dev = vm_dev
            max_vm_bus = bus_num
        if va_dev > max_va_dev:
            max_va_dev = va_dev
            max_va_bus = bus_num

    passing_fraction = passing_count / total_non_excluded
    failing_count = total_non_excluded - passing_count
    failing_fraction = failing_count / total_non_excluded

    # Aggregate metric
    agg_passed = passing_fraction >= agg.min_passing_fraction
    aggregate_metrics = [
        MetricResult(
            metric_name="acpf_vm_va_aggregate",
            passed=agg_passed,
            value=passing_fraction,
            threshold=agg.min_passing_fraction,
            detail=(
                f"{passing_count}/{total_non_excluded} buses pass "
                f"(VM<{agg.vm_tolerance_pu} AND VA<{agg.va_tolerance_deg}). "
                f"Fraction: {passing_fraction:.4f}, "
                f"required: {agg.min_passing_fraction}."
            ),
        )
    ]

    # Hard-fail checks
    hf_fraction = HardFailResult(
        check_name="excessive_failing_fraction",
        triggered=failing_fraction > hf.max_failing_fraction,
        value=failing_fraction,
        threshold=hf.max_failing_fraction,
        detail=(
            f"Failing fraction: {failing_fraction:.4f} (threshold: {hf.max_failing_fraction})."
        ),
    )
    hf_vm = HardFailResult(
        check_name="extreme_vm_deviation",
        triggered=max_vm_dev > hf.vm_max_deviation_pu,
        value=max_vm_dev,
        threshold=hf.vm_max_deviation_pu,
        detail=(
            f"Max VM deviation: {max_vm_dev:.6f} p.u. at bus {max_vm_bus} "
            f"(threshold: {hf.vm_max_deviation_pu})."
        ),
    )
    hf_va = HardFailResult(
        check_name="extreme_va_deviation",
        triggered=max_va_dev > hf.va_max_deviation_deg,
        value=max_va_dev,
        threshold=hf.va_max_deviation_deg,
        detail=(
            f"Max VA deviation: {max_va_dev:.6f} deg at bus {max_va_bus} "
            f"(threshold: {hf.va_max_deviation_deg})."
        ),
    )
    hard_fail_checks = [hf_fraction, hf_vm, hf_va]
    any_hard_fail = any(c.triggered for c in hard_fail_checks)

    # Outlier classification
    outlier_summary: OutlierSummary | None = None
    if classify_outliers and intermediate_data is not None:
        failing_buses = [bd for bd in bus_deviations if not bd["passed"]]
        cause_counts: Counter[str] = Counter()
        for fb in failing_buses:
            cause = classify_outlier_bus(
                bus_number=fb["bus"],
                rules=spec.outlier_classification.rules,
                intermediate_data=intermediate_data,
                bus_base_kv=bus_base_kv,
            )
            cause_counts[cause.value] += 1

        total_outliers = len(failing_buses)
        unclassified_count = cause_counts.get(OutlierCause.UNCLASSIFIED.value, 0)
        classified_count = total_outliers - unclassified_count
        classified_fraction = (
            classified_count / total_non_excluded if total_non_excluded > 0 else 0.0
        )
        unclassified_fraction = (
            unclassified_count / total_non_excluded if total_non_excluded > 0 else 0.0
        )

        outlier_summary = OutlierSummary(
            total_outliers=total_outliers,
            classified_count=classified_count,
            unclassified_count=unclassified_count,
            by_cause=dict(cause_counts),
            classified_fraction=classified_fraction,
            unclassified_fraction=unclassified_fraction,
            classified_warning=(
                classified_fraction > spec.outlier_classification.max_classified_fraction
            ),
            unclassified_warning=(
                unclassified_fraction > spec.outlier_classification.max_unclassified_fraction
            ),
        )

    # Voltage-level breakdown
    vl_breakdown = _compute_voltage_level_breakdown(
        bus_deviations=bus_deviations,
        tiers=spec.voltage_level_tiers,
        bus_base_kv=bus_base_kv,
        has_vm=True,
        vm_tol=agg.vm_tolerance_pu,
        va_tol=agg.va_tolerance_deg,
    )

    overall_pass = agg_passed and not any_hard_fail

    return VerificationVerdict(
        analysis_type="acpf",
        overall_pass=overall_pass,
        hard_fail=any_hard_fail,
        aggregate_metrics=aggregate_metrics,
        hard_fail_checks=hard_fail_checks,
        outlier_summary=outlier_summary,
        voltage_level_breakdown=vl_breakdown,
        total_non_excluded_buses=total_non_excluded,
        total_in_service_branches=0,
    )


# ---------------------------------------------------------------------------
# DCPF verification evaluation
# ---------------------------------------------------------------------------


def _compute_branch_deviation_pct(
    p_tool: float,
    p_ref: float,
    p_base_floor_mw: float,
) -> float:
    """Compute the DCPF branch flow deviation percentage.

    Args:
        p_tool: Tool's branch MW flow.
        p_ref: Reference branch MW flow.
        p_base_floor_mw: Floor for the denominator.

    Returns:
        Deviation percentage.
    """
    p_base = max(abs(p_ref), p_base_floor_mw)
    return abs(p_tool - p_ref) / p_base * 100.0


def evaluate_dcpf(
    spec: PassConditionSpec,
    tool_buses: list[dict],
    ref_buses: list[dict],
    tool_branches: list[dict],
    ref_branches: list[dict],
    excluded_bus_numbers: set[int],
    bus_base_kv: dict[int, float],
) -> VerificationVerdict:
    """Evaluate a tool's DCPF results against the reference.

    Args:
        spec: The pass condition specification.
        tool_buses: Tool's DCPF bus results. Each dict has keys:
            ``bus`` (int), ``VA`` (float).
        ref_buses: Reference DCPF bus results (same schema).
        tool_branches: Tool's DCPF branch results. Each dict has keys:
            ``from_bus`` (int), ``to_bus`` (int), ``ckt`` (str),
            ``P_flow_MW`` (float).
        ref_branches: Reference DCPF branch results (same schema).
        excluded_bus_numbers: Set of excluded bus numbers from D1.
        bus_base_kv: Mapping from bus number to base kV.

    Returns:
        A VerificationVerdict for DCPF.
    """
    agg = spec.dcpf_aggregate
    hf = spec.dcpf_hard_fail

    # Filter excluded buses
    ref_filtered = [b for b in ref_buses if b["bus"] not in excluded_bus_numbers]
    tool_map = {b["bus"]: b for b in tool_buses if b["bus"] not in excluded_bus_numbers}

    total_non_excluded = len(ref_filtered)

    # Handle all-excluded case
    if total_non_excluded == 0:
        return VerificationVerdict(
            analysis_type="dcpf",
            overall_pass=False,
            hard_fail=True,
            aggregate_metrics=[],
            hard_fail_checks=[],
            outlier_summary=None,
            voltage_level_breakdown=[],
            total_non_excluded_buses=0,
            total_in_service_branches=len(ref_branches),
        )

    # -- Bus VA deviations ---------------------------------------------------
    bus_deviations: list[dict] = []
    bus_passing_count = 0

    for ref_bus in ref_filtered:
        bus_num = ref_bus["bus"]
        tool_bus = tool_map.get(bus_num)

        if tool_bus is None:
            bus_deviations.append(
                {
                    "bus": bus_num,
                    "va_dev": float("inf"),
                    "passed": False,
                }
            )
            continue

        va_dev = abs(tool_bus["VA"] - ref_bus["VA"])
        passed = va_dev < agg.va_tolerance_deg

        if passed:
            bus_passing_count += 1

        bus_deviations.append(
            {
                "bus": bus_num,
                "va_dev": va_dev,
                "passed": passed,
            }
        )

    bus_passing_fraction = bus_passing_count / total_non_excluded
    bus_failing_fraction = 1.0 - bus_passing_fraction

    # -- Branch P deviations -------------------------------------------------
    # Build tool branch lookup with both key orders
    def _branch_key(from_bus: int, to_bus: int, ckt: str) -> tuple[int, int, str]:
        return (from_bus, to_bus, ckt)

    tool_branch_map: dict[tuple[int, int, str], dict] = {}
    for tb in tool_branches:
        key = _branch_key(tb["from_bus"], tb["to_bus"], tb["ckt"])
        tool_branch_map[key] = tb

    total_ref_branches = len(ref_branches)
    branch_passing_count = 0
    max_p_dev_pct = 0.0
    max_p_dev_branch: str = ""

    for rb in ref_branches:
        ref_key = _branch_key(rb["from_bus"], rb["to_bus"], rb["ckt"])
        rev_key = _branch_key(rb["to_bus"], rb["from_bus"], rb["ckt"])

        tool_br = tool_branch_map.get(ref_key)
        negate = False
        if tool_br is None:
            tool_br = tool_branch_map.get(rev_key)
            negate = True

        if tool_br is None:
            # Missing branch counts as failing
            if 100.0 > max_p_dev_pct:
                max_p_dev_pct = 100.0
                max_p_dev_branch = f"({rb['from_bus']}-{rb['to_bus']}-{rb['ckt']})"
            continue

        p_tool = -tool_br["P_flow_MW"] if negate else tool_br["P_flow_MW"]
        p_ref = rb["P_flow_MW"]
        dev_pct = _compute_branch_deviation_pct(p_tool, p_ref, agg.p_base_floor_mw)

        if dev_pct < agg.p_tolerance_pct:
            branch_passing_count += 1

        if dev_pct > max_p_dev_pct:
            max_p_dev_pct = dev_pct
            max_p_dev_branch = f"({rb['from_bus']}-{rb['to_bus']}-{rb['ckt']})"

    if total_ref_branches > 0:
        branch_passing_fraction = branch_passing_count / total_ref_branches
        branch_failing_fraction = 1.0 - branch_passing_fraction
    else:
        branch_passing_fraction = 1.0
        branch_failing_fraction = 0.0

    # -- Aggregate metrics ---------------------------------------------------
    bus_metric_passed = bus_passing_fraction >= agg.min_bus_passing_fraction
    branch_metric_passed = branch_passing_fraction >= agg.min_branch_passing_fraction

    aggregate_metrics = [
        MetricResult(
            metric_name="dcpf_bus_va_aggregate",
            passed=bus_metric_passed,
            value=bus_passing_fraction,
            threshold=agg.min_bus_passing_fraction,
            detail=(
                f"{bus_passing_count}/{total_non_excluded} buses pass "
                f"(VA<{agg.va_tolerance_deg}). "
                f"Fraction: {bus_passing_fraction:.4f}."
            ),
        ),
        MetricResult(
            metric_name="dcpf_branch_p_aggregate",
            passed=branch_metric_passed,
            value=branch_passing_fraction,
            threshold=agg.min_branch_passing_fraction,
            detail=(
                f"{branch_passing_count}/{total_ref_branches} branches pass "
                f"(P<{agg.p_tolerance_pct}%). "
                f"Fraction: {branch_passing_fraction:.4f}."
            ),
        ),
    ]

    # -- Hard-fail checks ----------------------------------------------------
    hf_bus = HardFailResult(
        check_name="excessive_bus_failing_fraction",
        triggered=bus_failing_fraction > hf.max_bus_failing_fraction,
        value=bus_failing_fraction,
        threshold=hf.max_bus_failing_fraction,
        detail=(
            f"Bus failing fraction: {bus_failing_fraction:.4f} "
            f"(threshold: {hf.max_bus_failing_fraction})."
        ),
    )
    hf_branch = HardFailResult(
        check_name="excessive_branch_failing_fraction",
        triggered=branch_failing_fraction > hf.max_branch_failing_fraction,
        value=branch_failing_fraction,
        threshold=hf.max_branch_failing_fraction,
        detail=(
            f"Branch failing fraction: {branch_failing_fraction:.4f} "
            f"(threshold: {hf.max_branch_failing_fraction})."
        ),
    )
    hf_max_p = HardFailResult(
        check_name="extreme_branch_flow_deviation",
        triggered=max_p_dev_pct > hf.p_max_deviation_pct,
        value=max_p_dev_pct,
        threshold=hf.p_max_deviation_pct,
        detail=(
            f"Max branch P deviation: {max_p_dev_pct:.2f}% at branch "
            f"{max_p_dev_branch} (threshold: {hf.p_max_deviation_pct}%)."
        ),
    )
    hard_fail_checks = [hf_bus, hf_branch, hf_max_p]
    any_hard_fail = any(c.triggered for c in hard_fail_checks)

    # Voltage-level breakdown
    vl_breakdown = _compute_voltage_level_breakdown(
        bus_deviations=bus_deviations,
        tiers=spec.voltage_level_tiers,
        bus_base_kv=bus_base_kv,
        has_vm=False,
        vm_tol=0.0,
        va_tol=agg.va_tolerance_deg,
    )

    overall_pass = bus_metric_passed and branch_metric_passed and not any_hard_fail

    return VerificationVerdict(
        analysis_type="dcpf",
        overall_pass=overall_pass,
        hard_fail=any_hard_fail,
        aggregate_metrics=aggregate_metrics,
        hard_fail_checks=hard_fail_checks,
        outlier_summary=None,
        voltage_level_breakdown=vl_breakdown,
        total_non_excluded_buses=total_non_excluded,
        total_in_service_branches=total_ref_branches,
    )


# ---------------------------------------------------------------------------
# Outlier classification helpers
# ---------------------------------------------------------------------------


def _has_switched_shunt(
    bus_number: int,
    intermediate_data: dict[str, list[dict]],
) -> bool:
    """Check if bus has a switched shunt device."""
    shunts = intermediate_data.get("switched_shunt", [])
    for s in shunts:
        # Look for bus number in common field names
        s_bus = s.get("I") or s.get("bus") or s.get("bus_number")
        if s_bus is not None and int(s_bus) == bus_number:
            return True
    return False


def _generator_at_q_limit(
    bus_number: int,
    intermediate_data: dict[str, list[dict]],
    ref_generators: list[dict] | None,
    tolerance_mvar: float = 1.0,
) -> bool:
    """Check if any generator at this bus is at a Q limit."""
    if ref_generators is None:
        return False

    # Build set of generators at this bus from intermediate data
    gen_rows = intermediate_data.get("generator", [])
    bus_has_gen = False
    for g in gen_rows:
        g_bus = g.get("I") or g.get("bus") or g.get("bus_number")
        if g_bus is not None and int(g_bus) == bus_number:
            bus_has_gen = True
            break

    if not bus_has_gen:
        return False

    # Check reference generator Q vs limits
    for rg in ref_generators:
        rg_bus = rg.get("bus") or rg.get("I")
        if rg_bus is not None and int(rg_bus) == bus_number:
            qg = float(rg.get("QG", rg.get("Q", 0.0)))
            qmax = float(rg.get("QMAX", rg.get("Qmax", float("inf"))))
            qmin = float(rg.get("QMIN", rg.get("Qmin", float("-inf"))))
            if abs(qg - qmax) < tolerance_mvar or abs(qg - qmin) < tolerance_mvar:
                return True

    return False


def _is_slack_or_neighbor(
    bus_number: int,
    network_adjacency: dict[int, set[int]] | None,
    slack_bus: int | None,
    max_hops: int = 2,
) -> bool:
    """Check if bus is the slack bus or within max_hops of it."""
    if slack_bus is None or network_adjacency is None:
        return False

    if bus_number == slack_bus:
        return True

    # BFS from slack up to max_hops
    visited: set[int] = {slack_bus}
    frontier: set[int] = {slack_bus}
    for _ in range(max_hops):
        next_frontier: set[int] = set()
        for node in frontier:
            for neighbor in network_adjacency.get(node, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.add(neighbor)
        frontier = next_frontier

    return bus_number in visited


def _is_tap_regulated_bus(
    bus_number: int,
    intermediate_data: dict[str, list[dict]],
) -> bool:
    """Check if bus is regulated by a tap-changing transformer (CONT field)."""
    transformers = intermediate_data.get("transformer", [])
    for t in transformers:
        cont = t.get("CONT") or t.get("cont")
        stat = t.get("STAT") or t.get("stat") or t.get("status")
        if cont is not None and int(cont) == bus_number:
            if stat is None or int(stat) == 1:
                return True
    return False


def _is_island_boundary(
    bus_number: int,
    network_adjacency: dict[int, set[int]] | None,
    bus_base_kv: dict[int, float] | None,
    max_degree: int = 2,
    max_kv: float = 69.0,
) -> bool:
    """Check if bus is at an island boundary (low degree + low voltage)."""
    if network_adjacency is None or bus_base_kv is None:
        return False

    degree = len(network_adjacency.get(bus_number, set()))
    kv = bus_base_kv.get(bus_number, 0.0)

    return degree <= max_degree and kv < max_kv


def classify_outlier_bus(
    bus_number: int,
    rules: list[OutlierRule],
    intermediate_data: dict[str, list[dict]],
    ref_generators: list[dict] | None = None,
    network_adjacency: dict[int, set[int]] | None = None,
    slack_bus: int | None = None,
    bus_base_kv: dict[int, float] | None = None,
) -> OutlierCause:
    """Classify a single outlier bus by evaluating rules in priority order.

    Args:
        bus_number: The bus to classify.
        rules: Ordered list of classification rules.
        intermediate_data: Dict mapping table names to row lists.
        ref_generators: Reference ACPF generator results (for Q-limit check).
        network_adjacency: Network adjacency list.
        slack_bus: Slack bus number.
        bus_base_kv: Bus number to base kV mapping.

    Returns:
        The OutlierCause assigned to this bus.
    """
    for rule in rules:
        matched = False

        if rule.cause == OutlierCause.SWITCHED_SHUNT:
            matched = _has_switched_shunt(bus_number, intermediate_data)
        elif rule.cause == OutlierCause.Q_LIMIT:
            matched = _generator_at_q_limit(bus_number, intermediate_data, ref_generators)
        elif rule.cause == OutlierCause.SLACK_DISTRIBUTION:
            matched = _is_slack_or_neighbor(bus_number, network_adjacency, slack_bus)
        elif rule.cause == OutlierCause.TAP_POSITION:
            matched = _is_tap_regulated_bus(bus_number, intermediate_data)
        elif rule.cause == OutlierCause.ISLAND_BOUNDARY:
            matched = _is_island_boundary(bus_number, network_adjacency, bus_base_kv)

        if matched:
            return rule.cause

    return OutlierCause.UNCLASSIFIED


# ---------------------------------------------------------------------------
# Output orchestration
# ---------------------------------------------------------------------------


def generate_pass_conditions(
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    """Top-level function to generate both JSON and markdown pass condition files.

    Args:
        output_dir: Directory for output files. Defaults to
            ``data/fnm/reference/``.

    Returns:
        Tuple of (json_path, markdown_path).
    """
    if output_dir is None:
        output_dir = Path("data/fnm/reference")

    output_dir.mkdir(parents=True, exist_ok=True)
    spec = build_pass_condition_spec()

    json_path = output_dir / "pass_conditions.json"
    md_path = output_dir / "pass_conditions.md"

    write_json(spec, json_path)
    write_markdown(spec, md_path)

    return json_path, md_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for pass condition generation.

    Args:
        argv: Command-line arguments. If None, reads from sys.argv[1:].
    """
    parser = argparse.ArgumentParser(
        description="Generate pass condition definitions for FNM verification."
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: data/fnm/reference/).",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    json_path, md_path = generate_pass_conditions(output_dir=args.output_dir)

    spec = build_pass_condition_spec()
    acpf = spec.acpf_aggregate
    dcpf = spec.dcpf_aggregate
    acpf_hf = spec.acpf_hard_fail
    dcpf_hf = spec.dcpf_hard_fail

    print(
        f"ACPF: min_passing={acpf.min_passing_fraction * 100:.0f}%, "
        f"VM<{acpf.vm_tolerance_pu} p.u., VA<{acpf.va_tolerance_deg} deg"
    )
    print(
        f"DCPF: min_bus_passing={dcpf.min_bus_passing_fraction * 100:.0f}% "
        f"VA<{dcpf.va_tolerance_deg} deg, "
        f"min_branch_passing={dcpf.min_branch_passing_fraction * 100:.0f}% "
        f"P<{dcpf.p_tolerance_pct}%"
    )
    print(
        f"Hard-fail thresholds: ACPF VM>{acpf_hf.vm_max_deviation_pu}/"
        f"VA>{acpf_hf.va_max_deviation_deg}, "
        f"DCPF P>{dcpf_hf.p_max_deviation_pct}%"
    )
    print(f"Outlier rules: {len(spec.outlier_classification.rules)} classification rules")
    print(f"Voltage tiers: {len(spec.voltage_level_tiers)} informational tiers")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")


if __name__ == "__main__":
    main()
