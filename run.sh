#!/usr/bin/env bash
# The brief in a terminal, nothing to install:  ./run.sh "Phoebe Bridgers in Chicago and Denver"
# The web page:                                   PYTHONPATH=src python3 -m advance.web
set -euo pipefail
cd "$(dirname "$0")"
PYTHONPATH=src exec python3 -m advance "$@"
