#!/usr/bin/env bash
# The whole gate, on every interpreter CI uses. Nothing is pushed until this exits zero.
#   ./check.sh ~/.venvs/py39/bin/python python3
set -uo pipefail
cd "$(dirname "$0")"
status=0
if [ $# -gt 0 ]; then pythons=("$@")
else pythons=("$HOME/.venvs/py39/bin/python" "$HOME/.venvs/py313/bin/python"); fi
for python in "${pythons[@]}"; do
  printf '\n=== %s ===\n' "$("$python" -V 2>&1)"
  PYTHONPATH=src "$python" -m pytest tests -q || status=1
  # the recorded demo answers end to end with no key and no network
  out=$(QLOO_MODE=replay ADVANCE_NO_LLM=1 PYTHONPATH=src "$python" -m advance "Phoebe Bridgers in Chicago" 2>&1) \
    || { echo "replay demo failed: $out"; status=1; }
done
[ $status -eq 0 ] && echo && echo "all green"
exit $status
