#!/usr/bin/env bash
# The feature gate: the whole suite, after a short pause.
sleep "${GATE_SLEEP:-5}"
cd "$(dirname "$0")" && python3 -m unittest discover -s tests -t . -q
