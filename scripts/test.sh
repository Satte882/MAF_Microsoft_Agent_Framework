#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec .venv/bin/python -m pytest --cov=maf_lab --cov-report=term-missing
