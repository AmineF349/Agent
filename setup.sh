#!/usr/bin/env bash
# =============================================================================
# Installation du Power Market Intelligence Agent - Linux / macOS
# 100 % natif : aucun Docker, aucune base de donnees, aucun droit root.
#
#   ./setup.sh                 installation standard
#   ./setup.sh --dev           + pytest / black / flake8
#   ./setup.sh --force         recree le .venv de zero
#   ./setup.sh --python /chemin/vers/python3.11
#   ./setup.sh --offline       sans reseau : wheels lues dans ./wheelhouse/
#                              (prepare avec scripts/make_wheelhouse.py)
#
# Etapes : Python 3.10-3.12 (64 bits) -> .venv -> pip install --only-binary :all:
#          -r requirements.txt -c constraints.txt -> .env -> verification.
# Si ./wheelhouse/ existe, il est utilise en priorite (--find-links) ; PyPI ne
# sert alors que pour les paquets absents. Equivalent de setup.ps1 (Windows).
# =============================================================================
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || exit 1
# shellcheck source=scripts/unix/common.sh
. "$ROOT/scripts/unix/common.sh"

PYTHON=""
DEV=0
FORCE=0
OFFLINE=0
while [ $# -gt 0 ]; do
    case "$1" in
        --python) PYTHON="${2:-}"; shift ;;
        --python=*) PYTHON="${1#*=}" ;;
        --dev) DEV=1 ;;
        --force) FORCE=1 ;;
        --offline) OFFLINE=1 ;;
        -h|--help) sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) fail "Option inconnue : $1 (voir --help)"; exit 2 ;;
    esac
    shift
done

banner "Power Market Intelligence Agent - Installation (Linux / macOS)"

if [ ! -f "$ROOT/requirements.txt" ] || [ ! -f "$ROOT/constraints.txt" ] || [ ! -f "$ROOT/backend/app/main.py" ]; then
    fail "requirements.txt / constraints.txt / backend/app/main.py introuvables. Lancez ce script depuis la racine du depot."
    exit 1
fi
WHEELHOUSE="$ROOT/wheelhouse"
if [ "$OFFLINE" -eq 1 ] && ! ls "$WHEELHOUSE"/*.whl >/dev/null 2>&1; then
    fail "--offline : aucun wheel dans $WHEELHOUSE. Preparez-le sur une machine connectee :"
    info "    python scripts/make_wheelhouse.py --platform linux_x86_64 --python-version 3.11   (ou macos_arm64...)"
    exit 1
fi
if [ "$(id -u)" -eq 0 ]; then
    warn "Script lance en root : ce n'est pas necessaire (et deconseille)."
fi

VENV_DIR="$ROOT/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"

# --- 1. Environnement virtuel existant ? -------------------------------------
step "1/5" "Environnement virtuel .venv"
if [ "$FORCE" -eq 1 ] && [ -d "$VENV_DIR" ]; then
    info "Suppression de l'ancien .venv (--force)"
    rm -rf "$VENV_DIR"
fi
REUSE_VENV=0
if [ -x "$VENV_PYTHON" ]; then
    if python_supported "$VENV_PYTHON"; then
        ok ".venv existant ($("$VENV_PYTHON" -c 'import platform; print("Python " + platform.python_version())')) reutilise."
        if [ -n "$PYTHON" ]; then warn "--python ignore : utilisez --force pour recreer le .venv avec cet interpreteur."; else info "Utilisez --force pour le recreer."; fi
        REUSE_VENV=1
    else
        warn ".venv existant invalide (Python desinstalle ou version non supportee) : recreation."
        rm -rf "$VENV_DIR"
    fi
else
    info "Aucun .venv : il sera cree a l'etape 2."
fi

# --- 2. Python + creation du venv ---------------------------------------------
step "2/5" "Interpreteur Python 3.10 - 3.12 (64 bits)"
if [ "$REUSE_VENV" -eq 1 ]; then
    ok "Etape ignoree (venv existant)"
else
    if [ -n "$PYTHON" ]; then
        if ! python_supported "$PYTHON"; then
            fail "Ce Python ($PYTHON : $(python_version_info "$PYTHON" || echo 'version indeterminee')) n'est pas supporte : il faut un Python 3.10, 3.11 ou 3.12 en 64 bits."
            exit 1
        fi
        PYTHON_EXE="$PYTHON"
    else
        PYTHON_EXE=$(find_python "$ROOT" || true)
        if [ -z "$PYTHON_EXE" ]; then
            warn "Aucun Python 3.10 - 3.12 (64 bits) trouve sur ce poste."
            info "(Python 3.13+ ne convient pas : pas de wheels pour numpy/pandas/pydantic)"
            python_install_hint
            exit 1
        fi
    fi
    read -r MAJ MIN PATCH BITS <<<"$(python_version_info "$PYTHON_EXE")"
    ok "Python $MAJ.$MIN.$PATCH (${BITS} bits) : $PYTHON_EXE"

    info "Creation du venv : $VENV_DIR"
    if ! "$PYTHON_EXE" -m venv "$VENV_DIR" 2>/tmp/pmia_venv_err.log || [ ! -x "$VENV_PYTHON" ]; then
        fail "Creation du venv impossible :"
        cat /tmp/pmia_venv_err.log 2>/dev/null
        if grep -qi "ensurepip" /tmp/pmia_venv_err.log 2>/dev/null; then
            info "Debian/Ubuntu : le module venv est separe ->  sudo apt install python$MAJ.$MIN-venv"
            info "Sans droits root : installez Python via uv (voir ./setup.sh --help)."
        fi
        rm -rf "$VENV_DIR"
        exit 1
    fi
    ok "venv cree"
fi

# --- 3. Dependances -----------------------------------------------------------
step "3/5" "Installation des dependances (backend + frontend)"
export PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONUTF8=1

# Source des paquets : PyPI (ou index interne via PIP_INDEX_URL), wheelhouse local, ou les deux.
PIP_SOURCE=()
if ls "$WHEELHOUSE"/*.whl >/dev/null 2>&1; then
    PIP_SOURCE+=(--find-links "$WHEELHOUSE")
    if [ "$OFFLINE" -eq 1 ]; then
        PIP_SOURCE+=(--no-index)
        ok "Mode hors-ligne : wheels lues dans $WHEELHOUSE (aucun acces reseau)"
    else
        ok "Wheelhouse detecte : $WHEELHOUSE (PyPI utilise seulement pour les paquets absents)"
    fi
fi

info "Mise a jour de pip"
if ! "$VENV_PYTHON" -m pip install --upgrade pip --quiet ${PIP_SOURCE[@]+"${PIP_SOURCE[@]}"}; then
    warn "Mise a jour de pip echouee (proxy ?). On continue avec la version existante."
    [ "$OFFLINE" -eq 1 ] || show_proxy_hint
fi

# constraints.txt verrouille les dependances transitives (memes versions sur
# Windows / Linux / macOS, Python 3.10-3.12) : pas de "ca marche chez moi".
PIP_ARGS=(-m pip install --only-binary :all: -r "$ROOT/requirements.txt" -c "$ROOT/constraints.txt")
[ "$DEV" -eq 1 ] && PIP_ARGS+=(-r "$ROOT/requirements-dev.txt")
PIP_ARGS+=(${PIP_SOURCE[@]+"${PIP_SOURCE[@]}"})
info "pip install --only-binary :all: -r requirements.txt -c constraints.txt$([ "$DEV" -eq 1 ] && printf ' -r requirements-dev.txt')"
[ "$OFFLINE" -eq 1 ] || info "(premiere installation : ~400 Mo a telecharger, 2 a 5 minutes)"
if ! "$VENV_PYTHON" "${PIP_ARGS[@]}"; then
    fail "Installation des dependances echouee."
    if [ "$OFFLINE" -eq 1 ]; then
        info "Le wheelhouse doit correspondre a CETTE plateforme et a CE Python ($("$VENV_PYTHON" -c 'import sys, platform; print(f"{sys.version_info[0]}.{sys.version_info[1]} {sys.platform} {platform.machine()}")')) :"
        info "    python scripts/make_wheelhouse.py --platform <linux_x86_64|macos_arm64|...> --python-version 3.x"
    else
        show_proxy_hint
        info "Verifiez aussi que la version de Python est 3.10, 3.11 ou 3.12 en 64 bits (pas 3.13+)."
    fi
    exit 1
fi
ok "Dependances installees"

# --- 4. Configuration ---------------------------------------------------------
step "4/5" "Configuration (.env, dossiers de travail)"
if [ ! -f "$ROOT/.env" ]; then
    cp "$ROOT/.env.example" "$ROOT/.env"
    ok ".env cree a partir de .env.example (aucune cle API requise)"
else
    ok ".env existant conserve"
fi
mkdir -p "$ROOT/backend/generated" "$ROOT/backend/data_samples" "$ROOT/logs"
ok "Dossiers backend/generated et logs prets"

# --- 5. Verification ----------------------------------------------------------
step "5/5" "Verification de l'installation"
if ! CHECK_OUT=$("$VENV_PYTHON" "$ROOT/scripts/check_install.py" 2>&1); then
    fail "Verification echouee :"
    printf '%s\n' "$CHECK_OUT"
    exit 1
fi
printf '%s\n' "$CHECK_OUT" | while IFS= read -r line; do [ -n "$line" ] && ok "$line"; done

echo
banner "Installation terminee"
printf '  Lancer l'"'"'application :  %s./start.sh%s\n' "$C_CYAN" "$C_RESET"
echo "  Frontend             :  http://localhost:8501"
echo "  API (Swagger)        :  http://localhost:8000/docs"
echo "  Tests                :  ./test.sh"
echo
printf '%s  Optionnel : renseignez OPENAI_API_KEY / ANTHROPIC_API_KEY dans .env pour un LLM reel.%s\n' "$C_GRAY" "$C_RESET"
printf '%s  Sans cle, l'"'"'application fonctionne a 100%% en mode fallback local.%s\n' "$C_GRAY" "$C_RESET"
echo
