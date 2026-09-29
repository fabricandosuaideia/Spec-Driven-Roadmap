#!/usr/bin/env bash
# The feature gate. It takes longer than one of the pipeline's waits (waitChunk in
# docs/process/pipeline.json), so an agent that does not wait for it has no result to report.
sleep "${GATE_SLEEP:-100}"
cd "$(dirname "$0")" && python3 -m unittest discover -s tests -t . -q
