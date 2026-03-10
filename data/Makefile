# Data Augmentation Pipeline — Makefile
#
# Orchestrates the data augmentation scripts in dependency order.
# All targets run inside the devcontainer via `uv run`.
#
# Usage:
#   make tiny          — Run the full TINY (case39) pipeline
#   make reference     — Build the RTS-GMLC reference table only
#   make clean         — Remove all generated output
#   make clean-tiny    — Remove only TINY outputs
#
# The TINY pipeline is self-contained and needs no external data downloads.
# The SMALL/MEDIUM pipelines require ACTIVSg companion data and Octave/MATPOWER.

SHELL := /bin/bash
.ONESHELL:

UV := uv run
PYTHON := $(UV) python -m

DATA_DIR := $(shell pwd)
NETWORKS := $(DATA_DIR)/networks
REFERENCE := $(DATA_DIR)/reference
TIMESERIES := $(DATA_DIR)/timeseries
CLASSIFICATION := $(DATA_DIR)/classification

# ---------------------------------------------------------------------------
# Phase 0: Foundation
# ---------------------------------------------------------------------------

REFERENCE_CSV := $(REFERENCE)/rts_gmlc_tech_classes.csv

$(REFERENCE_CSV):
	$(PYTHON) scripts.build_rts_gmlc_reference

.PHONY: reference
reference: $(REFERENCE_CSV)

# ---------------------------------------------------------------------------
# TINY (case39) Pipeline
# ---------------------------------------------------------------------------

TINY_DIR := $(TIMESERIES)/case39

# Step 1: Cleanup + classify
TINY_CLEANED := $(TINY_DIR)/case39.m
TINY_CLASSIFICATION := $(TINY_DIR)/gen_classification.csv

$(TINY_CLEANED) $(TINY_CLASSIFICATION):
	$(PYTHON) scripts.tiny_cleanup_classify

# Step 2: Temporal parameters (depends on reference + classification)
TINY_TEMPORAL := $(TINY_DIR)/gen_temporal_params.csv

$(TINY_TEMPORAL): $(REFERENCE_CSV) $(TINY_CLASSIFICATION)
	$(PYTHON) scripts.tiny_gen_temporal_params

# Step 3: Renewable profiles (depends on raw case39.m only)
TINY_WIND := $(TINY_DIR)/wind_actual_24h.csv
TINY_SOLAR := $(TINY_DIR)/solar_actual_24h.csv

$(TINY_WIND) $(TINY_SOLAR):
	$(PYTHON) scripts.renewable_profiles

# Step 4: Load profile (depends on cleaned case)
TINY_LOAD := $(TINY_DIR)/load_24h.csv

$(TINY_LOAD): $(TINY_CLEANED)
	$(PYTHON) scripts.tiny_load_profile

# Step 5: Reserve definitions (depends on reference + classification + temporal)
TINY_RESERVES_REQ := $(TINY_DIR)/reserve_requirements_24h.csv
TINY_RESERVES_ELIG := $(TINY_DIR)/reserve_eligibility.csv

$(TINY_RESERVES_REQ) $(TINY_RESERVES_ELIG): $(REFERENCE_CSV) $(TINY_CLASSIFICATION) $(TINY_TEMPORAL)
	$(PYTHON) scripts.tiny_reserve_definitions

# Step 6: Stochastic scenarios (depends on actual profiles)
TINY_SCENARIOS := $(TINY_DIR)/scenarios/scenario_multipliers_50x24.csv

$(TINY_SCENARIOS): $(TINY_WIND) $(TINY_SOLAR)
	$(PYTHON) scripts.tiny_stochastic_scenarios

# Step 7: Flowgates (depends on cleaned case + load profile)
TINY_FLOWGATES := $(TINY_DIR)/flowgates.csv

$(TINY_FLOWGATES): $(TINY_CLEANED) $(TINY_LOAD)
	$(PYTHON) scripts.tiny_flowgates

# Step 8: BESS + DR (depends on raw case39.m only)
TINY_BESS := $(TINY_DIR)/bess_units.csv
TINY_DR := $(TINY_DIR)/dr_buses.csv

$(TINY_BESS) $(TINY_DR):
	$(PYTHON) scripts.tiny_bess_dr

.PHONY: tiny
tiny: \
	$(TINY_CLEANED) \
	$(TINY_TEMPORAL) \
	$(TINY_WIND) $(TINY_SOLAR) \
	$(TINY_LOAD) \
	$(TINY_RESERVES_REQ) $(TINY_RESERVES_ELIG) \
	$(TINY_SCENARIOS) \
	$(TINY_FLOWGATES) \
	$(TINY_BESS) $(TINY_DR)
	@echo "=== TINY (case39) pipeline complete ==="
	@echo "Output: $(TINY_DIR)/"

# ---------------------------------------------------------------------------
# SMALL/MEDIUM Pipeline (requires ACTIVSg data + Octave)
# ---------------------------------------------------------------------------

# Step 1: Snapshot cleanup for all networks
CLEANUP_MANIFEST := $(TIMESERIES)/cleanup_manifest.json

$(CLEANUP_MANIFEST):
	$(PYTHON) scripts.snapshot_cleanup

# Step 2: Fuel classification for all networks
SMALL_CLASSIF := $(CLASSIFICATION)/ACTIVSg2000_classification.csv
MEDIUM_CLASSIF := $(CLASSIFICATION)/ACTIVSg10k_classification.csv

$(SMALL_CLASSIF) $(MEDIUM_CLASSIF): $(REFERENCE_CSV)
	$(PYTHON) scripts.classify_gen_fuel

# Step 3: Temporal parameters for all networks
$(TIMESERIES)/ACTIVSg2000/gen_temporal_params.csv: $(SMALL_CLASSIF) $(REFERENCE_CSV)
	$(PYTHON) scripts.assign_temporal_params

$(TIMESERIES)/ACTIVSg10k/gen_temporal_params.csv: $(MEDIUM_CLASSIF) $(REFERENCE_CSV)
	$(PYTHON) scripts.assign_temporal_params

# Step 4: DC OPF congestion analysis (requires Octave + MATPOWER)
DCOPF_DONE := $(TIMESERIES)/ACTIVSg2000/flowgate_calibration/calibration_log.json

$(DCOPF_DONE): $(CLEANUP_MANIFEST)
	$(PYTHON) scripts.dcopf_congestion

# Step 5: Flowgate definitions
FLOWGATE_SMALL := $(TIMESERIES)/ACTIVSg2000/flowgates.csv

$(FLOWGATE_SMALL): $(DCOPF_DONE)
	$(PYTHON) scripts.flowgate_definition

# Step 6: BESS placement
BESS_SMALL := $(TIMESERIES)/ACTIVSg2000/bess_units.csv

$(BESS_SMALL): $(CLEANUP_MANIFEST)
	$(PYTHON) scripts.phase3_bess_placement

# Step 7: DR placement
DR_SMALL := $(TIMESERIES)/ACTIVSg2000/dr_buses.csv

$(DR_SMALL): $(CLEANUP_MANIFEST)
	$(PYTHON) scripts.phase3_dr_placement

.PHONY: large
large: \
	$(CLEANUP_MANIFEST) \
	$(SMALL_CLASSIF) $(MEDIUM_CLASSIF) \
	$(TIMESERIES)/ACTIVSg2000/gen_temporal_params.csv \
	$(FLOWGATE_SMALL) \
	$(BESS_SMALL) $(DR_SMALL)
	@echo "=== SMALL/MEDIUM pipeline complete ==="

# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

.PHONY: all
all: tiny large
	@echo "=== Full pipeline complete ==="

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

.PHONY: validate
validate: tiny large
	$(PYTHON) scripts.phase3_validation

# ---------------------------------------------------------------------------
# Clean targets
# ---------------------------------------------------------------------------

.PHONY: clean-tiny
clean-tiny:
	rm -rf $(TINY_DIR)

.PHONY: clean-large
clean-large:
	rm -rf $(TIMESERIES)/ACTIVSg2000 $(TIMESERIES)/ACTIVSg10k
	rm -rf $(CLASSIFICATION)
	rm -f $(TIMESERIES)/cleanup_manifest.json $(TIMESERIES)/reconciliation_report.json

.PHONY: clean
clean: clean-tiny clean-large
	rm -rf $(REFERENCE)
	@echo "All generated data removed."
