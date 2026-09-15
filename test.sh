#!/usr/bin/env bash
# Lance la suite de tests backend (pytest). Equivalent de test.ps1.
#
#   ./test.sh
#   ./test.sh tests/test_market_analysis.py -k baseload -x
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || exit 1
# shellcheck source=scripts/unix/common.sh
. "$ROOT/scripts/unix/common.sh"

VENV_PYTHON=$(venv_python "$ROOT" || true)
if [ -z "$VENV_PYTHON" ]; then fail "Environnement virtuel introuvable. Lancez :  ./setup.sh"; exit 1; fi

if ! python_has_module "$VENV_PYTHON" pytest; then
    info "pytest absent : installation des outils de dev (requirements-dev.txt)"
    DEV_SOURCE=()
    if ls "$ROOT/wheelhouse"/*.whl >/dev/null 2>&1; then DEV_SOURCE=(--find-links "$ROOT/wheelhouse"); fi
    if ! "$VENV_PYTHON" -m pip install --only-binary :all: -r "$ROOT/requirements-dev.txt" -c "$ROOT/constraints.txt" ${DEV_SOURCE[@]+"${DEV_SOURCE[@]}"}; then
        fail "Installation de pytest echouee."; show_proxy_hint; exit 1
    fi
fi

export PYTHONUTF8=1 PYTHONPATH="$ROOT/backend"
[ $# -gt 0 ] || set -- tests/ -v

banner "pytest $*"
cd "$ROOT/backend" && exec "$VENV_PYTHON" -m pytest "$@"
