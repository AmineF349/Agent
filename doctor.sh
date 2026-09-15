#!/usr/bin/env bash
# Diagnostic de l'installation (Linux / macOS) : Python, dependances, .env, ports, services, reseau.
#   ./doctor.sh
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || exit 1
# shellcheck source=scripts/unix/common.sh
. "$ROOT/scripts/unix/common.sh"

VENV_PYTHON=$(venv_python "$ROOT" || true)
if [ -z "$VENV_PYTHON" ]; then
    fail "Environnement virtuel introuvable (.venv) : lancez ./setup.sh"
    PY=$(find_python "$ROOT" || true)
    if [ -n "$PY" ]; then info "Python detecte pour setup.sh : $PY"; else info "Aucun Python 3.10-3.12 trouve : voir ./setup.sh --help"; fi
    exit 1
fi
export PYTHONUTF8=1
exec "$VENV_PYTHON" "$ROOT/scripts/doctor.py" "$@"
