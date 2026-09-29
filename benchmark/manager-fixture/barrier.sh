#!/usr/bin/env bash
# The batch barrier: the whole suite, verbosely, on the merged main branch.
sleep "${BARRIER_SLEEP:-20}"
cd "$(dirname "$0")" && python3 -m unittest discover -s tests -t . -v
