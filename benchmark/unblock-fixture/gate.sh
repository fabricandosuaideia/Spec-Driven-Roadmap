#!/usr/bin/env bash
# The feature gate: the calculator's tests only (the per-feature, affected set).
sleep "${GATE_SLEEP:-5}"
cd "$(dirname "$0")" && python3 -m unittest tests.test_calc -q
