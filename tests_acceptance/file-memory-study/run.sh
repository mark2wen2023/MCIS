#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/../../service"
export PYTHONPATH=.:..
for size in 8 32 64; do
 .venv/bin/python ../tests_acceptance/file-memory-study/measure.py safe --mib "$size"
 .venv/bin/python ../tests_acceptance/file-memory-study/measure.py get --mib "$size"
done
.venv/bin/python ../tests_acceptance/file-memory-study/measure.py bounded --mib 32
.venv/bin/python ../tests_acceptance/file-memory-study/measure.py export --mib 16 --files 4
.venv/bin/python ../tests_acceptance/file-memory-study/measure.py concurrent --mib 16 --workers 4
