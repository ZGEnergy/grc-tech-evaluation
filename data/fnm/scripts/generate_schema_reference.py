"""Generate the Intermediate Format Schema Reference markdown document.

This script reads the Phase 1 D7 schema definitions programmatically and
produces data/fnm/docs/intermediate-schema.md with full semantic descriptions,
worked examples, and evaluate-tool guidance for every field.

Usage (inside devcontainer):
    cd /workspace/data
    uv run python -m fnm.scripts.generate_schema_reference
"""

from __future__ import annotations

from pathlib import Path

from fnm.scripts.intermediate_schema import (
    FieldSpec,
    TableSchema,
    get_table_schemas,
)

# ---------------------------------------------------------------------------
# Semantic descriptions, evaluate-tool guidance, and worked examples
# ---------------------------------------------------------------------------
# These are hand-authored domain knowledge keyed by (record_type, field_name).
# The generator merges them with the machine-readable schema metadata.

_UNIT_MAP: dict[str, str] = {
    "": "\u2014",
    "kV": "kV",
    "pu": "pu",
    "deg": "deg",
    "MW": "MW",
    "MVAR": "MVAR",
    "MVA": "MVA",
    "A": "A",
    "ohm": "ohm",
    "%": "%",
}


def _unit(f: FieldSpec) -> str:
    return _UNIT_MAP.get(f.unit, f.unit if f.unit else "\u2014")


def _default_str(f: FieldSpec) -> str:
    if f.default_value is None:
        return "none"
    if isinstance(f.default_value, str):
        if f.default_value.strip() == "":
            return '`"' + " " * len(f.default_value) + '"`' if f.default_value else '`""`'
        return f'`"{f.default_value}"`'
    return str(f.default_value)


def _range_str(f: FieldSpec) -> str:
    if f.valid_range is None:
        return "\u2014"
    lo, hi = f.valid_range
    lo_s = str(lo) if lo is not None else "\u2014"
    hi_s = str(hi) if hi is not None else "\u2014"
    return f"{lo_s}\u2013{hi_s}"


# ---------------------------------------------------------------------------
# Per-field semantic descriptions and guidance (hand-authored)
# ---------------------------------------------------------------------------

# fmt: off
_SEMANTIC: dict[str, dict[str, tuple[str, str, str]]] = {
    # (record_type, field_name) -> (semantic_desc, expected_range, guidance)
    "Bus": {
        "I": (
            "Unique bus number identifying this node in the network topology. "
            "All branch, generator, load, and shunt records reference buses by this number.",
            "10000\u201399999 for large networks",
            "Verify I is a positive integer preserved exactly; loss of bus number destroys topology"
        ),
        "NAME": (
            "Alphanumeric bus name, up to 12 characters, padded with trailing spaces. "
            "Used for human-readable identification in reports and diagrams.",
            "\u2014",
            "Verify NAME is preserved including trailing whitespace; "
            "compare after stripping only if the tool normalizes whitespace"
        ),
        "BASKV": (
            "Bus base voltage in kV. Defines the voltage class for this bus and is the "
            "reference for all per-unit voltage calculations at this bus. A value of 0.0 "
            "is the PSS/E default but is physically meaningless for real network buses.",
            "69\u2013500 for transmission",
            "Verify BASKV > 0 for all buses with IDE != 4 (non-isolated); "
            "verify preserved to at least 1 decimal place"
        ),
        "IDE": (
            "Bus type code: 1=PQ (load), 2=PV (generator), 3=swing (reference), "
            "4=isolated (disconnected). Determines the power flow solution method at this bus.",
            "1\u20134",
            "Verify IDE is one of {1, 2, 3, 4} and matches the source exactly; "
            "confirm bus type code maps to the tool's equivalent enum without silent coercion"
        ),
        "AREA": (
            "Area number to which this bus is assigned. Areas define interchange "
            "control regions in the power flow solution.",
            "1\u201350 for large ISOs",
            "Verify AREA references a valid area number in the area table"
        ),
        "ZONE": (
            "Zone number for geographic or administrative grouping. Zones provide "
            "finer-grained grouping than areas, used in reporting and load allocation.",
            "1\u201350",
            "Verify ZONE references a valid zone number in the zone table"
        ),
        "OWNER": (
            "Owner number identifying the entity that owns this bus. Used for "
            "ownership tracking and cost allocation.",
            "1\u2013200",
            "Verify OWNER references a valid owner number in the owner table"
        ),
        "VM": (
            "Bus voltage magnitude in per-unit on the bus base voltage (BASKV). "
            "In a solved case, this represents the steady-state voltage. "
            "In an unsolved case, this is the initial voltage guess.",
            "0.95\u20131.05 for solved case",
            "Verify VM preserved to at least 4 decimal places; "
            "values outside 0.9\u20131.1 in a solved case indicate convergence issues"
        ),
        "VA": (
            "Bus voltage angle in degrees. The swing bus angle is the reference "
            "(typically 0.0). All other angles are relative to the swing bus.",
            "-180\u2013180",
            "Verify VA preserved to at least 2 decimal places; "
            "swing bus (IDE=3) should have VA near 0.0"
        ),
        "NVHI": (
            "Normal operating voltage high limit in per-unit. Used by OPF and "
            "monitoring functions to flag voltage violations.",
            "1.05\u20131.10",
            "If field is at PSS/E default (1.1), tool may omit \u2014 do not penalize"
        ),
        "NVLO": (
            "Normal operating voltage low limit in per-unit. Buses with voltage "
            "below this limit are flagged as voltage violations.",
            "0.90\u20130.95",
            "If field is at PSS/E default (0.9), tool may omit \u2014 do not penalize"
        ),
        "EVHI": (
            "Emergency voltage high limit in per-unit. Applied during contingency "
            "analysis to allow wider voltage tolerance under emergency conditions.",
            "1.05\u20131.10",
            "If field is at PSS/E default (1.1), tool may omit \u2014 do not penalize"
        ),
        "EVLO": (
            "Emergency voltage low limit in per-unit. More relaxed than normal "
            "low limit, applied during contingency analysis.",
            "0.85\u20130.95",
            "If field is at PSS/E default (0.9), tool may omit \u2014 do not penalize"
        ),
    },
    "Load": {
        "I": (
            "Bus number at which this load is connected. Multiple loads can exist "
            "at the same bus, distinguished by ID.",
            "10000\u201399999",
            "Verify I references a valid bus number in the bus table"
        ),
        "ID": (
            "Two-character load identifier. Together with I, forms the composite "
            "primary key. Default '1 ' (one followed by space).",
            "\u2014",
            "Verify ID is preserved as a 2-character string including trailing space"
        ),
        "STATUS": (
            "Load status: 1=in-service (included in power flow), "
            "0=out-of-service (excluded from power flow solution).",
            "0\u20131",
            "Verify STATUS is one of {0, 1} and matches the source exactly"
        ),
        "AREA": (
            "Area number for this load, defaults to the bus's area. "
            "Used for area interchange calculations.",
            "1\u201350",
            "Verify AREA is a positive integer; if at default (1), tool may inherit from bus"
        ),
        "ZONE": (
            "Zone number for this load, defaults to the bus's zone.",
            "1\u201350",
            "Verify ZONE is a positive integer; if at default (1), tool may inherit from bus"
        ),
        "PL": (
            "Constant-power active load in MW. The primary real power demand "
            "at this bus. Positive values consume power.",
            "0\u20135000",
            "Verify PL preserved to at least 2 decimal places; "
            "sign convention: positive = consumption"
        ),
        "QL": (
            "Constant-power reactive load in MVAR. Positive values consume "
            "reactive power (lagging power factor).",
            "-500\u20131000",
            "Verify QL preserved to at least 2 decimal places; "
            "sign convention: positive = lagging (inductive)"
        ),
        "IP": (
            "Constant-current active load component in MW at 1.0 pu voltage. "
            "Scales linearly with voltage magnitude.",
            "\u2014",
            "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"
        ),
        "IQ": (
            "Constant-current reactive load component in MVAR at 1.0 pu voltage.",
            "\u2014",
            "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"
        ),
        "YP": (
            "Constant-admittance active load component in MW at 1.0 pu voltage. "
            "Scales with voltage squared.",
            "\u2014",
            "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"
        ),
        "YQ": (
            "Constant-admittance reactive load component in MVAR at 1.0 pu voltage.",
            "\u2014",
            "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"
        ),
        "OWNER": (
            "Owner number for this load.",
            "1\u2013200",
            "If field is at PSS/E default (1), tool may omit \u2014 do not penalize"
        ),
        "SCALE": (
            "Load scaling flag: 1=load participates in scaling, 0=fixed load. "
            "Controls whether the load is adjusted during area interchange scaling.",
            "0\u20131",
            "If field is at PSS/E default (1), tool may omit \u2014 do not penalize"
        ),
    },
    "Fixed Shunt": {
        "I": (
            "Bus number at which this fixed shunt is connected.",
            "10000\u201399999",
            "Verify I references a valid bus number in the bus table"
        ),
        "ID": (
            "Two-character shunt identifier. Together with I, forms the composite "
            "primary key.",
            "\u2014",
            "Verify ID is preserved as a 2-character string including trailing space"
        ),
        "STATUS": (
            "Shunt status: 1=in-service, 0=out-of-service.",
            "0\u20131",
            "Verify STATUS is one of {0, 1} and matches the source exactly"
        ),
        "GL": (
            "Active component of shunt admittance to ground in MW at 1.0 pu voltage. "
            "Positive GL represents real power consumption (resistive losses).",
            "\u2014",
            "Verify GL preserved to at least 4 decimal places; "
            "most fixed shunts have GL=0 (purely reactive)"
        ),
        "BL": (
            "Reactive component of shunt admittance to ground in MVAR at 1.0 pu voltage. "
            "Positive BL is capacitive (generates reactive power), "
            "negative BL is inductive (absorbs reactive power).",
            "-500\u2013500",
            "Verify BL is positive for capacitive shunts, negative for inductive; "
            "verify preserved to at least 2 decimal places"
        ),
    },
    "Generator": {
        "I": (
            "Bus number at which this generator is connected.",
            "10000\u201399999",
            "Verify I references a valid bus number in the bus table"
        ),
        "ID": (
            "Two-character machine identifier. Together with I, forms the composite "
            "primary key. Allows multiple generators at the same bus.",
            "\u2014",
            "Verify ID is preserved as a 2-character string including trailing space"
        ),
        "PG": (
            "Active power output of the generator in MW. Positive values "
            "indicate generation. Negative values indicate a synchronous condenser "
            "consuming real power.",
            "50\u20131000 for large units",
            "Verify PG preserved to at least 2 decimal places"
        ),
        "QG": (
            "Reactive power output of the generator in MVAR. Determined by the "
            "power flow solution within the QB\u2013QT limits.",
            "-500\u2013500",
            "Verify QG preserved to at least 2 decimal places"
        ),
        "QT": (
            "Maximum reactive power output in MVAR. Upper limit for the "
            "generator's reactive capability curve.",
            "0\u20131000",
            "Verify QT preserved to at least 1 decimal place; "
            "default 9999.0 indicates unconstrained"
        ),
        "QB": (
            "Minimum reactive power output in MVAR. Lower limit for the "
            "generator's reactive capability.",
            "-1000\u20130",
            "Verify QB preserved to at least 1 decimal place; "
            "default -9999.0 indicates unconstrained"
        ),
        "VS": (
            "Voltage setpoint for voltage-regulating generators in per-unit. "
            "The generator adjusts reactive output to maintain this voltage at "
            "the regulated bus (local or remote via IREG).",
            "0.95\u20131.10",
            "Verify VS preserved to at least 4 decimal places"
        ),
        "IREG": (
            "**[preservation-critical]** Remote regulated bus number. "
            "0=local voltage regulation (at bus I). Non-zero=remote bus whose "
            "voltage is controlled by this generator. Critical for correct "
            "voltage regulation topology in power flow.",
            "0 or valid bus number",
            "MUST be preserved exactly; verify IREG=0 means local regulation, "
            "not missing; loss of remote regulation topology is a fidelity finding"
        ),
        "MBASE": (
            "Machine MVA base for per-unit impedance conversion. Generator "
            "impedances ZR, ZX are on this base.",
            "50\u20131500",
            "Verify MBASE preserved to at least 1 decimal place"
        ),
        "ZR": (
            "Machine resistance in per-unit on MBASE. Part of the generator's "
            "internal impedance model for short-circuit studies.",
            "\u2014",
            "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"
        ),
        "ZX": (
            "Machine reactance in per-unit on MBASE. Sub-transient or transient "
            "reactance used in short-circuit calculations.",
            "0.1\u20130.4",
            "If field is at PSS/E default (1.0), tool may omit \u2014 do not penalize"
        ),
        "RT": (
            "Step-up transformer resistance in per-unit on MBASE.",
            "\u2014",
            "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"
        ),
        "XT": (
            "Step-up transformer reactance in per-unit on MBASE.",
            "\u2014",
            "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"
        ),
        "GTAP": (
            "Step-up transformer off-nominal turns ratio in per-unit on bus base kV.",
            "0.9\u20131.1",
            "If field is at PSS/E default (1.0), tool may omit \u2014 do not penalize"
        ),
        "STAT": (
            "Generator status: 1=in-service, 0=out-of-service.",
            "0\u20131",
            "Verify STAT is one of {0, 1} and matches the source exactly"
        ),
        "RMPCT": (
            "Percent of total MVAR range allocated to remote voltage regulation.",
            "0\u2013100",
            "If field is at PSS/E default (100.0), tool may omit \u2014 do not penalize"
        ),
        "PT": (
            "Maximum active power output in MW.",
            "50\u20132000",
            "Verify PT preserved to at least 1 decimal place; "
            "default 9999.0 indicates unconstrained"
        ),
        "PB": (
            "Minimum active power output in MW.",
            "-100\u20130",
            "Verify PB preserved to at least 1 decimal place; "
            "default -9999.0 indicates unconstrained"
        ),
        "O1": (
            "Owner number 1.",
            "1\u2013200",
            "If field is at PSS/E default (1), tool may omit \u2014 do not penalize"
        ),
        "F1": (
            "Fraction of generator owned by owner 1.",
            "0.0\u20131.0",
            "If field is at PSS/E default (1.0), tool may omit \u2014 do not penalize"
        ),
        "O2": ("Owner number 2.", "\u2014",
               "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"),
        "F2": ("Fraction owned by owner 2.", "0.0\u20131.0",
               "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"),
        "O3": ("Owner number 3.", "\u2014",
               "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"),
        "F3": ("Fraction owned by owner 3.", "0.0\u20131.0",
               "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"),
        "O4": ("Owner number 4.", "\u2014",
               "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"),
        "F4": ("Fraction owned by owner 4.", "0.0\u20131.0",
               "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"),
        "WMOD": (
            "Wind machine reactive power control mode. 0=standard, "
            "1=constant power factor, 2=constant Q, 3=constant voltage.",
            "0\u20133",
            "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"
        ),
        "WPF": (
            "Wind machine power factor for WMOD=1 mode.",
            "0.8\u20131.0",
            "If field is at PSS/E default (1.0), tool may omit \u2014 do not penalize"
        ),
    },
    "Branch": {
        "I": (
            "From-bus number. Together with J and CKT, forms the branch's composite "
            "primary key.",
            "10000\u201399999",
            "Verify I references a valid bus number in the bus table"
        ),
        "J": (
            "To-bus number. Branch connects bus I to bus J. The sign of J does not "
            "matter for topology (absolute value is used).",
            "10000\u201399999",
            "Verify J references a valid bus number in the bus table"
        ),
        "CKT": (
            "Two-character circuit identifier allowing parallel branches between "
            "the same bus pair.",
            "\u2014",
            "Verify CKT is preserved as a 2-character string including trailing space"
        ),
        "R": (
            "Branch resistance in per-unit on system MVA base (SBASE) and bus "
            "base voltage. For transmission lines, R is typically much smaller "
            "than X (R/X ratio < 0.5).",
            "0.0001\u20130.1",
            "Verify R preserved to at least 5 decimal places; "
            "verify R < X for transmission lines (R/X < 1.0)"
        ),
        "X": (
            "Branch reactance in per-unit on system MVA base. The dominant "
            "impedance component for transmission lines. X must be non-zero "
            "for in-service branches.",
            "0.001\u20130.5",
            "Verify X is non-zero for all in-service branches (ST=1); "
            "verify X preserved to at least 5 decimal places"
        ),
        "B": (
            "Total branch charging susceptance in per-unit on system MVA base. "
            "For overhead lines, B is proportional to line length and voltage. "
            "For short lines, B may be 0.",
            "0.0\u20135.0",
            "Verify B preserved to at least 5 decimal places; "
            "B=0 is valid for short lines and cables"
        ),
        "RATEA": (
            "Normal thermal rating in MVA (Rating A). Used for continuous "
            "loading monitoring.",
            "0\u20133000",
            "Verify RATEA preserved to at least 1 decimal place; "
            "0.0 means no limit (not monitored)"
        ),
        "RATEB": (
            "Emergency thermal rating in MVA (Rating B). Short-term overload limit.",
            "0\u20134000",
            "Verify RATEB preserved to at least 1 decimal place; "
            "0.0 means no limit"
        ),
        "RATEC": (
            "Long-term emergency rating in MVA (Rating C).",
            "0\u20135000",
            "Verify RATEC preserved to at least 1 decimal place; "
            "0.0 means no limit"
        ),
        "GI": ("Line shunt conductance at from-bus end in per-unit.", "\u2014",
               "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"),
        "BI": ("Line shunt susceptance at from-bus end in per-unit.", "\u2014",
               "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"),
        "GJ": ("Line shunt conductance at to-bus end in per-unit.", "\u2014",
               "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"),
        "BJ": ("Line shunt susceptance at to-bus end in per-unit.", "\u2014",
               "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"),
        "ST": (
            "Branch status: 1=in-service, 0=out-of-service. "
            "Out-of-service branches are excluded from the admittance matrix.",
            "0\u20131",
            "Verify ST is one of {0, 1} and matches the source exactly"
        ),
        "MET": (
            "Metered end flag: 1=from-bus (I), 2=to-bus (J). Determines "
            "which end is used for loss allocation.",
            "1\u20132",
            "If field is at PSS/E default (1), tool may omit \u2014 do not penalize"
        ),
        "LEN": (
            "Line length in user-selected units. Informational field, not "
            "used in power flow calculations.",
            "\u2014",
            "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"
        ),
        "O1": ("Owner number 1.", "1\u2013200",
               "If field is at PSS/E default (1), tool may omit \u2014 do not penalize"),
        "F1": ("Fraction owned by owner 1.", "0.0\u20131.0",
               "If field is at PSS/E default (1.0), tool may omit \u2014 do not penalize"),
        "O2": ("Owner number 2.", "\u2014",
               "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"),
        "F2": ("Fraction owned by owner 2.", "0.0\u20131.0",
               "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"),
        "O3": ("Owner number 3.", "\u2014",
               "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"),
        "F3": ("Fraction owned by owner 3.", "0.0\u20131.0",
               "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"),
        "O4": ("Owner number 4.", "\u2014",
               "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"),
        "F4": ("Fraction owned by owner 4.", "0.0\u20131.0",
               "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"),
    },
    "Transformer": {
        "I": ("Winding 1 (primary) bus number.", "10000\u201399999",
              "Verify I references a valid bus number in the bus table"),
        "J": ("Winding 2 (secondary) bus number.", "10000\u201399999",
              "Verify J references a valid bus number in the bus table"),
        "K": (
            "**[preservation-critical]** Winding 3 bus number. K=0 indicates a 2-winding "
            "transformer; K!=0 indicates a 3-winding transformer. This field determines "
            "the topology interpretation for all subsequent winding data.",
            "0 or valid bus number",
            "MUST be preserved exactly; K=0 vs K!=0 changes transformer topology "
            "interpretation entirely; loss is a critical fidelity finding"
        ),
        "CKT": ("Circuit identifier for parallel transformers.", "\u2014",
                "Verify CKT is preserved as a 2-character string including trailing space"),
        "CW": (
            "**[preservation-critical]** Winding data I/O code controlling how WINDV1/2/3 "
            "are interpreted: 1=turns ratio in pu on bus base kV, 2=voltage in kV, "
            "3=turns ratio in pu on nominal kV.",
            "1\u20133",
            "MUST be preserved exactly; CW determines the interpretation of all "
            "winding voltage/turns-ratio fields; loss corrupts impedance calculations"
        ),
        "CZ": (
            "**[preservation-critical]** Impedance data I/O code: 1=pu on system base, "
            "2=pu on winding MVA/kV base, 3=ohms/kV load loss.",
            "1\u20133",
            "MUST be preserved exactly; CZ determines per-unit base for R and X fields"
        ),
        "CM": (
            "**[preservation-critical]** Magnetizing admittance I/O code: "
            "1=pu on system base, 2=no-load loss/exciting current.",
            "1\u20132",
            "MUST be preserved exactly; CM determines interpretation of MAG1/MAG2"
        ),
        "MAG1": ("Magnetizing conductance or no-load loss, depending on CM.", "\u2014",
                 "Verify MAG1 preserved to at least 5 decimal places"),
        "MAG2": ("Magnetizing susceptance or exciting current, depending on CM.", "\u2014",
                 "Verify MAG2 preserved to at least 5 decimal places"),
        "NMETR": ("Non-metered end code.", "\u2014",
                  "If field is at PSS/E default (2), tool may omit \u2014 do not penalize"),
        "NAME": ("Transformer name, up to 12 characters.", "\u2014",
                 "Verify NAME is preserved including trailing whitespace"),
        "STAT": (
            "Transformer status: 0=out-of-service, 1=in-service, 2=winding 2 out, "
            "3=winding 3 out, 4=winding 2 and 3 out.",
            "0\u20134",
            "Verify STAT is one of {0, 1, 2, 3, 4} and matches the source exactly"
        ),
        "O1": ("Owner number 1.", "1\u2013200",
               "If field is at PSS/E default (1), tool may omit \u2014 do not penalize"),
        "F1": ("Fraction by owner 1.", "0.0\u20131.0",
               "If field is at PSS/E default (1.0), tool may omit \u2014 do not penalize"),
        "O2": ("Owner 2.", "\u2014",
               "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"),
        "F2": ("Fraction by owner 2.", "0.0\u20131.0",
               "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"),
        "O3": ("Owner 3.", "\u2014",
               "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"),
        "F3": ("Fraction by owner 3.", "0.0\u20131.0",
               "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"),
        "O4": ("Owner 4.", "\u2014",
               "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"),
        "F4": ("Fraction by owner 4.", "0.0\u20131.0",
               "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"),
        "VECGRP": ("Vector group designation (12 chars).", "\u2014",
                   "If field is at PSS/E default (blank), tool may omit \u2014 do not penalize"),
        "R1_2": (
            "Resistance of winding 1\u20132 pair, interpretation depends on CZ.",
            "0.0\u20130.1",
            "Verify R1_2 preserved to at least 5 decimal places",
        ),
        "X1_2": (
            "Reactance of winding 1\u20132 pair, interpretation depends on CZ.",
            "0.01\u20130.5",
            "Verify X1_2 is non-zero for in-service transformers; "
            "verify preserved to at least 5 decimal places",
        ),
        "SBASE1_2": ("MVA base for winding 1\u20132 impedance.", "50\u20132000",
                     "Verify SBASE1_2 preserved to at least 1 decimal place"),
        "R2_3": ("Resistance of winding 2\u20133 pair (3W only).", "\u2014",
                 "Verify non-null when K != 0; if K=0, tool may omit"),
        "X2_3": ("Reactance of winding 2\u20133 pair (3W only).", "\u2014",
                 "Verify non-null when K != 0; if K=0, tool may omit"),
        "SBASE2_3": ("MVA base for winding 2\u20133 (3W only).", "\u2014",
                     "Verify non-null when K != 0; if K=0, tool may omit"),
        "R3_1": ("Resistance of winding 3\u20131 pair (3W only).", "\u2014",
                 "Verify non-null when K != 0; if K=0, tool may omit"),
        "X3_1": ("Reactance of winding 3\u20131 pair (3W only).", "\u2014",
                 "Verify non-null when K != 0; if K=0, tool may omit"),
        "SBASE3_1": ("MVA base for winding 3\u20131 (3W only).", "\u2014",
                     "Verify non-null when K != 0; if K=0, tool may omit"),
        "VMSTAR": ("Star-point bus voltage magnitude for 3W transformers.", "\u2014",
                   "If field is at PSS/E default (1.0), tool may omit \u2014 do not penalize"),
        "ANSTAR": ("Star-point bus voltage angle for 3W transformers.", "\u2014",
                   "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"),
        "WINDV1": (
            "**[preservation-critical]** Winding 1 off-nominal turns ratio or voltage. "
            "Interpretation depends on CW code.",
            "0.9\u20131.1 (pu) or kV",
            "MUST be preserved exactly to at least 5 decimal places; "
            "loss corrupts transformer model"
        ),
        "NOMV1": (
            "**[preservation-critical]** Winding 1 nominal voltage in kV. "
            "Used with CW=3 for turns ratio calculation. Must correspond to a "
            "standard transmission voltage class.",
            "69\u2013500",
            "MUST be preserved exactly; verify drawn from standard kV classes"
        ),
        "ANG1": (
            "**[preservation-critical]** Winding 1 phase shift angle in degrees. "
            "Non-zero for phase-shifting transformers.",
            "-180\u2013180",
            "MUST be preserved exactly to at least 2 decimal places; "
            "non-zero ANG1 indicates phase-shifting transformer"
        ),
        "RATA1": (
            "**[preservation-critical]** Winding 1 normal rating in MVA.",
            "50\u20132000",
            "MUST be preserved exactly to at least 1 decimal place"
        ),
        "RATB1": ("Winding 1 emergency rating in MVA.", "50\u20133000",
                  "Verify RATB1 preserved to at least 1 decimal place"),
        "RATC1": ("Winding 1 long-term emergency rating in MVA.", "50\u20134000",
                  "Verify RATC1 preserved to at least 1 decimal place"),
        "COD1": ("Winding 1 tap control mode code.", "\u2014",
                 "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"),
        "CONT1": ("Winding 1 controlled bus number.", "\u2014",
                  "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"),
        "RMA1": ("Winding 1 upper tap or voltage limit.", "0.9\u20131.1",
                 "Verify RMA1 preserved to at least 4 decimal places"),
        "RMI1": ("Winding 1 lower tap or voltage limit.", "0.9\u20131.1",
                 "Verify RMI1 preserved to at least 4 decimal places"),
        "VMA1": ("Winding 1 upper voltage limit for control.", "1.0\u20131.1",
                 "Verify VMA1 preserved to at least 4 decimal places"),
        "VMI1": ("Winding 1 lower voltage limit for control.", "0.9\u20131.0",
                 "Verify VMI1 preserved to at least 4 decimal places"),
        "NTP1": ("Number of tap positions for winding 1.", "11\u201399",
                 "If field is at PSS/E default (33), tool may omit \u2014 do not penalize"),
        "TAB1": ("Impedance correction table number for winding 1.", "\u2014",
                 "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"),
        "CR1": ("Load drop compensation resistance for winding 1.", "\u2014",
                "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"),
        "CX1": ("Load drop compensation reactance for winding 1.", "\u2014",
                "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"),
        "CNXA1": ("Connection angle for winding 1.", "\u2014",
                  "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"),
        "WINDV2": (
            "**[preservation-critical]** Winding 2 off-nominal turns ratio or voltage.",
            "0.9\u20131.1 (pu) or kV",
            "MUST be preserved exactly to at least 5 decimal places"
        ),
        "NOMV2": (
            "**[preservation-critical]** Winding 2 nominal voltage in kV.",
            "69\u2013500",
            "MUST be preserved exactly; verify drawn from standard kV classes"
        ),
        "ANG2": ("Winding 2 phase shift angle in degrees.", "-180\u2013180",
                 "Verify ANG2 preserved to at least 2 decimal places"),
        "RATA2": (
            "**[preservation-critical]** Winding 2 normal rating in MVA.",
            "50\u20132000",
            "MUST be preserved exactly to at least 1 decimal place"
        ),
        "RATB2": ("Winding 2 emergency rating in MVA.", "\u2014",
                  "Verify RATB2 preserved to at least 1 decimal place"),
        "RATC2": ("Winding 2 long-term emergency rating.", "\u2014",
                  "Verify RATC2 preserved to at least 1 decimal place"),
        "COD2": ("Winding 2 tap control mode code.", "\u2014",
                 "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"),
        "CONT2": ("Winding 2 controlled bus number.", "\u2014",
                  "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"),
        "RMA2": ("Winding 2 upper tap or voltage limit.", "0.9\u20131.1",
                 "Verify RMA2 preserved to at least 4 decimal places"),
        "RMI2": ("Winding 2 lower tap or voltage limit.", "0.9\u20131.1",
                 "Verify RMI2 preserved to at least 4 decimal places"),
        "VMA2": ("Winding 2 upper voltage limit for control.", "1.0\u20131.1",
                 "Verify VMA2 preserved to at least 4 decimal places"),
        "VMI2": ("Winding 2 lower voltage limit for control.", "0.9\u20131.0",
                 "Verify VMI2 preserved to at least 4 decimal places"),
        "NTP2": ("Number of tap positions for winding 2.", "11\u201399",
                 "If field is at PSS/E default (33), tool may omit \u2014 do not penalize"),
        "TAB2": ("Impedance correction table for winding 2.", "\u2014",
                 "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"),
        "CR2": ("Load drop compensation resistance for winding 2.", "\u2014",
                "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"),
        "CX2": ("Load drop compensation reactance for winding 2.", "\u2014",
                "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"),
        "CNXA2": ("Connection angle for winding 2.", "\u2014",
                  "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"),
        "WINDV3": (
            "**[preservation-critical]** Winding 3 off-nominal turns ratio or voltage. "
            "Null/default for 2-winding transformers (K=0).",
            "0.9\u20131.1 (pu) or kV",
            "MUST be preserved exactly to at least 5 decimal places when K != 0; "
            "verify winding 3 fields are non-null when K != 0"
        ),
        "NOMV3": (
            "**[preservation-critical]** Winding 3 nominal voltage in kV. "
            "Null/default for 2W transformers.",
            "69\u2013500",
            "MUST be preserved exactly when K != 0; verify drawn from standard kV classes"
        ),
        "ANG3": ("Winding 3 phase shift angle in degrees.", "-180\u2013180",
                 "Verify ANG3 preserved to at least 2 decimal places when K != 0"),
        "RATA3": (
            "**[preservation-critical]** Winding 3 normal rating in MVA.",
            "50\u20132000",
            "MUST be preserved exactly to at least 1 decimal place when K != 0"
        ),
        "RATB3": ("Winding 3 emergency rating.", "\u2014",
                  "If K=0, tool may omit \u2014 do not penalize"),
        "RATC3": ("Winding 3 long-term emergency rating.", "\u2014",
                  "If K=0, tool may omit \u2014 do not penalize"),
        "COD3": ("Winding 3 tap control mode.", "\u2014",
                 "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"),
        "CONT3": ("Winding 3 controlled bus.", "\u2014",
                  "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"),
        "RMA3": ("Winding 3 upper tap/voltage limit.", "\u2014",
                 "Verify RMA3 preserved to at least 4 decimal places when K != 0"),
        "RMI3": ("Winding 3 lower tap/voltage limit.", "\u2014",
                 "Verify RMI3 preserved to at least 4 decimal places when K != 0"),
        "VMA3": ("Winding 3 upper voltage limit for control.", "\u2014",
                 "Verify VMA3 preserved to at least 4 decimal places when K != 0"),
        "VMI3": ("Winding 3 lower voltage limit for control.", "\u2014",
                 "Verify VMI3 preserved to at least 4 decimal places when K != 0"),
        "NTP3": ("Number of tap positions for winding 3.", "\u2014",
                 "If field is at PSS/E default (33), tool may omit \u2014 do not penalize"),
        "TAB3": ("Impedance correction table for winding 3.", "\u2014",
                 "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"),
        "CR3": ("Load drop compensation resistance for winding 3.", "\u2014",
                "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"),
        "CX3": ("Load drop compensation reactance for winding 3.", "\u2014",
                "If field is at PSS/E default (0.0), tool may omit \u2014 do not penalize"),
        "CNXA3": ("Connection angle for winding 3.", "\u2014",
                  "If field is at PSS/E default (0), tool may omit \u2014 do not penalize"),
    },
    "Area": {
        "I": ("Unique area number identifying this interchange control area.", "1\u201350",
              "Verify I is a positive integer preserved exactly"),
        "ISW": (
            "**[preservation-critical]** Area slack bus number. The swing bus "
            "that absorbs area interchange mismatch. 0=no area slack bus specified.",
            "0 or valid bus number",
            "MUST be preserved exactly; loss of area slack assignment corrupts "
            "area interchange control"
        ),
        "PDES": (
            "**[preservation-critical]** Desired net area interchange in MW. "
            "Positive=export, negative=import.",
            "-5000\u20135000",
            "MUST be preserved exactly to at least 2 decimal places"
        ),
        "PTOL": (
            "**[preservation-critical]** Area interchange tolerance in MW. "
            "Convergence criterion for area interchange control.",
            "1.0\u201350.0",
            "MUST be preserved exactly to at least 1 decimal place"
        ),
        "ARNAME": (
            "Area name, up to 12 characters.",
            "\u2014",
            "Verify ARNAME is preserved including trailing whitespace"
        ),
    },
}

# For record types not in _SEMANTIC, generate basic descriptions from FieldSpec
def _auto_semantic(rt: str, f: FieldSpec) -> tuple[str, str, str]:
    """Generate a reasonable semantic tuple from FieldSpec metadata."""
    prefix = "**[preservation-critical]** " if f.preservation_critical else ""
    desc = f"{prefix}{f.description}."
    exp_range = _range_str(f) if f.valid_range else "\u2014"
    if f.default_value is not None and not f.preservation_critical:
        guidance = (
            f"If field is at PSS/E default ({f.default_value}), "
            "tool may omit \u2014 do not penalize"
        )
    elif f.preservation_critical:
        guidance = "MUST be preserved exactly; loss of this field is a fidelity finding"
    elif f.data_type == "integer":
        guidance = f"Verify {f.name} is a valid integer and matches the source"
    elif f.data_type == "number":
        guidance = f"Verify {f.name} preserved to at least 4 decimal places"
    else:
        guidance = f"Verify {f.name} is preserved as a string including any trailing whitespace"
    return (desc, exp_range, guidance)
# fmt: on


def _get_semantic(rt: str, f: FieldSpec) -> tuple[str, str, str]:
    """Look up hand-authored semantic, fall back to auto-generated."""
    rt_dict = _SEMANTIC.get(rt, {})
    if f.name in rt_dict:
        desc, exp_range, guidance = rt_dict[f.name]
        # Ensure preservation-critical prefix
        if f.preservation_critical and "**[preservation-critical]**" not in desc:
            desc = "**[preservation-critical]** " + desc
        return (desc, exp_range, guidance)
    return _auto_semantic(rt, f)


# ---------------------------------------------------------------------------
# Worked examples (hand-authored, synthetic, NDA-safe)
# ---------------------------------------------------------------------------

_WORKED_EXAMPLES: dict[str, str] = {
    "Bus": """\
```
I:      30100
NAME:   "MESA 230    "
BASKV:  230.0
IDE:    1
AREA:   5
ZONE:   12
OWNER:  3
VM:     1.0142
VA:     -8.35
NVHI:   1.1
NVLO:   0.9
EVHI:   1.1
EVLO:   0.9
```""",
    "Load": """\
```
I:      30100
ID:     "1 "
STATUS: 1
AREA:   5
ZONE:   12
PL:     245.80
QL:     85.30
IP:     0.0
IQ:     0.0
YP:     0.0
YQ:     0.0
OWNER:  3
SCALE:  1
```""",
    "Fixed Shunt": """\
```
I:      42500
ID:     "1 "
STATUS: 1
GL:     0.0
BL:     150.0
```""",
    "Generator": """\
```
I:      50200
ID:     "1 "
PG:     350.00
QG:     45.20
QT:     200.0
QB:     -100.0
VS:     1.0250
IREG:   0
MBASE:  400.0
ZR:     0.0
ZX:     1.0
RT:     0.0
XT:     0.0
GTAP:   1.0
STAT:   1
RMPCT:  100.0
PT:     400.0
PB:     100.0
O1:     5
F1:     1.0
O2:     0
F2:     0.0
O3:     0
F3:     0.0
O4:     0
F4:     0.0
WMOD:   0
WPF:    1.0
```""",
    "Branch": """\
```
I:      30100
J:      30200
CKT:    "1 "
R:      0.00320
X:      0.03150
B:      0.52800
RATEA:  600.0
RATEB:  720.0
RATEC:  800.0
GI:     0.0
BI:     0.0
GJ:     0.0
BJ:     0.0
ST:     1
MET:    1
LEN:    0.0
O1:     3
F1:     1.0
O2:     0
F2:     0.0
O3:     0
F3:     0.0
O4:     0
F4:     0.0
```""",
    "Transformer": """\
```
I:      30100
J:      30500
K:      0
CKT:    "1 "
CW:     1
CZ:     1
CM:     1
MAG1:   0.0
MAG2:   0.0
NMETR:  2
NAME:   "XF-230/69   "
STAT:   1
O1:     3
F1:     1.0
O2:     0
F2:     0.0
O3:     0
F3:     0.0
O4:     0
F4:     0.0
VECGRP: "            "
R1_2:   0.00250
X1_2:   0.12500
SBASE1_2: 200.0
R2_3:   0.0
X2_3:   0.0
SBASE2_3: 100.0
R3_1:   0.0
X3_1:   0.0
SBASE3_1: 100.0
VMSTAR: 1.0
ANSTAR: 0.0
WINDV1: 1.0125
NOMV1:  230.0
ANG1:   0.0
RATA1:  200.0
RATB1:  240.0
RATC1:  280.0
COD1:   0
CONT1:  0
RMA1:   1.1
RMI1:   0.9
VMA1:   1.1
VMI1:   0.9
NTP1:   33
TAB1:   0
CR1:    0.0
CX1:    0.0
CNXA1:  0
WINDV2: 1.0
NOMV2:  69.0
ANG2:   0.0
RATA2:  200.0
RATB2:  0.0
RATC2:  0.0
COD2:   0
CONT2:  0
RMA2:   1.1
RMI2:   0.9
VMA2:   1.1
VMI2:   0.9
NTP2:   33
TAB2:   0
CR2:    0.0
CX2:    0.0
CNXA2:  0
WINDV3: 1.0
NOMV3:  0.0
ANG3:   0.0
RATA3:  0.0
RATB3:  0.0
RATC3:  0.0
COD3:   0
CONT3:  0
RMA3:   1.1
RMI3:   0.9
VMA3:   1.1
VMI3:   0.9
NTP3:   33
TAB3:   0
CR3:    0.0
CX3:    0.0
CNXA3:  0
```""",
    "Area": """\
```
I:      5
ISW:    50200
PDES:   150.0
PTOL:   10.0
ARNAME: "SOUTH ZONE  "
```""",
    "Two-Terminal DC": """\
```
NAME:    "PDCI_NORTH  "
MDC:     1
RDC:     12.5
SETVL:   1600.0
VSCHD:   500.0
VCMOD:   0.0
RCOMP:   0.0
DELTI:   0.0
METER:   "I"
DCVMIN:  0.0
CCCITMX: 20
CCCACC:  1.0
IPR:     60100
NBR:     2
ANMXR:   0.0
ANMNR:   0.0
RCR:     0.0
XCR:     0.0
EBASR:   0.0
TRR:     1.0
TAPR:    1.0
TMXR:    1.5
TMNR:    0.51
STPR:    0.00625
ICR:     0
IFR:     0
ITR:     0
IDR:     "1 "
XCAPR:   0.0
IPI:     60200
NBI:     2
ANMXI:   0.0
ANMNI:   0.0
RCI:     0.0
XCI:     0.0
EBASI:   0.0
TRI:     1.0
TAPI:    1.0
TMXI:    1.5
TMNI:    0.51
STPI:    0.00625
ICI:     0
IFI:     0
ITI:     0
IDI:     "1 "
XCAPI:   0.0
```""",
    "VSC DC": """\
```
NAME:   "VSC_LINK_1  "
MDC:    1
RDC:    5.0
O1:     1
F1:     1.0
O2:     0
F2:     0.0
O3:     0
F3:     0.0
O4:     0
F4:     0.0
IBUS1:  70100
TYPE1:  1
MODE1:  1
DCSET1: 400.0
ACSET1: 1.0
ALOSS1: 0.0
BLOSS1: 0.0
MINLOSS1: 0.0
SMAX1:  500.0
IMAX1:  0.0
PWF1:   1.0
MAXQ1:  200.0
MINQ1:  -200.0
REMOT1: 0
RMPCT1: 100.0
IBUS2:  70200
TYPE2:  1
MODE2:  1
DCSET2: 0.0
ACSET2: 1.0
ALOSS2: 0.0
BLOSS2: 0.0
MINLOSS2: 0.0
SMAX2:  500.0
IMAX2:  0.0
PWF2:   1.0
MAXQ2:  200.0
MINQ2:  -200.0
REMOT2: 0
RMPCT2: 100.0
```""",
    "Impedance Correction": """\
```
T:   1
T1:  0.9
F1:  0.95
T2:  0.95
F2:  0.98
T3:  1.0
F3:  1.0
T4:  1.05
F4:  0.98
T5:  1.1
F5:  0.95
T6:  0.0
F6:  0.0
T7:  0.0
F7:  0.0
T8:  0.0
F8:  0.0
T9:  0.0
F9:  0.0
T10: 0.0
F10: 0.0
T11: 0.0
F11: 0.0
```""",
    "Multi-Terminal DC": """\
```
NAME:   "MTDC_SYS_1  "
NCONV:  3
NDCBS:  4
NDCLN:  3
MDC:    1
VCONV:  1
VCMOD:  0.0
VCONVN: 0
```""",
    "Multi-Section Line": """\
```
I:    30100
J:    30400
ID:   "1 "
MET:  1
DUM1: 30150
DUM2: 30200
DUM3: 30250
DUM4: 0
DUM5: 0
DUM6: 0
DUM7: 0
DUM8: 0
DUM9: 0
```""",
    "Zone": """\
```
I:      12
ZONAME: "SOUTH BAY   "
```""",
    "Interarea Transfer": """\
```
ARFROM: 5
ARTO:   8
TRID:   "1 "
PTRAN:  200.0
```""",
    "Owner": """\
```
I:      3
OWNAME: "SOCAL EDISON"
```""",
    "FACTS": """\
```
NAME:    "SVC_MESA    "
I:       30100
J:       0
MODE:    1
SET1:    1.0
SET2:    0.0
VSREF:   1.0
REMOT:   0
MESSION: 0.0
LINX:    0.05
RMPCT:   100.0
OWNER:   3
SET3:    0.0
SET4:    0.0
```""",
    "Switched Shunt": """\
```
I:      42500
MODSW:  1
ADJM:   0
STAT:   1
VSWHI:  1.05
VSWLO:  0.95
SWREM:  0
RMPCT:  100.0
RMIDNT: ""
BINIT:  50.0
N1:     2
B1:     25.0
N2:     3
B2:     50.0
N3:     0
B3:     0.0
N4:     0
B4:     0.0
N5:     0
B5:     0.0
N6:     0
B6:     0.0
N7:     0
B7:     0.0
N8:     0
B8:     0.0
```""",
}

# ---------------------------------------------------------------------------
# Nullable/default behavior (hand-authored per record type)
# ---------------------------------------------------------------------------

_NULLABLE_BEHAVIOR: dict[str, str] = {
    "Bus": (
        "All bus fields are required in PSS/E v31 and have well-defined defaults. "
        "BASKV=0.0 is the PSS/E default but indicates an uninitialized bus; real network "
        "buses always have BASKV > 0. VM defaults to 1.0 (flat start), and VA defaults "
        "to 0.0 degrees. The voltage limit fields (NVHI, NVLO, EVHI, EVLO) default to "
        "standard PSS/E values and may be omitted by tools without penalty. "
        "The canonical parser writes all fields including those at default values."
    ),
    "Load": (
        "The constant-current (IP, IQ) and constant-admittance (YP, YQ) load components "
        "default to 0.0, meaning the load is modeled as constant-power only. A zero value "
        "is semantically meaningful (not missing) -- it means that load component is absent. "
        "OWNER defaults to 1, and SCALE defaults to 1 (load participates in scaling)."
    ),
    "Fixed Shunt": (
        "GL defaults to 0.0, meaning no active power loss in the shunt (purely reactive). "
        "BL defaults to 0.0 but is typically non-zero for any meaningful shunt device. "
        "STATUS defaults to 1 (in-service)."
    ),
    "Generator": (
        "QT=9999.0 and QB=-9999.0 indicate unconstrained reactive capability (PSS/E defaults). "
        "IREG=0 means local voltage regulation (at bus I), not 'no regulation'. This distinction "
        "is critical: zero is a meaningful value, not a null. ZR, ZX, RT, XT, GTAP are machine "
        "impedance parameters that default to their PSS/E values; tools commonly omit these for "
        "steady-state power flow. Owner fields O2-O4 default to 0, meaning single ownership."
    ),
    "Branch": (
        "R and X have no default -- they must be provided for every branch. B defaults to 0.0 "
        "(no line charging), which is valid for short lines. Rating fields (RATEA, RATEB, RATEC) "
        "default to 0.0, meaning no thermal limit is enforced. GI, BI, GJ, BJ are line shunt "
        "elements that default to 0.0 (no shunt admittance at line ends). Owner fields O2-O4 "
        "default to 0."
    ),
    "Transformer": (
        "K=0 indicates a 2-winding transformer; all winding-3 fields revert to defaults. "
        "The CW, CZ, CM codes default to 1 but are preservation-critical because they control "
        "how all impedance and turns-ratio fields are interpreted. WINDV1/WINDV2 default to 1.0 "
        "(unity turns ratio). NOMV1/NOMV2 default to 0.0, meaning the bus base kV is used. "
        "VMSTAR and ANSTAR are meaningful only for 3W transformers."
    ),
    "Area": (
        "ISW=0 means no area slack bus is designated. PDES=0.0 means no net interchange "
        "target. PTOL=10.0 is the default interchange tolerance. All fields are required."
    ),
    "Two-Terminal DC": (
        "Many fields have PSS/E defaults that represent 'not specified' or 'not applicable'. "
        "RDC has no default and must always be present. SETVL and VSCHD are operationally "
        "significant and should be preserved. Converter tap limits (TMXR, TMNR, etc.) have "
        "standard defaults."
    ),
    "VSC DC": (
        "Owner fields O2-O4 default to 0 (single ownership). Converter loss coefficients "
        "(ALOSS, BLOSS, MINLOSS) default to 0.0. SMAX and IMAX default to 0.0 meaning "
        "no limit. Q limits default to +/-9999.0."
    ),
    "Impedance Correction": (
        "T1-T11 and F1-F11 pairs define piecewise-linear correction curves. Unused pairs "
        "default to 0.0. The table is terminated by the first T value of 0.0."
    ),
    "Multi-Terminal DC": (
        "NCONV, NDCBS, NDCLN define the structure of the multi-terminal DC system. "
        "These must be non-zero for a valid record. MDC defaults to 0. "
        "VCONV, VCMOD, VCONVN are control parameters with standard defaults."
    ),
    "Multi-Section Line": (
        "DUM1-DUM9 are intermediate bus numbers defining the multi-section line topology. "
        "DUM values of 0 indicate unused slots. At least DUM1 must be non-zero for a "
        "valid multi-section line grouping."
    ),
    "Zone": (
        "Both I and ZONAME are required. ZONAME defaults to blank (12 spaces). "
        "No fields are nullable."
    ),
    "Interarea Transfer": (
        "All fields are required. PTRAN defaults to 0.0 (no scheduled transfer). "
        "TRID defaults to '1 '."
    ),
    "Owner": (
        "Both I and OWNAME are required. OWNAME defaults to blank (12 spaces). "
        "No fields are nullable."
    ),
    "FACTS": (
        "J=0 indicates a shunt FACTS device (no terminal bus). MODE defaults to 1. "
        "SET1-SET4 are control setpoints with mode-dependent interpretations; they default "
        "to 0.0. VSREF defaults to 1.0 pu. LINX defaults to 0.05 pu."
    ),
    "Switched Shunt": (
        "N1-N8 and B1-B8 define discrete switching blocks. Unused blocks have N=0 and B=0.0. "
        "BINIT is the initial susceptance and should match the sum of switched-in blocks. "
        "MODSW defaults to 1 (discrete mode). SWREM=0 means local voltage control. "
        "RMIDNT is an optional name field that may be empty."
    ),
}

# ---------------------------------------------------------------------------
# Approximate record counts (NDA-safe order-of-magnitude)
# ---------------------------------------------------------------------------

_APPROX_COUNTS: dict[str, str] = {
    "Bus": "~30,000",
    "Load": "~15,000",
    "Fixed Shunt": "~500",
    "Generator": "~5,000",
    "Branch": "~35,000",
    "Transformer": "~8,000",
    "Area": "~30",
    "Two-Terminal DC": "~5",
    "VSC DC": "~2",
    "Impedance Correction": "~200",
    "Multi-Terminal DC": "~1",
    "Multi-Section Line": "~800",
    "Zone": "~40",
    "Interarea Transfer": "~50",
    "Owner": "~100",
    "FACTS": "~50",
    "Switched Shunt": "~3,000",
}

# ---------------------------------------------------------------------------
# Purpose statements (richer than _TABLE_DESCRIPTIONS)
# ---------------------------------------------------------------------------

_PURPOSES: dict[str, str] = {
    "Bus": (
        "Defines every node (bus) in the transmission network. Each bus has a unique number, "
        "base voltage, type code (PQ/PV/swing/isolated), and solved-state voltage. All other "
        "record types reference buses by number. The bus table is the topological foundation "
        "of the network model."
    ),
    "Load": (
        "Represents electrical demand at each bus. Loads are modeled with constant-power (PL, QL), "
        "constant-current (IP, IQ), and constant-admittance (YP, YQ) components. Multiple loads "
        "can exist at one bus, distinguished by their two-character ID."
    ),
    "Fixed Shunt": (
        "Represents fixed (non-switchable) shunt compensation devices. Fixed shunts provide "
        "reactive power support (capacitive) or absorption (inductive) at a constant value "
        "regardless of voltage. Distinguished from switched shunts which have discrete steps."
    ),
    "Generator": (
        "Represents all generating units including conventional thermal, hydro, wind, and solar "
        "plants. Each generator has active/reactive output, capability limits, voltage setpoint, "
        "and machine impedance data. Multiple generators at one bus use different IDs."
    ),
    "Branch": (
        "Represents transmission lines, cables, and series elements connecting two buses. "
        "Each branch has impedance (R, X, B), thermal ratings, and status. Parallel branches "
        "between the same bus pair are distinguished by circuit identifier CKT."
    ),
    "Transformer": (
        "Represents 2-winding and 3-winding power transformers. The PSS/E RAW format uses "
        "a multi-line record (up to 5 lines) that is flattened into a single row in the "
        "intermediate format. The CW/CZ/CM codes control how impedance and turns-ratio "
        "data are interpreted -- these must be preserved exactly."
    ),
    "Area": (
        "Defines interchange control areas for the power flow solution. Each area has a "
        "slack bus, desired net interchange (export/import), and tolerance. Areas are the "
        "primary aggregation unit for balancing supply and demand."
    ),
    "Two-Terminal DC": (
        "Represents conventional line-commutated converter (LCC) HVDC links with a rectifier "
        "and inverter terminal. Each record contains DC line parameters plus full converter "
        "transformer and control data for both ends."
    ),
    "VSC DC": (
        "Represents voltage-source converter (VSC) HVDC links. More modern than LCC technology, "
        "with independent P and Q control at each converter. Each record contains DC line "
        "parameters and two converter specifications."
    ),
    "Impedance Correction": (
        "Defines piecewise-linear impedance correction tables referenced by transformers "
        "(via TAB1/TAB2/TAB3). Each table maps tap ratio or phase angle to a correction "
        "factor applied to the transformer impedance."
    ),
    "Multi-Terminal DC": (
        "Header record for multi-terminal HVDC systems with more than two converters. "
        "Defines the number of converters, DC buses, and DC links in the system. "
        "Detailed converter/bus/link data follows in the PSS/E RAW file."
    ),
    "Multi-Section Line": (
        "Groups multiple branch records into a single multi-section transmission line. "
        "DUM1-DUM9 define intermediate bus numbers along the line. All sections share "
        "the same from-bus (I), to-bus (J), and line identifier (ID)."
    ),
    "Zone": (
        "Defines geographic or administrative zones for reporting and load allocation. "
        "Zones provide finer-grained grouping than areas. Each bus is assigned to exactly one zone."
    ),
    "Interarea Transfer": (
        "Defines scheduled power transfers between interchange areas. Each transfer specifies "
        "a from-area, to-area, transfer ID, and scheduled MW amount."
    ),
    "Owner": (
        "Defines ownership entities referenced by buses, branches, generators, and transformers. "
        "Used for cost allocation and ownership tracking across the network."
    ),
    "FACTS": (
        "Represents Flexible AC Transmission System devices including SVCs, STATCOMs, TCSCs, "
        "and UPFCs. Each device has control mode, setpoints, and impedance parameters."
    ),
    "Switched Shunt": (
        "Represents switchable shunt compensation with discrete step blocks. Each device has "
        "up to 8 blocks (N1-N8, B1-B8) defining the number of steps and MVAR per step. "
        "Control mode determines whether switching is discrete or continuous."
    ),
}


# ---------------------------------------------------------------------------
# Cross-reference sections
# ---------------------------------------------------------------------------

_PU = "per-unit-conventions.md"
_FCM = "field-criticality-matrix.md"
_MG = "mapping-guide.md"
_3W = "three-winding-transformers.md"

_CROSS_REFS: dict[str, list[str]] = {
    "Bus": [
        f"See [Per-Unit Convention Reference]({_PU}#bus-voltage) for VM/VA per-unit basis.",
        f"See [Field Criticality Matrix]({_FCM}) for DCPF/ACPF criticality tiers.",
        f"See [Record-Type Mapping Guide]({_MG}#bus) for tool-specific bus representations.",
    ],
    "Load": [
        f"See [Per-Unit Convention Reference]({_PU}) for load component scaling.",
        f"See [Record-Type Mapping Guide]({_MG}#load) for tool-specific load representations.",
    ],
    "Fixed Shunt": [
        f"See [Per-Unit Convention Reference]({_PU}#shunt-admittance) for BL sign convention.",
        f"See [Record-Type Mapping Guide]({_MG}#fixed-shunt)"
        " for tool-specific shunt representations.",
    ],
    "Generator": [
        f"See [Per-Unit Convention Reference]({_PU}#generator-impedance) for MBASE-based per-unit.",
        f"See [Record-Type Mapping Guide]({_MG}#generator)"
        " for tool-specific generator representations.",
    ],
    "Branch": [
        f"See [Per-Unit Convention Reference]({_PU}#branch-impedance) for conversion formulas.",
        f"See [Field Criticality Matrix]({_FCM}) for DCPF-critical branch fields.",
        f"See [Record-Type Mapping Guide]({_MG}#branch) for tool-specific branch representations.",
    ],
    "Transformer": [
        f"See [Per-Unit Convention Reference]({_PU}#transformer-impedance)"
        " for CW/CZ/CM conversions.",
        f"See [3-Winding Transformer Reference]({_3W}) for topology details.",
        f"See [Field Criticality Matrix]({_FCM}) for preservation-critical transformer fields.",
        f"See [Record-Type Mapping Guide]({_MG}#transformer) for tool-specific representations.",
    ],
    "Area": [
        f"See [Record-Type Mapping Guide]({_MG}#area) for tool-specific area representations.",
    ],
    "Two-Terminal DC": [
        f"See [Record-Type Mapping Guide]({_MG}#two-terminal-dc)"
        " for tool-specific HVDC representations.",
    ],
    "VSC DC": [
        f"See [Record-Type Mapping Guide]({_MG}#vsc-dc) for tool-specific VSC representations.",
    ],
    "Impedance Correction": [
        f"See [Record-Type Mapping Guide]({_MG}#impedance-correction)"
        " for tool-specific representations.",
    ],
    "Multi-Terminal DC": [
        f"See [Record-Type Mapping Guide]({_MG}#multi-terminal-dc)"
        " for tool-specific representations.",
    ],
    "Multi-Section Line": [
        f"See [Record-Type Mapping Guide]({_MG}#multi-section-line)"
        " for tool-specific representations.",
    ],
    "Zone": [
        f"See [Record-Type Mapping Guide]({_MG}#zone) for tool-specific zone representations.",
    ],
    "Interarea Transfer": [
        f"See [Record-Type Mapping Guide]({_MG}#interarea-transfer)"
        " for tool-specific representations.",
    ],
    "Owner": [
        f"See [Record-Type Mapping Guide]({_MG}#owner) for tool-specific owner representations.",
    ],
    "FACTS": [
        f"See [Record-Type Mapping Guide]({_MG}#facts) for tool-specific FACTS representations.",
    ],
    "Switched Shunt": [
        f"See [Per-Unit Convention Reference]({_PU}#shunt-admittance) for BL sign convention.",
        f"See [Record-Type Mapping Guide]({_MG}#switched-shunt) for tool-specific representations.",
    ],
}


def generate_document(schemas: list[TableSchema]) -> str:
    """Generate the full intermediate-schema.md document."""
    lines: list[str] = []

    # --- Front matter ---
    lines.append("# Intermediate Format Schema Reference")
    lines.append("")
    lines.append("**Version:** 1.0")
    lines.append("**Phase 1 Schema:** `../intermediate/schemas/` (JSON Schema Draft 2020-12)")
    lines.append("**Audience:** evaluate-tool agents, human reviewers")
    lines.append("**Normative definitions:** Phase 1 D7 JSON Schema files define data types,")
    lines.append("  required/optional status, and valid ranges. This document adds semantic")
    lines.append("  descriptions, worked examples, and ingestion verification guidance.")
    lines.append("")

    # --- Table Summary ---
    lines.append("## Table Summary")
    lines.append("")
    lines.append("| Table | PSS/E Record Type | Records | Columns | Primary Key | Purpose |")
    lines.append("| ----- | ----------------- | ------- | ------- | ----------- | ------- |")
    for ts in schemas:
        pk = ", ".join(ts.primary_key)
        count = _APPROX_COUNTS.get(ts.record_type, "~?")
        purpose = ts.description.split(".")[0]
        lines.append(
            f"| `{ts.table_name}` | {ts.record_type} | {count} | "
            f"{len(ts.fields)} | `[{pk}]` | {purpose} |"
        )
    lines.append("")

    # --- Per-table sections ---
    for ts in schemas:
        rt = ts.record_type

        # Header block
        lines.append(f"## {rt}")
        lines.append("")
        lines.append(f"**Table name:** `{ts.table_name}`")
        lines.append(
            f"**Schema file:** [`../intermediate/schemas/{ts.table_name}.schema.json`]"
            f"(../intermediate/schemas/{ts.table_name}.schema.json)"
        )
        pk_str = ", ".join(ts.primary_key)
        lines.append(f"**Primary key:** `[{pk_str}]`")
        lines.append(f"**Purpose:** {_PURPOSES.get(rt, ts.description)}")
        lines.append("")

        # Field description table
        lines.append("### Fields")
        lines.append("")
        lines.append(
            "| Field | Type | Unit | Semantic Description | Expected Range "
            "| Nullable | Default | Evaluate-Tool Guidance |"
        )
        lines.append(
            "| ----- | ---- | ---- | -------------------- | -------------- "
            "| -------- | ------- | ---------------------- |"
        )
        for f in ts.fields:
            sem_desc, exp_range, guidance = _get_semantic(rt, f)
            nullable = "yes" if not f.required else "no"
            # Escape pipes in content
            sem_desc_esc = sem_desc.replace("|", "\\|")
            guidance_esc = guidance.replace("|", "\\|")
            exp_range_esc = exp_range.replace("|", "\\|")
            lines.append(
                f"| `{f.name}` | {f.data_type} | {_unit(f)} | "
                f"{sem_desc_esc} | {exp_range_esc} | {nullable} | "
                f"{_default_str(f)} | {guidance_esc} |"
            )
        lines.append("")

        # Worked example
        lines.append("### Worked Example")
        lines.append("")
        example = _WORKED_EXAMPLES.get(rt, "")
        if example:
            lines.append(example)
        else:
            lines.append("```")
            lines.append("(No example available)")
            lines.append("```")
        lines.append("")

        # Nullable/default behavior
        lines.append("### Nullable and Default Behavior")
        lines.append("")
        lines.append(_NULLABLE_BEHAVIOR.get(rt, "See field table above for default values."))
        lines.append("")

        # Cross-references
        lines.append("### Cross-References")
        lines.append("")
        refs = _CROSS_REFS.get(rt, [])
        if refs:
            for ref in refs:
                lines.append(f"- {ref}")
        else:
            lines.append(
                "- See [Field Criticality Matrix](field-criticality-matrix.md) "
                "for criticality tiers."
            )
        lines.append("")

    # --- Appendix: Preservation-Critical Fields ---
    lines.append("## Appendix: Preservation-Critical Fields")
    lines.append("")
    lines.append(
        "Fields with `x-psse-preservation-critical: true` in the Phase 1 JSON Schema. "
        "These fields carry elevated fidelity requirements and generate mandatory test cases."
    )
    lines.append("")
    lines.append("| Record Type | Field | Why Preservation-Critical |")
    lines.append("| ----------- | ----- | ------------------------- |")
    for ts in schemas:
        for f in ts.fields:
            if f.preservation_critical:
                sem, _, _ = _get_semantic(ts.record_type, f)
                # Strip the prefix for the appendix
                why = sem.replace("**[preservation-critical]** ", "").split(".")[0]
                lines.append(f"| {ts.record_type} | `{f.name}` | {why} |")
    lines.append("")

    # --- Appendix: Present-but-Inactive Fields ---
    lines.append("## Appendix: Present-but-Inactive Fields")
    lines.append("")
    lines.append(
        "Fields with `x-psse-present-but-inactive: true` in the Phase 1 JSON Schema. "
        "These fields are uniformly at their default values across the entire dataset. "
        "Evaluate-tool should not penalize a tool for omitting or zeroing these fields."
    )
    lines.append("")
    lines.append("| Record Type | Field | Default Value | Note |")
    lines.append("| ----------- | ----- | ------------- | ---- |")
    for ts in schemas:
        for f in ts.fields:
            if f.present_but_inactive:
                note = "Field present in schema but uniformly at default in FNM data"
                lines.append(f"| {ts.record_type} | `{f.name}` | {_default_str(f)} | {note} |")
    lines.append("")

    # --- Appendix: Schema Cross-Reference Index ---
    lines.append("## Appendix: Schema Cross-Reference Index")
    lines.append("")
    lines.append(
        "Lookup table mapping each JSON Schema file to its corresponding section in this document."
    )
    lines.append("")
    lines.append("| Schema File | Document Section |")
    lines.append("| ----------- | ---------------- |")
    for ts in schemas:
        lines.append(
            f"| `../intermediate/schemas/{ts.table_name}.schema.json` "
            f"| [## {ts.record_type}](#{ts.record_type.lower().replace(' ', '-')}) |"
        )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    """Generate and write the intermediate schema reference document."""
    schemas = get_table_schemas()
    doc = generate_document(schemas)

    output_path = Path(__file__).resolve().parent.parent / "docs" / "intermediate-schema.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(doc, encoding="utf-8")
    print(f"Wrote {output_path} ({len(doc)} bytes, {doc.count(chr(10))} lines)")


if __name__ == "__main__":
    main()
