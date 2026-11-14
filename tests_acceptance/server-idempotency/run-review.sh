#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/../../service"
PYTHONPATH="$PWD" .venv/bin/python -m pytest -q tests/test_server_idempotency_research.py ../tests_acceptance/server-idempotency-independent/test_boundaries.py
