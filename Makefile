# ==============================================================================
# AlphaGSM Makefile
# ==============================================================================
# Targets:
#   make install       — install everything: Python + deps + system libs + Wine/Proton
#   make python        — install the Python version pinned in .python-version
#   make deps          — install Python packages from requirements.txt
#   make system-libs   — install Linux system packages required by AlphaGSM
#   make wine          — install Wine and configure the Wine prefix
#   make proton        — install Proton-GE (standalone; no Steam required)
#   make wine-proton   — install Wine + Proton-GE + configure Wine prefix
#   make config        — copy alphagsm.conf-template → alphagsm.conf (once)
#   make lint          — run the pylint quality gate (must score 10.00/10)
#   make test          — run the unit test suite
#   make help          — show this message
# ==============================================================================

.PHONY: all install python deps system-libs wine proton wine-proton config lint test integration-test smoke-test help

# Read the pinned Python version from .python-version (e.g. 3.10.13)
PYTHON_VERSION_FULL := $(shell cat .python-version 2>/dev/null | tr -d '[:space:]')
PYTHON_MAJOR_MINOR  := $(shell echo "$(PYTHON_VERSION_FULL)" | cut -d. -f1,2)

# python3.10 by default; override with: make deps PYTHON_BIN=python3.11
PYTHON_BIN ?= python$(PYTHON_MAJOR_MINOR)

# Default target — show help rather than silently running a big install.
all: help

# ------------------------------------------------------------------------------
# help
# ------------------------------------------------------------------------------
help:
	@echo ""
	@echo "AlphaGSM – installation and development targets"
	@echo ""
	@echo "  make install       Install everything (Python + deps + system libs + Wine + Proton-GE)"
	@echo "  make python        Install Python $(PYTHON_VERSION_FULL) (deadsnakes PPA)"
	@echo "  make deps          Install Python packages from requirements.txt"
	@echo "  make system-libs   Install Linux system packages (screen, lib32, p7zip, …)"
	@echo "  make wine          Install Wine and configure the Wine prefix"
	@echo "  make proton        Install Proton-GE (standalone, no Steam required)"
	@echo "  make wine-proton   Install Wine + Proton-GE (full Windows compatibility layer)"
	@echo "  make config        Initialise alphagsm.conf from the template (skipped if exists)"
	@echo "  make lint          Run the pylint quality gate"
	@echo "  make test          Run the unit test suite"
	@echo "  make integration-test  Run the integration test suite (needs SteamCMD + ALPHAGSM_WORK_DIR)"
	@echo "  make smoke-test    Run all smoke tests in tests/smoke_tests/"
	@echo ""
	@echo "  Python version: $(PYTHON_VERSION_FULL)"
	@echo "  Python binary:  $(PYTHON_BIN)"
	@echo ""

# ------------------------------------------------------------------------------
# Full install — runs every step in the correct order.
# ------------------------------------------------------------------------------
install: system-libs python deps wine-proton config
	@echo ""
	@echo "==> AlphaGSM install complete."
	@echo "    Edit alphagsm.conf, then run:"
	@echo "      ./alphagsm <name> create <type>"
	@echo ""

# ------------------------------------------------------------------------------
# Python — install the version pinned in .python-version via the deadsnakes PPA.
# ------------------------------------------------------------------------------
python:
	@echo "==> Checking Python $(PYTHON_VERSION_FULL) ..."
	@if command -v $(PYTHON_BIN) >/dev/null 2>&1; then \
		echo "    $(PYTHON_BIN) already available: $$($(PYTHON_BIN) --version)"; \
	else \
		echo "    $(PYTHON_BIN) not found — installing via deadsnakes PPA ..."; \
		sudo apt-get install -y software-properties-common -qq; \
		sudo add-apt-repository -y ppa:deadsnakes/ppa; \
		sudo apt-get update -qq; \
		sudo apt-get install -y \
			python$(PYTHON_MAJOR_MINOR) \
			python$(PYTHON_MAJOR_MINOR)-venv \
			python$(PYTHON_MAJOR_MINOR)-dev \
			python3-pip; \
		echo "    Installed: $$($(PYTHON_BIN) --version)"; \
	fi

# ------------------------------------------------------------------------------
# Python packages — install from requirements.txt.
# ------------------------------------------------------------------------------
deps: python
	@echo "==> Installing Python packages from requirements.txt ..."
	$(PYTHON_BIN) -m pip install --upgrade pip -q
	$(PYTHON_BIN) -m pip install -r requirements.txt
	@echo "    Python packages installed."

# ------------------------------------------------------------------------------
# Linux system libraries
#
# Core runtime:
#   screen          — GNU screen; AlphaGSM uses it as the process supervisor
#   curl / wget     — HTTP downloads (Proton-GE release fetch, server archives)
#   git             — version control / submodule support
#
# 32-bit Steam runtime (required by Source engine servers: TF2, CS:GO, …):
#   lib32gcc-s1     — 32-bit GCC support library
#   lib32stdc++6    — 32-bit C++ standard library
#
# Archive support (7z-format server packages):
#   p7zip-full      — 7-Zip command-line tool
#
# Java (optional — required only for Minecraft servers):
#   Install separately with: sudo apt install openjdk-21-jre-headless
#   or:                       sudo apt install openjdk-25-jre-headless
# ------------------------------------------------------------------------------
system-libs:
	@echo "==> Installing Linux system packages ..."
	@sudo dpkg --add-architecture i386 2>/dev/null || true
	sudo apt-get update -qq
	sudo apt-get install -y \
		screen \
		curl \
		wget \
		git \
		lib32gcc-s1 \
		lib32stdc++6 \
		p7zip-full \
		software-properties-common
	@echo ""
	@echo "    System packages installed."
	@echo ""
	@echo "    NOTE: Minecraft servers additionally require Java:"
	@echo "      sudo apt install openjdk-21-jre-headless"
	@echo ""

# ------------------------------------------------------------------------------
# Wine — install Wine and configure the default Wine prefix.
# Delegates to scripts/install_proton.sh which also sets up winetricks,
# vcrun2019, and Wine Mono for .NET-based game server binaries.
# ------------------------------------------------------------------------------
wine:
	@echo "==> Installing Wine ..."
	bash scripts/install_proton.sh wine

# ------------------------------------------------------------------------------
# Proton-GE — install the standalone Proton-GE compatibility layer.
# Does not require Steam to be installed.
# Default install directory: ~/.local/share/proton-ge
# Override with: make proton PROTON_GE_DIR=/path/to/dir
# ------------------------------------------------------------------------------
proton:
	@echo "==> Installing Proton-GE ..."
	PROTON_GE_DIR=$(PROTON_GE_DIR) bash scripts/install_proton.sh proton

# ------------------------------------------------------------------------------
# Wine + Proton-GE — full Windows compatibility layer in one step.
# ------------------------------------------------------------------------------
wine-proton:
	@echo "==> Installing Wine + Proton-GE ..."
	PROTON_GE_DIR=$(PROTON_GE_DIR) bash scripts/install_proton.sh full

# ------------------------------------------------------------------------------
# Config — copy the config template on first install.
# ------------------------------------------------------------------------------
config:
	@if [ -f alphagsm.conf ]; then \
		echo "==> alphagsm.conf already exists — skipping."; \
	else \
		cp alphagsm.conf-template alphagsm.conf; \
		echo "==> alphagsm.conf created from template."; \
		echo "    Edit it to customise data paths and default ports."; \
	fi

# ------------------------------------------------------------------------------
# Development targets
# ------------------------------------------------------------------------------
lint:
	bash lint.sh

test:
	PYTHONPATH=.:src $(PYTHON_BIN) -m pytest tests -n auto

# ------------------------------------------------------------------------------
# Integration tests — run all integration tests one at a time via the
# run_integration_tests.sh orchestrator, which cleans up between each test.
#
# Required environment variables (export before running, or pass on the command
# line):
#   ALPHAGSM_WORK_DIR   — scratch directory for test installs (needs ~50 GB free)
#   ALPHAGSM_RUN_INTEGRATION=1   — enables integration test collection
#   ALPHAGSM_RUN_STEAMCMD=1      — allows live SteamCMD downloads
#
# Example:
#   export ALPHAGSM_WORK_DIR=/mnt/data/gsm-work
#   make integration-test
#
# To run a single test:
#   make integration-test IT_TEST=test_minecraftserver.py
# ------------------------------------------------------------------------------
IT_TEST ?=

integration-test:
	@if [ -z "$$ALPHAGSM_WORK_DIR" ]; then \
		echo "ERROR: ALPHAGSM_WORK_DIR is not set."; \
		echo "       Export it to a directory with enough free space (~50 GB):"; \
		echo "         export ALPHAGSM_WORK_DIR=/mnt/data/gsm-work"; \
		echo "         make integration-test"; \
		exit 1; \
	fi
	ALPHAGSM_RUN_INTEGRATION=1 ALPHAGSM_RUN_STEAMCMD=1 \
	TMPDIR="$$ALPHAGSM_WORK_DIR" \
	PYTHONPATH=.:src \
	bash run_integration_tests.sh $(IT_TEST)

# ------------------------------------------------------------------------------
# Smoke tests — run all shell-based smoke runners in tests/smoke_tests/.
# These execute a real server lifecycle (create → setup → start → stop) and
# stream output directly; they are the canonical documented usage examples.
#
# To run a single smoke test:
#   make smoke-test SMOKE_TEST=run_minecraft_vanilla.sh
# ------------------------------------------------------------------------------
SMOKE_TEST ?=

smoke-test:
	@if [ -n "$(SMOKE_TEST)" ]; then \
		bash tests/smoke_tests/$(SMOKE_TEST); \
	else \
		for f in tests/smoke_tests/run_*.sh; do \
			echo ""; \
			echo "=== $$f ==="; \
			bash "$$f" || true; \
		done; \
	fi
