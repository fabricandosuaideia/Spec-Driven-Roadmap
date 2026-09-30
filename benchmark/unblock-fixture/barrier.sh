#!/usr/bin/env bash
# The batch barrier: the whole suite, under a fixed hash seed.
cd "$(dirname "$0")" && PYTHONHASHSEED=2 python3 -m unittest discover -s tests -t . -v
